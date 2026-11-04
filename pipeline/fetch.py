"""Découverte des ressources via l'API data.gouv.fr et téléchargement robuste."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import DATASET_API, RAW_DIR, USER_AGENT

_KEY_RE = re.compile(r"/(\d{8})-export-etalab-(data|ref)")


def session() -> requests.Session:
    """Session HTTP avec tentatives et attente exponentielle (coupures réseau, 429, 5xx)."""
    s = requests.Session()
    retry = Retry(total=8, connect=8, read=8, backoff_factor=1.5,
                  status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "HEAD"))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": USER_AGENT})
    return s


HTTP = session()


def get_json(url: str, **params) -> object:
    for attempt in range(8):
        try:
            r = HTTP.get(url, params=params or None, timeout=90)
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(2 ** min(attempt + 1, 5))
    raise RuntimeError(f"échec de la requête : {url}")


@dataclass(frozen=True)
class Extraction:
    """Une extraction mensuelle ANFR : la paire d'archives data + ref."""
    key: str             # date d'extraction AAAAMMJJ
    data: dict           # ressource data.gouv (archive des tables)
    ref: dict | None     # ressource data.gouv (tables de référence)

    @property
    def iso_date(self) -> str:
        return f"{self.key[:4]}-{self.key[4:6]}-{self.key[6:]}"


def fetch_metadata() -> dict:
    return get_json(DATASET_API)  # type: ignore[return-value]


def list_extractions(meta: dict) -> list[Extraction]:
    """Toutes les extractions publiées, de la plus ancienne à la plus récente."""
    by_key: dict[str, dict[str, dict]] = {}
    for r in meta.get("resources", []):
        m = _KEY_RE.search(r.get("url", ""))
        if not m:
            continue
        key, kind = m.groups()
        prev = by_key.setdefault(key, {}).get(kind)
        # En cas de doublon, on garde la ressource la plus récemment modifiée.
        if prev is None or (r.get("last_modified") or "") > (prev.get("last_modified") or ""):
            by_key[key][kind] = r
    return [Extraction(k, v["data"], v.get("ref")) for k, v in sorted(by_key.items()) if "data" in v]


def download(url: str, dest: Path, attempts: int = 8) -> Path:
    """Télécharge `url` vers `dest`, avec reprise (en-tête Range) après coupure."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"téléchargement : {url}", flush=True)
    for attempt in range(attempts):
        done = tmp.stat().st_size if tmp.exists() else 0
        headers = {"Range": f"bytes={done}-"} if done else {}
        try:
            with HTTP.get(url, headers=headers, stream=True, timeout=120) as r:
                r.raise_for_status()
                mode = "ab" if done and r.status_code == 206 else "wb"
                with open(tmp, mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            tmp.rename(dest)
            return dest
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** min(attempt + 1, 5)
            print(f"  coupure ({e.__class__.__name__}), reprise dans {wait} s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"échec du téléchargement : {url}")


def download_extraction(ext: Extraction, raw_dir: Path = RAW_DIR) -> tuple[Path, Path | None]:
    def local(r: dict) -> Path:
        return raw_dir / Path(r["url"].split("?")[0]).name
    data = download(ext.data["url"], local(ext.data))
    ref = download(ext.ref["url"], local(ext.ref)) if ext.ref else None
    return data, ref
