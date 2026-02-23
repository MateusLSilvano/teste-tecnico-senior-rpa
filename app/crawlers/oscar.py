# app/crawlers/oscar.py
from __future__ import annotations

from typing import Any, Iterable

import httpx

BASE = "https://www.scrapethissite.com/pages/ajax-javascript/"


def _to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip()
        if not s:
            return default
        return int(float(s))
    except Exception:
        return default


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "sim", "s", "winner", "won"}


def normalize_oscar_payload(payload: Any, year: int) -> list[dict[str, Any]]:
    data: Any = None

    if isinstance(payload, list):
        data = payload
    elif isinstance(payload, dict):
        data = payload.get("data")
        if data is None:
            data = payload.get("results")
        if data is None:
            data = payload.get("movies")
    else:
        return []

    if not isinstance(data, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        title = (item.get("title") or item.get("film") or "").strip()
        if not title:
            continue

        nominations = _to_int(item.get("nominations"))
        awards = _to_int(item.get("awards"))
        best_picture = _to_bool(item.get("best_picture") or item.get("bestPicture") or item.get("best-picture"))

        rows.append(
            {
                "year": int(year),
                "title": title,
                "nominations": nominations,
                "awards": awards,
                "best_picture": best_picture,
            }
        )

    return rows


async def fetch_oscar(
    years: Iterable[int] | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """
    Busca por anos (default 2010-2015) via endpoint AJAX.
    Permite injetar client (para testes sem rede).
    """
    years_list = list(years) if years is not None else [2010, 2011, 2012, 2013, 2014, 2015]

    created_client = False
    if client is None:
        created_client = True
        client = httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            },
        )

    try:
        out: list[dict[str, Any]] = []
        for y in years_list:
            r = await client.get(BASE, params={"ajax": "true", "year": str(y)})
            r.raise_for_status()

            payload = r.json()
            rows = normalize_oscar_payload(payload, int(y))

            # fail-fast “senior”: ano sem dados é suspeito
            if not rows:
                raise RuntimeError(f"Oscar AJAX returned 0 rows for year={y}. Payload keys={list(payload.keys())}")

            out.extend(rows)
        return out
    finally:
        if created_client:
            await client.aclose()