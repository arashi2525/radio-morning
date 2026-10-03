"""文字版(Markdown)を、公開ページ用のHTMLにする。"""

import html
import re

import markdown

from .script import ANSWER_MARKER

ANCHOR_RE = re.compile(r'<a href="([^"]*)">(.*?)</a>', re.S)

STYLE = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--accent:#0b6bcb;--up:#c62828;--down:#1565c0;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececee;--muted:#9a9aa1;--line:#2c2c30;--accent:#6aa9ff;--up:#ff7b72;--down:#79b8ff;--card:#1c1c1f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.8 system-ui,-apple-system,"Hiragino Sans","Yu Gothic UI",sans-serif}
main{max-width:42rem;margin:0 auto;padding:1.5rem 16px 4rem}
a{color:var(--accent)}
h1{font-size:1.5rem;line-height:1.4;margin:.5rem 0}
h2{font-size:1.15rem;margin:2.2rem 0 .6rem;padding-bottom:.3rem;border-bottom:1px solid var(--line)}
ul{padding-left:1.2rem}li{margin:.5rem 0}
.meta,.back{color:var(--muted);font-size:.9rem}
audio{width:100%;margin:1rem 0}
table{width:100%;border-collapse:collapse;font-size:.92rem;font-variant-numeric:tabular-nums}
th,td{padding:.35rem .5rem;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}
.up{color:var(--up)}.down{color:var(--down)}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.6rem 1rem;margin:1rem 0}
summary{cursor:pointer;font-weight:600}
.episodes{list-style:none;padding:0}.episodes li{padding:1rem 0;border-bottom:1px solid var(--line)}
.episodes p{margin:0}
"""


def page(title: str, body: str, head: str = "") -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{head}<style>{STYLE}</style>
</head>
<body><main>
{body}
</main></body>
</html>
"""


def _markdown(text: str, links: dict[str, str]) -> str:
    # 記事由来の文字列をHTMLとして解釈させないよう、先にエスケープしてから変換する
    rendered = markdown.markdown(html.escape(text, quote=False), extensions=["tables"])

    # リンクは記事idで書かせているので、実際のURLに置き換える。それ以外のリンクは文字だけ残す
    def link(m: re.Match) -> str:
        url = links.get(m.group(1))
        if not url:
            return m.group(2)
        return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{m.group(2)}</a>'

    return ANCHOR_RE.sub(link, rendered)


def _market_table(market: list[dict]) -> str:
    if not market:
        return ""
    rows = []
    for m in market:
        cls = "up" if m["change"] > 0 else "down" if m["change"] < 0 else ""
        rows.append(
            f"<tr><td>{html.escape(m['name'])}</td><td>{m['price']:,.2f}{html.escape(m['unit'])}</td>"
            f'<td class="{cls}">{m["change"]:+,.2f} ({m["pct"]:+.2f}%)</td></tr>'
        )
    return (
        "<h2>マーケット概況</h2>\n<table><thead><tr><th>指標</th><th>値</th><th>前日比</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>\n"
        '<p class="meta">各市場の直近の終値(取引中のものは現在値)。出典: Yahoo Finance</p>\n'
    )


def render_body(text: str, links: dict[str, str], market: list[dict]) -> str:
    """ページ本文とポッドキャストのショーノートに使うHTML断片。"""
    question, marker, answer = text.partition(ANSWER_MARKER)
    body = _market_table(market) + _markdown(question, links)
    if marker:
        body += f"\n<details><summary>正解と解説を見る</summary>\n{_markdown(answer, links)}\n</details>"
    return body


def episode_page(podcast_title: str, title: str, audio_file: str, body: str) -> str:
    return page(
        f"{title} | {podcast_title}",
        f'<p class="back"><a href="../">← {html.escape(podcast_title)}</a></p>\n'
        f"<h1>{html.escape(title)}</h1>\n"
        f'<audio controls preload="none" src="{html.escape(audio_file)}"></audio>\n'
        f"{body}",
    )
