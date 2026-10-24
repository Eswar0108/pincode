"""Topic Collector — fetches trending topics from Google Trends RSS + Hacker News,
scores them, and persists to the factory database."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.backend.db import dict_from_row, get_connection

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEO = "US"
RSS_URL = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={GEO}"
HN_API = "https://hn.algolia.com/api/v1/search_by_date?tags=front_page&hitsPerPage=100"

TECH_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "gpt", "claude", "gemini",
    "coding", "programming", "developer", "software", "app", "github",
    "python", "javascript", "react", "vue", "node", "rust", "swift",
    "startup", "tech", "tool", "api", "automation", "bot", "chrome",
    "iphone", "android", "windows", "macos", "linux", "crypto",
    "bitcoin", "blockchain", "nft", "saas", "productivity",
]

LOW_VALUE_KEYWORDS = [
    "lottery", "powerball", "mega millions", "weather", "horoscope",
    "obituary", "mugshot", "arrest", "crash", "fire", "shooting",
]


@dataclass
class RawTopic:
    title: str
    link: str
    pub_date: str
    description: str | None = None
    source: str = "unknown"
    approx_traffic: str | None = None
    points: int = 0


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


async def fetch_google_trends() -> list[RawTopic]:
    """Fetch from Google Trends daily RSS. Returns empty list on failure."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                RSS_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/rss+xml, application/xml, text/xml",
                },
            )
            resp.raise_for_status()
            xml = resp.text
    except Exception as exc:  # noqa: BLE001
        print(f"[topic_collector] Google Trends failed: {exc}")
        return []

    items: list[RawTopic] = []
    for block in xml.split("<item>")[1:]:
        end_item = block.find("</item>")
        item_xml = block[:end_item] if end_item > -1 else block

        def _extract(tag: str) -> str:
            m = re.search(rf"<{tag}>(.*?)</{tag}>", item_xml, re.DOTALL)
            if not m:
                return ""
            return m.group(1).replace("<![CDATA[", "").replace("]]>", "").strip()

        title = _extract("title")
        link = _extract("link")
        pub_date = _extract("pubDate")
        description = _extract("description") or None

        if title:
            items.append(
                RawTopic(
                    title=title,
                    link=link,
                    pub_date=pub_date,
                    description=description,
                    source="google-trends",
                )
            )

    print(f"[topic_collector] Google Trends RSS: parsed {len(items)} topics")
    return items[:100]


async def fetch_hacker_news() -> list[RawTopic]:
    """Fetch from Hacker News Algolia API. Returns empty list on failure."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                HN_API,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"[topic_collector] Hacker News failed: {exc}")
        return []

    hits = data.get("hits", []) or []
    items: list[RawTopic] = []
    for h in hits:
        title = h.get("title") or h.get("story_title") or ""
        if not title:
            continue
        items.append(
            RawTopic(
                title=title,
                link=h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
                pub_date=h.get("created_at", datetime.now(timezone.utc).isoformat()),
                description=None,
                source="hacker-news",
                approx_traffic=f"{h.get('num_comments', 0)} comments",
                points=h.get("points", 0),
            )
        )

    print(f"[topic_collector] Hacker News Algolia: parsed {len(items)} topics")
    return items


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_topic(item: RawTopic, rank: int) -> float:
    """Score a topic (higher = better). Tech keywords boost, low-value penalize."""
    text = f"{item.title} {item.description or ''}".lower()
    score = 100.0
    score -= rank * 0.5  # earlier rank = higher score

    tech_hits = sum(1 for kw in TECH_KEYWORDS if kw in text)
    score += tech_hits * 15

    low_hits = sum(1 for kw in LOW_VALUE_KEYWORDS if kw in text)
    score -= low_hits * 25

    if len(item.title) <= 40:
        score += 10
    if len(item.title) > 80:
        score -= 10

    return round(max(0.0, score), 2)


# ---------------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------------


import sqlite3  # noqa: E402


def save_topics(topics: list[RawTopic]) -> int:
    """Save scored topics to the database. Returns count of new rows inserted."""
    conn = get_connection()
    inserted = 0
    try:
        for idx, item in enumerate(topics, start=1):
            score = score_topic(item, idx)
            topic_id = f"topic_{abs(hash((item.title, item.source, item.pub_date))) & 0xFFFFFFFF:08x}"

            try:
                conn.execute(
                    """
                    INSERT INTO topics (id, title, source, score, rank, url, fetched_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        topic_id,
                        item.title,
                        item.source,
                        score,
                        idx,
                        item.link,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # Duplicate — skip
                pass
        conn.commit()
    finally:
        conn.close()
    return inserted


def get_topics(limit: int = 10, status: str | None = None) -> list[dict]:
    """Retrieve topics ordered by score descending."""
    conn = get_connection()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM topics WHERE status = ? ORDER BY score DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM topics ORDER BY score DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict_from_row(r) for r in rows]
    finally:
        conn.close()


def select_topics(topic_ids: list[str]) -> int:
    """Mark topics as 'selected' for rendering."""
    conn = get_connection()
    try:
        conn.executemany(
            "UPDATE topics SET status = 'selected' WHERE id = ?",
            [(tid,) for tid in topic_ids],
        )
        conn.commit()
        return conn.total_changes
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


async def collect_topics(limit: int = 100) -> dict[str, Any]:
    """Fetch from all sources, score, save to DB, return summary."""
    gt, hn = await asyncio.gather(
        fetch_google_trends(),
        fetch_hacker_news(),
    )

    all_topics = gt + hn

    if not all_topics:
        print("[topic_collector] All sources failed — no topics collected")
        return {"source": "sample", "count": 0, "topics": []}

    # Score and sort
    for idx, item in enumerate(all_topics, start=1):
        item.score = score_topic(item, idx)

    all_topics.sort(key=lambda t: t.score, reverse=True)
    top = all_topics[:limit]

    inserted = save_topics(top)

    return {
        "source": "live" if gt else ("live" if hn else "sample"),
        "count": inserted,
        "topics": [
            {
                "id": f"topic_{abs(hash((t.title, t.source, t.pub_date))) & 0xFFFFFFFF:08x}",
                "title": t.title,
                "source": t.source,
                "score": t.score,
                "rank": idx + 1,
                "url": t.link,
                "approx_traffic": t.approx_traffic,
            }
            for idx, t in enumerate(top)
        ],
    }