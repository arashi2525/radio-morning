"""エピソード一覧(episodes.json)を更新し、ポッドキャストRSSとトップページを書き出す。"""

import html
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES)
ET.register_namespace("atom", ATOM)


def base_url(config: dict) -> str:
    url = config["podcast"].get("base_url")
    if not url:
        repo = os.environ.get("GITHUB_REPOSITORY")  # "owner/repo"
        if repo:
            owner, name = repo.split("/", 1)
            url = f"https://{owner.lower()}.github.io/{name}"
        else:
            url = "http://localhost:8000"
    return url.rstrip("/") + "/"


def update_episodes(config: dict, site: Path, episode: dict) -> list[dict]:
    """同じ日付の回は置き換え、古い回はMP3ごと削除する。新しい順のリストを返す。"""
    index = site / "episodes.json"
    episodes = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    episodes = [e for e in episodes if e["date"] != episode["date"]] + [episode]
    episodes.sort(key=lambda e: e["date"], reverse=True)

    keep = config["podcast"].get("keep_episodes", 30)
    for old in episodes[keep:]:
        (site / old["file"]).unlink(missing_ok=True)
    episodes = episodes[:keep]

    index.write_text(json.dumps(episodes, ensure_ascii=False, indent=2), encoding="utf-8")
    return episodes


def _sub(parent, tag, text=None, **attrib):
    el = ET.SubElement(parent, tag, attrib)
    el.text = text
    return el


def write_feed(config: dict, site: Path, episodes: list[dict]) -> None:
    pod = config["podcast"]
    base = base_url(config)

    rss = ET.Element("rss", version="2.0")
    ch = _sub(rss, "channel")
    _sub(ch, "title", pod["title"])
    _sub(ch, "link", base)
    _sub(ch, "description", pod["description"])
    _sub(ch, "language", pod.get("language", "ja"))
    _sub(ch, f"{{{ATOM}}}link", href=urljoin(base, "feed.xml"), rel="self", type="application/rss+xml")
    _sub(ch, f"{{{ITUNES}}}author", pod.get("author", ""))
    _sub(ch, f"{{{ITUNES}}}explicit", "false")
    ET.SubElement(ch, f"{{{ITUNES}}}category", {"text": pod.get("category", "News")})
    if pod.get("cover_image"):
        _sub(ch, f"{{{ITUNES}}}image", href=urljoin(base, pod["cover_image"]))

    for ep in episodes:
        url = urljoin(base, ep["file"])
        item = _sub(ch, "item")
        _sub(item, "title", ep["title"])
        _sub(item, "description", ep["description"])
        _sub(item, "guid", url, isPermaLink="true")
        _sub(item, "pubDate", format_datetime(datetime.fromisoformat(ep["published"])))
        _sub(item, "enclosure", url=url, length=str(ep["bytes"]), type="audio/mpeg")
        _sub(item, f"{{{ITUNES}}}duration", str(ep["seconds"]))

    ET.indent(rss)
    ET.ElementTree(rss).write(site / "feed.xml", encoding="utf-8", xml_declaration=True)

    rows = "\n".join(
        f'<li><p>{html.escape(ep["title"])}</p>'
        f'<audio controls preload="none" src="{html.escape(ep["file"])}"></audio></li>'
        for ep in episodes
    )
    (site / "index.html").write_text(
        f"""<!doctype html>
<html lang="ja">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(pod["title"])}</title>
<link rel="alternate" type="application/rss+xml" href="feed.xml">
<style>body{{font-family:sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem}}
ul{{list-style:none;padding:0}}audio{{width:100%}}</style>
<h1>{html.escape(pod["title"])}</h1>
<p>{html.escape(pod["description"])}</p>
<p>ポッドキャストアプリに登録: <a href="feed.xml">{html.escape(urljoin(base, "feed.xml"))}</a></p>
<ul>
{rows}
</ul>
</html>
""",
        encoding="utf-8",
    )
