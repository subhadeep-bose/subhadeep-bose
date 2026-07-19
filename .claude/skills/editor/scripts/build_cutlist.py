"""Stage 4: materialize the cut list -> .editor/cutlist.json

Claude decides keep-spans from validated.json plus user directives, then
calls this with explicit --keep spans. With no --keep args, every
validated segment is used. fps/width/height are probed from the source
and locked into the cutlist (hard rule: the render never deviates).
"""
import argparse
from pathlib import Path

from media import probe, read_json, workdir, write_json


def parse_span(spec: str) -> dict:
    start, end = spec.split("-")
    span = {"start": float(start), "end": float(end)}
    if span["end"] <= span["start"]:
        raise SystemExit(f"bad span {spec}: end must be after start")
    return span


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--keep", action="append", default=[],
                    metavar="START-END", help="keep span in seconds, repeatable")
    args = ap.parse_args()

    wd = workdir(args.video)
    src = probe(args.video)

    if args.keep:
        segments = sorted((parse_span(s) for s in args.keep),
                          key=lambda s: s["start"])
    else:
        segments = read_json(wd / "validated.json")["segments"]

    segments = [{"start": max(0.0, s["start"]),
                 "end": min(src["duration"], s["end"])} for s in segments]
    total = sum(s["end"] - s["start"] for s in segments)

    out = wd / "cutlist.json"
    write_json(out, {
        "source": str(args.video.resolve()),
        "fps": src["fps"], "width": src["width"], "height": src["height"],
        "segments": segments,
        "expected_duration": round(total, 3),
    })
    print(f"{len(segments)} segments, {total:.1f}s "
          f"(locked {src['width']}x{src['height']} @ {src['fps']}fps) -> {out}")


if __name__ == "__main__":
    main()
