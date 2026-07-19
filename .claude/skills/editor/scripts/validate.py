"""Stage 3: drop non-speech + duplicate takes -> .editor/validated.json"""
import argparse
import difflib
import re
from pathlib import Path

from media import read_json, workdir, write_json

FILLERS = {"um", "uh", "umm", "uhh", "er", "erm", "hmm", "mm", "mhm", "ah"}
NON_SPEECH = re.compile(r"^\[.*\]$|^\(.*\)$")  # [breath], (clears throat), etc.


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def mark_non_speech(words: list[dict]) -> None:
    for w in words:
        token = normalize(w["word"])
        if NON_SPEECH.match(w["word"]) or token in FILLERS or w["prob"] < 0.2:
            w["drop"] = "non-speech"


def sentences(words: list[dict]) -> list[dict]:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["word"].endswith((".", "!", "?")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"text": normalize(" ".join(
                w["word"] for w in s if not w.get("drop"))),
             "start": s[0]["start"], "end": s[-1]["end"], "words": s}
            for s in out if s]


def mark_duplicate_takes(words: list[dict], threshold: float) -> int:
    """Adjacent near-identical sentences are retakes; keep the last one."""
    sents = sentences(words)
    dropped = 0
    for prev, cur in zip(sents, sents[1:]):
        if not prev["text"] or not cur["text"]:
            continue
        ratio = difflib.SequenceMatcher(None, prev["text"], cur["text"]).ratio()
        if ratio >= threshold:
            for w in prev["words"]:
                w["drop"] = "duplicate-take"
            dropped += 1
    return dropped


def kept_segments(words: list[dict], pad: float) -> list[dict]:
    segs = []
    for w in words:
        if w.get("drop"):
            continue
        if segs and w["start"] - segs[-1]["end"] <= pad:
            segs[-1]["end"] = w["end"]
        else:
            segs.append({"start": w["start"], "end": w["end"]})
    return [{"start": round(max(0, s["start"] - 0.1), 3),
             "end": round(s["end"] + 0.15, 3)} for s in segs]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--similarity", type=float, default=0.85,
                    help="duplicate-take similarity threshold")
    ap.add_argument("--join-gap", type=float, default=0.6,
                    help="gaps shorter than this stay in one segment")
    args = ap.parse_args()

    wd = workdir(args.video)
    words = read_json(wd / "transcript.json")["words"]
    mark_non_speech(words)
    dup_count = mark_duplicate_takes(words, args.similarity)
    segments = kept_segments(words, args.join_gap)

    drops = [{"word": w["word"], "start": w["start"], "end": w["end"],
              "reason": w["drop"]} for w in words if w.get("drop")]
    out = wd / "validated.json"
    write_json(out, {"segments": segments, "drops": drops,
                     "duplicate_takes_dropped": dup_count})
    print(f"{len(segments)} keep-segments, {len(drops)} words dropped "
          f"({dup_count} duplicate takes) -> {out}")


if __name__ == "__main__":
    main()
