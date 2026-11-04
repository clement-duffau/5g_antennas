#!/usr/bin/env python3
"""Contrôles de cohérence complémentaires (jointures, unités, coordonnées, opérateurs).

Usage : python scripts/explore_checks.py data/raw/AAAAMMJJ-export-etalab-data.zip data/raw/AAAAMMJJ-export-etalab-ref.zip
Les résultats commentés sont dans docs/data-exploration.md.
"""
import sys, zipfile, io, pandas as pd, numpy as np
d, r = sys.argv[1], sys.argv[2]
def rd(z, n):
    with zipfile.ZipFile(z) as zf: return pd.read_csv(io.BytesIO(zf.read(n+".txt")), sep=";", dtype=str, encoding="utf-8")
sup=rd(d,"SUP_SUPPORT"); sta=rd(d,"SUP_STATION"); ant=rd(d,"SUP_ANTENNE"); emr=rd(d,"SUP_EMETTEUR"); ban=rd(d,"SUP_BANDE")
exp=rd(r,"SUP_EXPLOITANT"); nat=rd(r,"SUP_NATURE"); tpo=rd(r,"SUP_PROPRIETAIRE")
num=lambda s: pd.to_numeric(s.str.replace(",",".",regex=False), errors="coerce")
P=print
# coords
for c in ["COR_NB_DG_LAT","COR_NB_MN_LAT","COR_NB_SC_LAT","COR_NB_DG_LON","COR_NB_MN_LON","COR_NB_SC_LON"]: sup[c]=num(sup[c])
sup["lat"]=(sup.COR_NB_DG_LAT+sup.COR_NB_MN_LAT/60+sup.COR_NB_SC_LAT/3600)*np.where(sup.COR_CD_NS_LAT=="S",-1,1)
sup["lon"]=(sup.COR_NB_DG_LON+sup.COR_NB_MN_LON/60+sup.COR_NB_SC_LON/3600)*np.where(sup.COR_CD_EW_LON=="W",-1,1)
g=sup.groupby("SUP_ID").agg(nlat=("lat","nunique"),nlon=("lon","nunique"),nnat=("NAT_ID","nunique"),nh=("SUP_NM_HAUT","nunique"),ninsee=("COM_CD_INSEE","nunique"),ntpo=("TPO_ID","nunique"),nsta=("STA_NM_ANFR","nunique"))
P("== SUP_ID cohérence (supports où l'attribut varie entre lignes):"); P((g[["nlat","nlon","nnat","nh","ninsee","ntpo"]]>1).sum().to_dict())
P("stations par support:", g.nsta.describe().round(2).to_dict()); P(g.nsta.value_counts().head(8).to_dict())
st_sup=sup.groupby("STA_NM_ANFR").SUP_ID.nunique(); P("supports par station:", st_sup.value_counts().head(5).to_dict())
s1=sup.drop_duplicates("SUP_ID")
P("seconde=60 :", int((sup.COR_NB_SC_LAT==60).sum()))
P("bbox lat", s1.lat.min(), s1.lat.max(), "lon", s1.lon.min(), s1.lon.max())
dep=s1.COM_CD_INSEE.str[:2]; dep=np.where(dep.isin(["97","98"]), s1.COM_CD_INSEE.str[:3], dep)
s1=s1.assign(dep=dep)
P("INSEE longueurs:", s1.COM_CD_INSEE.str.len().value_counts().to_dict())
P("zones:", {"metro":int((~s1.dep.str.startswith("9")|s1.dep.isin(["91","92","93","94","95"])).sum())})
P("dep 97x/98x:", s1[s1.dep.str.len()==3].dep.value_counts().to_dict())
P("métro hors bbox (41-51.5N, -5.5-10E):", int(((~s1.dep.str.len().eq(3)) & ~(s1.lat.between(41,51.5)&s1.lon.between(-5.5,10))).sum()))
h=num(s1.SUP_NM_HAUT); P("hauteur quantiles", h.quantile([.5,.9,.99,.999]).to_dict(), "<=0:", int((h<=0).sum()), ">200:", int((h>200).sum()))
P("top hauteurs:"); P(s1.assign(h=h).nlargest(8,"h")[["SUP_ID","h","NAT_ID","COM_CD_INSEE","ADR_LB_ADD1"]].to_string())
P("natures:"); P(s1.NAT_ID.map(dict(zip(nat.NAT_ID,nat.NAT_LB_NOM))).value_counts().head(15).to_dict())
P("propriétaires:"); P(s1.TPO_ID.map(dict(zip(tpo.TPO_ID,tpo.TPO_LB))).value_counts().head(12).to_dict())
# exploitants
sta["exp"]=sta.ADM_ID.map(dict(zip(exp.ADM_ID,exp.ADM_LB_NOM)))
P("== exploitants (stations):"); P(sta.exp.value_counts().head(25).to_dict())
P("ADM_ID sans libellé:", int(sta.exp.isna().sum()))
P("STA_NM_USER vs ADM_ID 1-1 ?", sta.groupby("ADM_ID").STA_NM_USER.nunique().max())
# joins
P("== jointures")
P("emr.STA absent de station:", int((~emr.STA_NM_ANFR.isin(sta.STA_NM_ANFR)).sum()))
P("sup.STA absent de station:", int((~sup.STA_NM_ANFR.isin(sta.STA_NM_ANFR)).sum()))
P("emr.AER absent de antenne:", int((~emr.AER_ID.isin(ant.AER_ID)).sum()))
P("ban.EMR absent de emr:", int((~ban.EMR_ID.isin(emr.EMR_ID)).sum()), "emr sans bande:", int((~emr.EMR_ID.isin(ban.EMR_ID)).sum()))
dup=ant[ant.duplicated("AER_ID",keep=False)].sort_values("AER_ID"); P("AER_ID dupliqués, exemple:"); P(dup.head(6).to_string())
P("AER dupliqué: même station ?", (dup.groupby("AER_ID").STA_NM_ANFR.nunique()>1).sum(), "sup différents:", (dup.groupby("AER_ID").SUP_ID.nunique()>1).sum())
# emr->station->exp, system
emr=emr.merge(sta[["STA_NM_ANFR","exp"]], on="STA_NM_ANFR", how="left")
P("== systèmes x exploitants (top)")
mob=emr[emr.EMR_LB_SYSTEME.str.match(r"^(GSM|UMTS|LTE|5G)", na=False)]
P(mob.exp.value_counts().head(10).to_dict())
for s in ["FH","PMR","FM","RDF DVB-T","TETRA","GSM R","COM TER","BLR LTE 3500"]:
    P(s, emr[emr.EMR_LB_SYSTEME==s].exp.value_counts().head(5).to_dict())
