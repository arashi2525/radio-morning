"""Yahoo Finance から主要指標の終値と前日比を取る。"""

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=10d&interval=1d"


def _quote(symbol: str) -> dict:
    req = urllib.request.Request(CHART_URL.format(quote(symbol)), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        result = json.load(res)["chart"]["result"][0]
    meta = result["meta"]
    tz = timezone(timedelta(seconds=meta.get("gmtoffset", 0)))
    price = meta["regularMarketPrice"]
    day = datetime.fromtimestamp(meta["regularMarketTime"], tz).date()

    # 前日比の基準 = 最新の取引日より前で、終値が入っている最後の日足
    closes = result["indicators"]["quote"][0]["close"]
    previous = [
        c for ts, c in zip(result["timestamp"], closes)
        if c is not None and datetime.fromtimestamp(ts, tz).date() < day
    ]
    prev = previous[-1]
    return {"price": price, "change": price - prev, "pct": (price - prev) / prev * 100, "date": day.isoformat()}


def fetch_market(config: dict) -> list[dict]:
    """取得できた指標だけ返す。失敗しても番組は止めない。"""
    rows = []
    for entry in config.get("market") or []:
        try:
            rows.append({"name": entry["name"], "unit": entry.get("unit", ""), **_quote(entry["symbol"])})
        except Exception as e:  # ネットワーク・形式変更・レート制限など
            print(f"  [warn] {entry['name']}: 市場データを取得できませんでした ({e})")
    print(f"  市場データ: {len(rows)}件")
    return rows
