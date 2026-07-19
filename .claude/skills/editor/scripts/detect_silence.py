"""Stage 2: ffmpeg silencedetect + stumble candidates -> .editor/silences.json"""
import argparse
import re
import subprocess
from pathlib import Path

from media import ffmpeg_exe, read_json, workdir, write_json


def detect_silences(video: Path, noise_db: float, min_dur: float) -> list[dict]:
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(video), "-af",
         f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True)
    silences, start = [], None
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            silences.append({"start": start, "end": float(m.group(1))})
            start = None
    return silences


def stumble_candidates(video: Path, silences: list[dict]) -> list[dict]:
    """Long gaps between words inside a sentence usually mean a restart/stumble."""
    transcript = workdir(video) / "transcript.json"
    if not transcript.exists():
        return []
    words = read_json(transcript)["words"]
    candidates = []
    for prev, cur in zip(words, words[1:]):
        gap = cur["start"] - prev["end"]
        mid_sentence = not prev["word"].endswith((".", "!", "?"))
        if gap >= 0.8 and mid_sentence:
            candidates.append({"after_word": prev["word"], "start": prev["end"],
                               "end": cur["start"], "gap": round(gap, 3)})
    return candidates


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--noise-db", type=float, default=-35.0)
    ap.add_argument("--min-duration", type=float, default=0.45)
    args = ap.parse_args()

    silences = detect_silences(args.video, args.noise_db, args.min_duration)
    stumbles = stumble_candidates(args.video, silences)
    out = workdir(args.video) / "silences.json"
    write_json(out, {"noise_db": args.noise_db, "min_duration": args.min_duration,
                     "silences": silences, "stumbles": stumbles})
    print(f"{len(silences)} silences, {len(stumbles)} stumble candidates -> {out}")


if __name__ == "__main__":
    main()
