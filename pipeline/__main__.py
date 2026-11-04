"""Point d'entrée du pipeline.

    python -m pipeline build                    # dernière extraction publiée
    python -m pipeline build --extraction 20260831
    python -m pipeline build --zip data.zip ref.zip --date 2026-09-30   # hors ligne
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import duckdb

from . import clean, communes, export, fetch, load, stats
from .config import CACHE_DIR, DATASET_PAGE, OUT_DIR


def _json_default(o: object) -> object:
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    raise TypeError(f"non sérialisable : {type(o)}")


def write_json(path: Path, data: object, quiet: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=_json_default),
                    encoding="utf-8")
    if not quiet:
        print(f"  {path.name} : {path.stat().st_size / 1e3:,.0f} Ko")


def cmd_build(args: argparse.Namespace) -> int:
    t0 = time.time()
    meta_source: dict = {}
    if args.zip:
        zips = [Path(z) for z in args.zip]
        key = args.date.replace("-", "") if args.date else zips[0].name[:8]
    else:
        meta = fetch.fetch_metadata()
        extractions = fetch.list_extractions(meta)
        ext = extractions[-1] if args.extraction == "latest" else next(
            e for e in extractions if e.key == args.extraction)
        data_zip, ref_zip = fetch.download_extraction(ext)
        zips = [p for p in (data_zip, ref_zip) if p]
        key = ext.key
        meta_source = {
            "titre": meta.get("title", "").strip(),
            "licence": meta.get("license"),
            "page": DATASET_PAGE,
            "archive": ext.data.get("title"),
            "url": ext.data.get("url"),
            "publication": (ext.data.get("last_modified") or "")[:10],
            "extractions_disponibles": len(extractions),
        }
    extraction_date = f"{key[:4]}-{key[4:6]}-{key[6:]}"
    print(f"extraction {extraction_date}", flush=True)

    db = CACHE_DIR / "atlas.duckdb"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    load.load(con, load.extract(zips, key))
    communes.load(con, refresh=args.refresh_geo)
    clean.clean(con, extraction_date)
    print(f"nettoyage terminé ({time.time() - t0:.0f} s)", flush=True)

    out = Path(args.out)
    meta_site = {
        "extraction": extraction_date,
        "generation": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": meta_source,
        "perimetre": "France métropolitaine (Corse comprise)",
    }
    write_json(out / "meta.json", meta_site)
    write_json(out / "stats.json", {"meta": meta_site, **stats.build(con)})
    export.write_all(con, out, write_json)
    print(f"terminé en {time.time() - t0:.0f} s")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline", description="Atlas des antennes : pipeline de données")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="télécharge, nettoie et exporte une extraction")
    b.add_argument("--extraction", default="latest", help="AAAAMMJJ ou 'latest'")
    b.add_argument("--zip", nargs="+", help="archives locales (data, ref) au lieu du téléchargement")
    b.add_argument("--date", help="date d'extraction AAAA-MM-JJ (avec --zip)")
    b.add_argument("--out", default=str(OUT_DIR), help="dossier de sortie")
    b.add_argument("--refresh-geo", action="store_true", help="re-télécharger le référentiel communes")
    b.set_defaults(func=cmd_build)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
