"""Voice the narration with edge-tts and write the timings the video uses.

    python tts.py            # needs: pip install edge-tts

Reads narration.json; writes public/audio/<scene>.mp3 and src/narration.generated.json (each scene's duration and
its caption lines, timed from the voice's word boundaries). `say` is what the voice reads when it must differ from
the caption text (pronunciation); captions always show `text`.
"""

import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "public" / "audio"
OUT = HERE / "src" / "narration.generated.json"
WORDS_PER_LINE = 11


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def caption_lines(text: str, words: list[dict]) -> list[dict]:
    """Split the caption text into lines and time each from the spoken words (same order, maybe different spelling)."""
    shown = text.split()
    # break at sentence ends, at commas once a line is long enough, and at WORDS_PER_LINE
    spans, i = [], 0
    for j, word in enumerate(shown):
        size = j - i + 1
        if (word[-1] in ".:?" and size >= 3) or (word[-1] == "," and size >= 6) or size >= WORDS_PER_LINE:
            spans.append((i, j + 1))
            i = j + 1
    if i < len(shown):
        spans.append((i, len(shown)))
    lines, n = [], len(words)
    for i, j in spans:
        # map caption word positions onto spoken word positions proportionally
        a = min(n - 1, round(i * n / len(shown)))
        b = min(n - 1, max(a, round(j * n / len(shown)) - 1))
        lines.append({"text": " ".join(shown[i:j]), "start": words[a]["start"], "end": words[b]["end"]})
    for prev, nxt in zip(lines, lines[1:]):
        prev["end"] = nxt["start"]
    return lines


async def voice(scene: dict, cfg: dict) -> dict:
    path = AUDIO / f"{scene['id']}.mp3"
    comm = edge_tts.Communicate(scene.get("say", scene["text"]), cfg["voice"], rate=cfg.get("rate", "+0%"),
                                boundary="WordBoundary")
    words = []
    with path.open("wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append({"text": chunk["text"], "start": start, "end": start + chunk["duration"] / 1e7})
    return {"id": scene["id"], "text": scene["text"], "audio": f"audio/{path.name}", "duration": duration(path),
            "captions": caption_lines(scene["text"], words)}


async def main() -> None:
    cfg = json.loads((HERE / "narration.json").read_text(encoding="utf-8"))
    AUDIO.mkdir(parents=True, exist_ok=True)
    scenes = [await voice(s, cfg) for s in cfg["scenes"]]
    OUT.write_text(json.dumps({"voice": cfg["voice"], "scenes": scenes}, indent=1), encoding="utf-8")
    for s in scenes:
        print(f"{s['id']:<11} {s['duration']:5.1f} s")
    print(f"total voice {sum(s['duration'] for s in scenes):.1f} s")


if __name__ == "__main__":
    asyncio.run(main())
