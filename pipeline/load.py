"""Extraction des archives, normalisation d'encodage et chargement dans DuckDB."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import duckdb

from .config import CACHE_DIR

TABLES = ("SUP_SUPPORT", "SUP_STATION", "SUP_ANTENNE", "SUP_EMETTEUR", "SUP_BANDE",
          "SUP_EXPLOITANT", "SUP_NATURE", "SUP_PROPRIETAIRE", "SUP_TYPE_ANTENNE")


def detect_encoding(raw: bytes) -> str:
    """UTF-8 strict (avec ou sans BOM), sinon Windows-1252."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def extract(zips: list[Path], key: str, cache_dir: Path = CACHE_DIR) -> dict[str, Path]:
    """Extrait les tables SUP_* en UTF-8 dans cache_dir/key/. Retourne {table: chemin}."""
    out_dir = cache_dir / key
    out_dir.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for name in zf.namelist():
                stem = Path(name).stem.upper()
                if stem not in TABLES or not re.search(r"\.(txt|csv)$", name, re.I):
                    continue
                dest = out_dir / f"{stem}.txt"
                if not dest.exists():
                    raw = zf.read(name)
                    enc = detect_encoding(raw)
                    text = raw.decode(enc)
                    # On écrit en UTF-8, fins de ligne LF.
                    dest.write_text(text.replace("\r\n", "\n"), encoding="utf-8")
                    if enc != "utf-8":
                        print(f"  {stem} : converti depuis {enc}")
                found[stem] = dest
    missing = [t for t in TABLES if t not in found]
    if missing:
        raise FileNotFoundError(f"tables manquantes dans l'archive : {missing}")
    return found


def load(con: duckdb.DuckDBPyConnection, files: dict[str, Path]) -> None:
    """Crée une table raw_<table> (tout en VARCHAR) par fichier."""
    for table, path in files.items():
        con.execute(f"""
            CREATE OR REPLACE TABLE raw_{table.lower()} AS
            SELECT * FROM read_csv(?, delim=';', header=true, all_varchar=true,
                                   quote='', escape='', strict_mode=false, null_padding=true)
        """, [str(path)])
