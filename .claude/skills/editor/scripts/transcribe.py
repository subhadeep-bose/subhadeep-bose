"""Stage 1: word-level transcription with Whisper -> .editor/transcript.json"""
import argparse
from pathlib import Path

from media import workdir, write_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--model", default="small",
                    help="Whisper model size (tiny/base/small/medium/large)")
    ap.add_argument("--language", default=None)
    args = ap.parse_args()

    import whisper
    model = whisper.load_model(args.model)
    result = model.transcribe(str(args.video), word_timestamps=True,
                              language=args.language, verbose=False)

    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": round(w["start"], 3),
                "end": round(w["end"], 3),
                "prob": round(w.get("probability", 1.0), 3),
                "segment": seg["id"],
            })

    out = workdir(args.video) / "transcript.json"
    write_json(out, {"language": result["language"], "words": words})
    print(f"{len(words)} words -> {out}")


if __name__ == "__main__":
    main()