# frequencies normalized
ban["f0"]=num(ban.BAN_NB_F_DEB); ban["f1"]=num(ban.BAN_NB_F_FIN)
mul=ban.BAN_FG_UNITE.map({"K":1e-3,"M":1,"G":1e3})
ban["m0"]=ban.f0*mul; ban["m1"]=ban.f1*mul
b=ban.merge(emr[["EMR_ID","EMR_LB_SYSTEME"]], on="EMR_ID", how="left")
P("== plages MHz normalisées par système (q05/q50/q95 de f_deb)")
t=b.groupby("EMR_LB_SYSTEME").agg(n=("m0","size"),q05=("m0",lambda x:x.quantile(.05)),q50=("m0","median"),q95=("m1",lambda x:x.quantile(.95)),mn=("m0","min"),mx=("m1","max"))
P(t.sort_values("n",ascending=False).head(40).round(2).to_string())
P("bandes f_fin<f_deb:", int((b.m1<b.m0).sum()), "largeur 0:", int((b.m1==b.m0).sum()))
P("bandes par émetteur:", ban.groupby("EMR_ID").size().value_counts().head(6).to_dict())
P("unité G par système:", b[b.BAN_FG_UNITE=="G"].EMR_LB_SYSTEME.value_counts().head(8).to_dict())
P("unité K par système:", b[b.BAN_FG_UNITE=="K"].EMR_LB_SYSTEME.value_counts().head(8).to_dict())
P("FH en M >10000:", int(((b.EMR_LB_SYSTEME=="FH")&(b.BAN_FG_UNITE=="M")&(b.f0>10000)).sum()))
P("LTE 800 exemples bornes:", b[b.EMR_LB_SYSTEME=="LTE 800"][["m0","m1"]].value_counts().head(6).to_dict())
P("5G NR 3500 exemples:", b[b.EMR_LB_SYSTEME=="5G NR 3500"].merge(emr[["EMR_ID","exp"]],on="EMR_ID").groupby("exp")[["m0","m1"]].agg(lambda x: x.mode().iloc[0]).to_dict())
# dates
emr["dt"]=pd.to_datetime(emr.EMR_DT_SERVICE, format="%d/%m/%Y", errors="coerce")
P("dates > 2026-11-04:", int((emr.dt>"2026-11-04").sum()), "< 1990:", int((emr.dt<"1990-01-01").sum()))
P("5G NR 3500 par année:", emr[emr.EMR_LB_SYSTEME=="5G NR 3500"].dt.dt.year.value_counts().sort_index().to_dict())
P("sans date par système:", emr[emr.dt.isna()].EMR_LB_SYSTEME.value_counts().head(8).to_dict())
# multi-operator sites
mobsta=sta[sta.STA_NM_ANFR.isin(mob.STA_NM_ANFR)]
m=sup.merge(mobsta[["STA_NM_ANFR","exp"]],on="STA_NM_ANFR").groupby("SUP_ID").exp.nunique()
P("supports mobiles:", len(m), "nb opérateurs mobiles:", m.value_counts().sort_index().to_dict())
P("supports avec au moins 1 émetteur:", sup[sup.STA_NM_ANFR.isin(emr.STA_NM_ANFR)].SUP_ID.nunique())
