#!/usr/bin/env python3
"""Exploration d'un mois du jeu ANFR « installations radioélectriques > 5 W ».

Étapes :
  1. interroge l'API data.gouv.fr pour lister les ressources du jeu de données ;
  2. télécharge l'archive zip la plus récente (ou celle passée en argument) dans data/raw/ ;
  3. détecte l'encodage de chaque fichier (UTF-8 strict, sinon Windows-1252) ;
  4. décrit chaque fichier (colonnes, volumes, valeurs nulles, valeurs fréquentes) ;
  5. sort des analyses ciblées (systèmes EMR_LB_SYSTEME, unités de fréquence,
     format des coordonnées, dates de mise en service) ;
  6. écrit le tout dans docs/data-exploration.md.

Usage :
    python scripts/explore.py                 # archive la plus récente
    python scripts/explore.py --zip chemin.zip  # archive déjà téléchargée
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
REPORT = ROOT / "docs" / "data-exploration.md"
DATASET_SLUG = "donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1"
API = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_SLUG}/"
UA = {"User-Agent": "atlas-antennes-pipeline/0.1"}


# --------------------------------------------------------------------------- #
# Téléchargement
# --------------------------------------------------------------------------- #
def fetch_metadata() -> dict:
    r = requests.get(API, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def zip_resources(meta: dict) -> list[dict]:
    res = [
        r for r in meta.get("resources", [])
        if (r.get("format") or "").lower() == "zip" or r.get("url", "").lower().endswith(".zip")
    ]
    # Plus récente d'abord (dernière modification, puis date de création).
    res.sort(key=lambda r: (r.get("last_modified") or r.get("created_at") or ""), reverse=True)
    return res


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"déjà présent : {dest}")
        return dest
    print(f"téléchargement : {url}")
    with requests.get(url, headers=UA, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    return dest


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def detect_encoding(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def non_ascii_sample(text: str, n: int = 8) -> list[str]:
    words = re.findall(r"\b\w*[^\x00-\x7f]\w*\b", text[:2_000_000])
    seen: list[str] = []
    for w in words:
        if w not in seen:
            seen.append(w)
        if len(seen) >= n:
            break
    return seen


def read_member(zf: zipfile.ZipFile, name: str) -> tuple[pd.DataFrame, dict]:
    raw = zf.read(name)
    enc = detect_encoding(raw)
    text = raw.decode(enc)
    first_line = text.split("\n", 1)[0]
    sep = ";" if first_line.count(";") >= first_line.count(",") else ","
    df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False, na_values=[""])
    info = {
        "size_mb": len(raw) / 1e6,
        "encoding": enc,
        "sep": sep,
        "line_ending": "CRLF" if "\r\n" in text[:10000] else "LF",
        "header": first_line.strip(),
        "non_ascii": non_ascii_sample(text),
    }
    return df, info


# --------------------------------------------------------------------------- #
# Rapport
# --------------------------------------------------------------------------- #
def md_escape(v: object, maxlen: int = 60) -> str:
    s = str(v).replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"


def describe(df: pd.DataFrame) -> str:
    lines = ["| Colonne | Non nuls | Distinctes | Exemples (valeurs les plus fréquentes) |",
             "|---|---:|---:|---|"]
    n = len(df)
    for c in df.columns:
        s = df[c]
        nn = int(s.notna().sum())
        nd = int(s.nunique(dropna=True))
        top = s.value_counts(dropna=True).head(5)
        ex = ", ".join(f"`{md_escape(k, 30)}` ({v})" for k, v in top.items())
        lines.append(f"| `{c}` | {nn:,} ({nn / max(n, 1):.0%}) | {nd:,} | {ex} |")
    return "\n".join(lines)


def counts_table(s: pd.Series, title: str, limit: int | None = None) -> str:
    vc = s.value_counts(dropna=False)
    if limit:
        vc = vc.head(limit)
    out = [f"| {title} | Nombre |", "|---|---:|"]
    out += [f"| `{md_escape(k)}` | {v:,} |" for k, v in vc.items()]
    return "\n".join(out)


def find_col(df: pd.DataFrame, *patterns: str) -> list[str]:
    return [c for c in df.columns if any(re.search(p, c, re.I) for p in patterns)]


def targeted(frames: dict[str, pd.DataFrame]) -> list[str]:
    out: list[str] = []

    def get(stem: str) -> pd.DataFrame | None:
        for k, v in frames.items():
            if k.upper().startswith(stem):
                return v
        return None

    emr = get("SUP_EMETTEUR")
    if emr is not None:
        for c in find_col(emr, r"SYSTEME"):
            out += [f"### Valeurs distinctes de `{c}` (SUP_EMETTEUR)", "",
                    counts_table(emr[c], c), ""]
        for c in find_col(emr, r"_DT_"):
            d = pd.to_datetime(emr[c], errors="coerce", dayfirst=True)
            out += [f"### Dates `{c}`", "",
                    f"- exemples bruts : {', '.join('`'+x+'`' for x in emr[c].dropna().unique()[:5])}",
                    f"- parsées : {int(d.notna().sum()):,} / {len(d):,} ; min {d.min()} ; max {d.max()}",
                    "", "Émetteurs par année :", "",
                    counts_table(d.dt.year.astype("Int64").astype(str), "Année").replace("`<NA>`", "*(vide)*"),
                    ""]

    ban = get("SUP_BANDE")
    if ban is not None:
        for c in find_col(ban, r"UNIT", r"_LB_"):
            out += [f"### Valeurs de `{c}` (SUP_BANDE)", "", counts_table(ban[c], c, 30), ""]
        for c in find_col(ban, r"_NB_"):
            num = pd.to_numeric(ban[c].str.replace(",", ".", regex=False), errors="coerce")
            out += [f"- `{c}` : {int(num.notna().sum()):,} numériques, min {num.min()}, max {num.max()}, "
                    f"médiane {num.median()} ; exemples bruts "
                    + ", ".join(f"`{x}`" for x in ban[c].dropna().unique()[:6])]
        out.append("")
        unit_cols = find_col(ban, r"UNIT")
        num_cols = find_col(ban, r"_NB_")
        if unit_cols and num_cols:
            u = unit_cols[0]
            out += [f"Plages de valeurs par unité (`{u}`) :", "",
                    "| Unité | Colonne | min | médiane | max |", "|---|---|---:|---:|---:|"]
            for unit, g in ban.groupby(u, dropna=False):
                for c in num_cols:
                    num = pd.to_numeric(g[c].str.replace(",", ".", regex=False), errors="coerce")
                    out.append(f"| `{unit}` | `{c}` | {num.min()} | {num.median()} | {num.max()} |")
            out.append("")

    sup = get("SUP_SUPPORT")
    if sup is not None:
        coord = find_col(sup, r"COR_", r"LAT", r"LON")
        if coord:
            out += ["### Coordonnées (SUP_SUPPORT)", "", "Colonnes : " + ", ".join(f"`{c}`" for c in coord), "",
                    "Cinq lignes d'exemple :", "",
                    "| " + " | ".join(coord) + " |", "|" + "---|" * len(coord)]
            for _, row in sup[coord].dropna(how="all").sample(min(5, len(sup)), random_state=1).iterrows():
                out.append("| " + " | ".join(md_escape(row[c]) for c in coord) + " |")
            out.append("")
            for c in find_col(sup, r"_CD_"):
                if c in coord:
                    out += [counts_table(sup[c], c), ""]
        for c in find_col(sup, r"HAUT", r"_NB_"):
            num = pd.to_numeric(sup[c].str.replace(",", ".", regex=False), errors="coerce")
            out.append(f"- `{c}` : min {num.min()}, médiane {num.median()}, max {num.max()}, "
                       f"non numériques {int(num.isna().sum()):,}")
        out.append("")
        dep = find_col(sup, r"DEPT|DEP")
        if dep:
            out += ["Départements (top 15) :", "", counts_table(sup[dep[0]], dep[0], 15), ""]

    # Cardinalités des jointures
    sta, ant = get("SUP_STATION"), get("SUP_ANTENNE")
    if emr is not None and sta is not None:
        out += ["### Clés et cardinalités", ""]
        for df_name, df in frames.items():
            keys = [c for c in df.columns if re.search(r"(_ID$|NM_ANFR|_ID_)", c)]
            if keys:
                parts = [f"`{k}` ({df[k].nunique():,} distinctes / {len(df):,} lignes)" for k in keys]
                out.append(f"- **{df_name}** : " + ", ".join(parts))
        out.append("")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, help="archive déjà téléchargée")
    args = ap.parse_args()

    meta_lines: list[str] = []
    if args.zip:
        zpath = args.zip
    else:
        meta = fetch_metadata()
        zres = zip_resources(meta)
        if not zres:
            print("aucune ressource zip trouvée", file=sys.stderr)
            return 1
        latest = zres[0]
        zpath = download(latest["url"], RAW_DIR / Path(latest["url"]).name.split("?")[0])
        meta_lines = [
            f"- Jeu de données : **{meta.get('title')}** (`{meta.get('id')}`)",
            f"- Licence : `{meta.get('license')}` ; fréquence : `{meta.get('frequency')}` ; "
            f"dernière mise à jour : `{meta.get('last_update')}`",
            f"- Ressources zip : {len(zres)} ; la plus récente : **{latest.get('title')}** "
            f"({(latest.get('filesize') or 0) / 1e6:.1f} Mo, modifiée le {latest.get('last_modified')})",
            "", "Dix ressources zip les plus récentes :", "",
            "| Titre | Taille (Mo) | Modifiée |", "|---|---:|---|",
        ] + [f"| {md_escape(r.get('title'))} | {(r.get('filesize') or 0) / 1e6:.1f} | {(r.get('last_modified') or '')[:10]} |"
             for r in zres[:10]] + [""]

    frames: dict[str, pd.DataFrame] = {}
    infos: dict[str, dict] = {}
    with zipfile.ZipFile(zpath) as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]
        for m in members:
            if not re.search(r"\.(txt|csv)$", m, re.I):
                continue
            name = Path(m).stem
            print(f"lecture {m}")
            frames[name], infos[name] = read_member(zf, m)

    rep: list[str] = [
        "# Exploration des données ANFR",
        "",
        f"*Généré par `scripts/explore.py` le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC "
        f"à partir de `{zpath.name}`.*",
        "",
        "## Source",
        "",
        *meta_lines,
        f"Contenu de l'archive : {', '.join(f'`{m}`' for m in members)}",
        "",
        "## Vue d'ensemble des fichiers",
        "",
        "| Fichier | Lignes | Colonnes | Taille (Mo) | Encodage détecté | Séparateur | Fins de ligne | Mots non ASCII |",
        "|---|---:|---:|---:|---|---|---|---|",
    ]
    for k, df in frames.items():
        i = infos[k]
        rep.append(f"| `{k}` | {len(df):,} | {df.shape[1]} | {i['size_mb']:.1f} | {i['encoding']} | "
                   f"`{i['sep']}` | {i['line_ending']} | {md_escape(', '.join(i['non_ascii']), 80)} |")
    rep += ["", "## Analyses ciblées", "", *targeted(frames), "## Détail par fichier", ""]
    for k, df in frames.items():
        rep += [f"### {k}", "", f"En-tête brut : `{md_escape(infos[k]['header'], 300)}`", "", describe(df), ""]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"rapport écrit : {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
