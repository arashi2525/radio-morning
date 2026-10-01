"""RSSからジャンルごとに新着記事を集める。"""

import calendar
import html
import re
import socket
import time
from itertools import zip_longest

import feedparser

TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub("", text or ""))).strip()


def _timestamp(entry) -> float | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return calendar.timegm(parsed) if parsed else None


def fetch_news(config: dict) -> list[dict]:
    """[{"name": ジャンル名, "items": [{title, summary, link, source}]}] を返す。"""
    opts = config.get("fetch", {})
    cutoff = time.time() - opts.get("lookback_hours", 24) * 3600
    max_summary = opts.get("max_summary_chars", 400)
    socket.setdefaulttimeout(20)

    seen_links = set()
    genres = []
    for genre in config["genres"]:
        per_source = []
        for source in genre["sources"]:
            feed = feedparser.parse(source["url"])
            if not feed.entries:
                reason = getattr(feed, "bozo_exception", "記事なし")
                print(f"  [warn] {source['name']}: 取得できませんでした ({reason})")
                continue
            items = []
            per_source.append(items)
            for entry in feed.entries:
                link = entry.get("link", "")
                ts = _timestamp(entry)
                if (ts is not None and ts < cutoff) or link in seen_links:
                    continue
                seen_links.add(link)
                items.append(
                    {
                        "title": _clean(entry.get("title", "")),
                        "summary": _clean(entry.get("summary", ""))[:max_summary],
                        "link": link,
                        "source": source["name"],
                        "ts": ts or 0,
                    }
                )
            if not items:
                print(f"  [warn] {source['name']}: 期間内の新着なし(フィードが更新停止していないか確認)")
            items.sort(key=lambda i: i["ts"], reverse=True)
        # 1つのソースに偏らないよう、各ソースの新しい順に1件ずつ交互に取る
        items = [i for group in zip_longest(*per_source) for i in group if i]
        items = items[: genre.get("max_items", 5)]
        print(f"  {genre['name']}: {len(items)}件")
        if items:
            genres.append({"name": genre["name"], "items": items})
    return genres
