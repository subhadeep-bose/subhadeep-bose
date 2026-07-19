"""Shared helpers: locate ffmpeg/ffprobe, probe sources, manage .editor dirs."""
import json
import shutil
import subprocess
from pathlib import Path


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit("ffmpeg not found — run `python scripts/setup.py` first")


def probe(video: Path) -> dict:
    """Return locked source properties: fps, width, height, duration."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries",
             "stream=width,height,avg_frame_rate:format=duration",
             "-of", "json", str(video)],
            capture_output=True, text=True, check=True).stdout
        data = json.loads(out)
        stream = data["streams"][0]
        num, den = stream["avg_frame_rate"].split("/")
        return {
            "fps": round(int(num) / int(den), 3),
            "width": stream["width"],
            "height": stream["height"],
            "duration": float(data["format"]["duration"]),
        }
    return _probe_via_ffmpeg(video)


def _probe_via_ffmpeg(video: Path) -> dict:
    """Fallback for installs without ffprobe (e.g. the static pip build)."""
    import re
    stderr = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(video)],
        capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", stderr)
    vid = re.search(r"Video:.* (\d{2,5})x(\d{2,5})[ ,].*?([\d.]+) fps", stderr)
    if not dur or not vid:
        raise SystemExit(f"could not probe {video} — is it a valid video file?")
    h, m, s = dur.groups()
    return {
        "fps": float(vid.group(3)),
        "width": int(vid.group(1)),
        "height": int(vid.group(2)),
        "duration": int(h) * 3600 + int(m) * 60 + float(s),
    }


def workdir(video: Path) -> Path:
    d = video.resolve().parent / ".editor"
    d.mkdir(exist_ok=True)
    return d


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2))
