"""Stage 6: QA the rendered output -> .editor/qa_report.json

One invocation = one QA pass. Claude runs up to five passes, patching
the cutlist / re-rendering between passes until the report is clean.
"""
import argparse
import re
import subprocess
from pathlib import Path

from media import ffmpeg_exe, probe, read_json, workdir, write_json


def loudness_stats(video: Path) -> dict:
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(video),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True)
    stats = {}
    for key in ("mean_volume", "max_volume"):
        m = re.search(rf"{key}: (-?[\d.]+) dB", proc.stderr)
        if m:
            stats[key] = float(m.group(1))
    return stats


def dead_air(video: Path, min_dur: float) -> list[dict]:
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(video),
         "-af", f"silencedetect=noise=-35dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True)
    gaps, start = [], None
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            gaps.append({"start": start, "end": float(m.group(1))})
            start = None
    return gaps


def black_frames(video: Path) -> list[dict]:
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(video),
         "-vf", "blackdetect=d=0.2:pix_th=0.10", "-f", "null", "-"],
        capture_output=True, text=True)
    return [{"start": float(m.group(1)), "duration": float(m.group(2))}
            for m in re.finditer(
                r"black_start:([\d.]+).*?black_duration:([\d.]+)", proc.stderr)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path, help="the ORIGINAL source video")
    ap.add_argument("--reference", type=Path, default=None,
                    help="example clip to compare loudness/pacing against")
    args = ap.parse_args()

    wd = workdir(args.video)
    cutlist = read_json(wd / "cutlist.json")
    output = args.video.resolve().parent / f"{args.video.stem}.edited.mp4"
    if not output.exists():
        raise SystemExit(f"no rendered output at {output} — run render.py first")

    out_props = probe(output)
    failures, checks = [], {}

    checks["fps_locked"] = abs(out_props["fps"] - cutlist["fps"]) < 0.05
    checks["dimensions_locked"] = (out_props["width"] == cutlist["width"]
                                   and out_props["height"] == cutlist["height"])
    drift = abs(out_props["duration"] - cutlist["expected_duration"])
    checks["duration_matches_cutlist"] = drift < 1.0
    blacks = black_frames(output)
    checks["no_black_frames"] = not blacks
    gaps = dead_air(output, min_dur=1.0)
    checks["no_dead_air"] = not gaps

    if args.reference:
        ref_loud = loudness_stats(args.reference)
        out_loud = loudness_stats(output)
        delta = abs(ref_loud.get("mean_volume", 0) - out_loud.get("mean_volume", 0))
        checks["loudness_near_reference"] = delta < 6.0
        checks["reference_stats"] = {"reference": ref_loud, "output": out_loud}

    for name, ok in checks.items():
        if ok is False:
            failures.append(name)

    report = {"output": str(output), "checks": checks, "failures": failures,
              "black_frames": blacks, "dead_air": gaps,
              "duration": {"actual": out_props["duration"],
                           "expected": cutlist["expected_duration"]}}
    write_json(wd / "qa_report.json", report)
    status = "CLEAN" if not failures else f"FAILURES: {', '.join(failures)}"
    print(f"QA {status} -> {wd / 'qa_report.json'}")


if __name__ == "__main__":
    main()
