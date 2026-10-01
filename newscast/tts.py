"""原稿をMP3にする(edge-tts: APIキー不要のMicrosoft Edge読み上げ音声)。"""

import asyncio
from pathlib import Path

import edge_tts


def synthesize(config: dict, text: str, path: Path) -> None:
    opts = config.get("tts", {})
    communicate = edge_tts.Communicate(
        text,
        voice=opts.get("voice", "ja-JP-NanamiNeural"),
        rate=opts.get("rate", "+0%"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(communicate.save(str(path)))
