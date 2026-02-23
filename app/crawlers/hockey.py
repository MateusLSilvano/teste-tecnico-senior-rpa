from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.scrapethissite.com/pages/forms/"

_INT_RE = re.compile(r"-?\d+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _safe_int(s: str, default: int | None = None) -> int | None:
    s = (s or "").strip().replace(",", "")
    m = _INT_RE.search(s)
    if not m:
        return default
    return int(m.group(0))


def _find_hockey_table(soup: BeautifulSoup):
    tables = soup.find_all("table")
    best = None
    best_score = -1

    # Escolhe a table cujo header bate com o esperado
    for t in tables:
        ths = [_norm(th.get_text(" ", strip=True)) for th in t.find_all("th")]
        header = " | ".join(ths)
        score = 0
        for token in ("team", "team name", "year", "wins", "losses", "goals for", "goals against"):
            if token in header:
                score += 1
        if score > best_score:
            best = t
            best_score = score

    return best


def _build_index_map(table) -> dict[str, int]:
    """
    Mapeia nomes de colunas -> índice (0-based) lendo <th>.
    Funciona mesmo se o site mudar classes/ordem levemente.
    """
    ths = table.find_all("th")
    headers = [_norm(th.get_text(" ", strip=True)) for th in ths]

    def find_idx(*needles: str) -> int:
        for i, h in enumerate(headers):
            for n in needles:
                if n in h:
                    return i
        return -1

    idx = {
        "team_name": find_idx("team name", "team"),
        "year": find_idx("year"),
        "wins": find_idx("wins", "win "),
        "losses": find_idx("losses", "loss "),
        "ot_losses": find_idx("ot losses", "ot-losses", "ot"),
        "win_pct": find_idx("win %", "pct", "percentage"),
        "goals_for": find_idx("goals for", "gf"),
        "goals_against": find_idx("goals against", "ga"),
        "goal_diff": find_idx("+ / -", "+/-", "diff", "difference"),
    }

    # Se algum não achou, deixa fallback pro layout padrão
    fallback = {
        "team_name": 0,
        "year": 1,
        "wins": 2,
        "losses": 3,
        "ot_losses": 4,
        "win_pct": 5,
        "goals_for": 6,
        "goals_against": 7,
        "goal_diff": 8,
    }
    for k, v in idx.items():
        if v == -1:
            idx[k] = fallback[k]

    return idx


def parse_hockey_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    table = _find_hockey_table(soup)
    if not table:
        return []

    idx = _build_index_map(table)

    rows: list[dict[str, Any]] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue

        def cell(i: int) -> str:
            if 0 <= i < len(tds):
                return tds[i].get_text(" ", strip=True)
            return ""

        team_name = cell(idx["team_name"]).strip()
        year = _safe_int(cell(idx["year"]))
        wins = _safe_int(cell(idx["wins"]))
        losses = _safe_int(cell(idx["losses"]))
        ot_losses = _safe_int(cell(idx["ot_losses"]), default=0)
        win_pct = cell(idx["win_pct"]).strip()
        goals_for = _safe_int(cell(idx["goals_for"]))
        goals_against = _safe_int(cell(idx["goals_against"]))
        goal_diff = _safe_int(cell(idx["goal_diff"]))

        # critérios mínimos
        if not team_name or year is None or wins is None or losses is None:
            continue
        if goals_for is None or goals_against is None or goal_diff is None:
            continue

        rows.append(
            {
                "team_name": team_name,
                "year": int(year),
                "wins": int(wins),
                "losses": int(losses),
                "ot_losses": int(ot_losses or 0),
                "win_pct": win_pct,
                "goals_for": int(goals_for),
                "goals_against": int(goals_against),
                "goal_diff": int(goal_diff),
            }
        )

    return rows


async def fetch_hockey(max_pages: int = 50) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
    }

    async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            r = await client.get(BASE, params={"page_num": page})
            r.raise_for_status()

            rows = parse_hockey_html(r.text)

            # "senior": se page1 vier 0, é bug/markup mismatch => falha o job
            if page == 1 and not rows:
                snippet = r.text[:500].replace("\n", " ")
                raise RuntimeError(f"Parsed 0 hockey rows on page 1. snippet={snippet!r}")

            if not rows:
                break

            out.extend(rows)

    return out