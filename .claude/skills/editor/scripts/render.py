"""Stage 5: render the cutlist at locked source fps/dimensions.

Prefers the Remotion project bundled with the skill; falls back to a
pure-ffmpeg segment-concat render when node/npx is unavailable.
Output: <video-dir>/<name>.edited.mp4
"""
import argparse
import shutil
import subprocess
from pathlib import Path

from media import ffmpeg_exe, read_json, workdir

REMOTION_DIR = Path(__file__).resolve().parent.parent / "remotion"


def render_remotion(cutlist: dict, output: Path) -> None:
    source = Path(cutlist["source"])
    public_copy = REMOTION_DIR / "public" / source.name
    if not public_copy.exists() or public_copy.stat().st_size != source.stat().st_size:
        shutil.copy2(source, public_copy)

    props = dict(cutlist, src=source.name)
    props_file = REMOTION_DIR / "props.json"
    props_file.write_text(__import__("json").dumps(props))
    subprocess.run(
        ["npx", "remotion", "render", "src/index.ts", "CutVideo", str(output),
         f"--props={props_file}"],
        cwd=REMOTION_DIR, check=True)


def render_ffmpeg(cutlist: dict, output: Path) -> None:
    parts = []
    for s in cutlist["segments"]:
        parts.append(
            f"between(t,{s['start']},{s['end']})")
    keep = "+".join(parts)
    vf = f"select='{keep}',setpts=N/FRAME_RATE/TB"
    af = f"aselect='{keep}',asetpts=N/SR/TB"
    subprocess.run(
        [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "warning",
         "-stats", "-i", cutlist["source"],
         "-vf", vf, "-af", af,
         "-r", str(cutlist["fps"]),
         "-s", f"{cutlist['width']}x{cutlist['height']}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", str(output)],
        check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--engine", choices=["auto", "remotion", "ffmpeg"],
                    default="auto")
    args = ap.parse_args()

    cutlist = read_json(workdir(args.video) / "cutlist.json")
    output = args.video.resolve().parent / f"{args.video.stem}.edited.mp4"

    use_remotion = args.engine == "remotion" or (
        args.engine == "auto"
        and shutil.which("npx")
        and (REMOTION_DIR / "node_modules").exists())
    if use_remotion:
        render_remotion(cutlist, output)
    else:
        render_ffmpeg(cutlist, output)
    print(f"rendered -> {output}")


if __name__ == "__main__":
    main()
