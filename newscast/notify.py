"""python -m newscast.notify : 今日の回の見出し一覧を ntfy でスマホに通知する。

公開ページが見られるようになってから送るため、GitHub Actions では push の後に実行する。
通知先のトピック名は環境変数 NTFY_TOPIC(GitHub の Secret)で渡す。未設定なら何もしない。
"""

import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import yaml

from .feed import base_url, load_episodes

SITE = Path("docs")
SERVER = "https://ntfy.sh"
MAX_CHARS = 1200  # ntfy の本文上限(4KB)に収まるよう余裕をもって切る

TAG_RE = re.compile(r"<[^>]+>")
BLOCK_RE = re.compile(r"<h2>(.*?)</h2>|<li>(?:\s*<p>)?\s*<strong>(.*?)</strong>|<p>(.*?)</p>", re.S)


def _text(fragment: str) -> str:
    return html.unescape(TAG_RE.sub("", fragment)).strip()


def headlines(body: str) -> str:
    """文字版HTMLから「【コーナー】・見出し」の一覧を作る。クイズは問題文だけ載せる。"""
    body = body.split("<details>")[0]  # 正解と解説は通知に載せない
    lines, section, section_has_items = [], "", False
    for h2, item, para in BLOCK_RE.findall(body):
        if h2:
            if _text(h2) == "マーケット概況":  # 数値表はページで見てもらう
                section = ""
                continue
            section, section_has_items = _text(h2), False
            lines.append(f"\n【{section}】")
        elif item and section:
            lines.append(f"・{_text(item).rstrip(':：')}")
            section_has_items = True
        elif para and section and not section_has_items:
            lines.append(_text(para))  # 箇条書きのない節(クイズ)は最初の段落を載せる
            section_has_items = True
    text = "\n".join(lines).strip()
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS].rstrip() + "…"


def _wait_until_published(url: str, timeout: int = 300) -> None:
    """GitHub Pages の反映を待つ(最大5分)。間に合わなくても通知は送る。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10):
                return
        except Exception:
            time.sleep(15)
    print(f"  [warn] ページの公開を確認できないまま通知します: {url}")


def send(topic: str, title: str, message: str, click: str, audio: str) -> None:
    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "click": click,
        "tags": ["radio"],
        "actions": [
            {"action": "view", "label": "文字版を読む", "url": click},
            {"action": "view", "label": "音声を聴く", "url": audio},
        ],
    }
    req = urllib.request.Request(
        SERVER,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        res.read()


def main() -> int:
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC が未設定のため通知しません。")
        return 0

    config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")
    episode = next((e for e in load_episodes(SITE) if e["date"] == today), None)
    if not episode or not episode.get("body"):
        print("今日の文字版がないため通知しません。")
        return 0

    base = base_url(config)
    page = urljoin(base, episode["page"])
    _wait_until_published(page)
    try:
        send(
            topic,
            f"{config['podcast']['title']} {episode['title']}",
            headlines(episode["body"]),
            click=page,
            audio=urljoin(base, episode["file"]),
        )
    except Exception as e:  # 通知の失敗で配信自体を失敗扱いにしない
        print(f"  [warn] 通知を送れませんでした ({e})")
        return 0
    print("通知を送りました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
