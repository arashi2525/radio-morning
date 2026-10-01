"""python -m newscast : RSS収集 → 原稿 → MP3 → ポッドキャストRSS更新。"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .fetch import fetch_news

JST = ZoneInfo("Asia/Tokyo")
SITE = Path("docs")  # GitHub Pages の公開ディレクトリ


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="RSS取得だけ行い、記事一覧を表示して終了")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    now = datetime.now(JST)

    print("RSSを取得中...")
    genres = fetch_news(config)
    if not genres:
        print("新着記事がないため、今日の回は作成しません。")
        return 0
    if args.dry_run:
        for genre in genres:
            print(f"\n## {genre['name']}")
            for item in genre["items"]:
                print(f"- [{item['source']}] {item['title']}")
        return 0

    # APIキーが必要な処理は dry-run では import しない
    from mutagen.mp3 import MP3

    from .feed import update_episodes, write_feed
    from .script import write_script
    from .tts import synthesize

    print("原稿を生成中...")
    script = write_script(config, genres, now)
    print(f"  {len(script)}文字")

    date = now.strftime("%Y-%m-%d")
    mp3 = SITE / "episodes" / f"{date}.mp3"
    print("音声を合成中...")
    synthesize(config, script, mp3)
    mp3.with_suffix(".txt").write_text(script, encoding="utf-8")
    seconds = round(MP3(mp3).info.length)
    print(f"  {seconds // 60}分{seconds % 60}秒")

    headlines = "\n".join(
        f"・{item['title']}({item['source']}){item['link']}" for g in genres for item in g["items"]
    )
    episode = {
        "date": date,
        "title": f"{now.year}年{now.month}月{now.day}日のニュース",
        "description": f"参照した記事:\n{headlines}",
        "file": f"episodes/{date}.mp3",
        "bytes": mp3.stat().st_size,
        "seconds": seconds,
        "published": now.isoformat(timespec="seconds"),
    }
    episodes = update_episodes(config, SITE, episode)
    write_feed(config, SITE, episodes)
    print(f"完了: {mp3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
