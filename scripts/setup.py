"""One-time setup for the /editor skill: ffmpeg, Whisper, Remotion, yt-dlp.

Cross-platform: macOS (brew), Linux (apt, with pip fallback), Windows
(winget, with pip fallback). Safe to re-run; every step skips work
already done.

    python scripts/setup.py
"""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REMOTION_DIR = (Path(__file__).resolve().parent.parent
                / ".claude" / "skills" / "editor" / "remotion")


def run(cmd: list[str], **kw) -> bool:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, **kw).returncode == 0


def pip_install(*packages: str) -> bool:
    return run([sys.executable, "-m", "pip", "install", "--upgrade", *packages])


def install_ffmpeg() -> None:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        print("ffmpeg: already installed")
        return
    system = platform.system()
    ok = False
    if system == "Darwin" and shutil.which("brew"):
        ok = run(["brew", "install", "ffmpeg"])
    elif system == "Linux" and shutil.which("apt-get"):
        ok = (run(["sudo", "apt-get", "update", "-qq"])
              and run(["sudo", "apt-get", "install", "-y", "-qq", "ffmpeg"]))
    elif system == "Windows" and shutil.which("winget"):
        ok = run(["winget", "install", "--id", "Gyan.FFmpeg", "-e",
                  "--accept-source-agreements", "--accept-package-agreements"])
    if not ok:
        print("ffmpeg: package manager unavailable, using static pip build")
        pip_install("imageio-ffmpeg")
        print("  note: imageio-ffmpeg has no ffprobe; install ffmpeg properly "
              "for full QA support")


def install_python_deps() -> None:
    print("python: installing openai-whisper + yt-dlp")
    if not pip_install("openai-whisper", "yt-dlp"):
        raise SystemExit("pip install failed — fix the error above and re-run")


def install_remotion() -> None:
    if (REMOTION_DIR / "node_modules").exists():
        print("remotion: already installed")
        return
    npm = shutil.which("npm")
    if not npm:
        print("remotion: npm not found — install Node.js (https://nodejs.org) "
              "and re-run; the editor will fall back to ffmpeg rendering "
              "until then")
        return
    if not run([npm, "install"], cwd=REMOTION_DIR):
        print("remotion: npm install failed; ffmpeg fallback will be used")


def main() -> None:
    print(f"Setting up /editor on {platform.system()}...")
    install_ffmpeg()
    install_python_deps()
    install_remotion()
    print("\nDone. Try: python .claude/skills/editor/scripts/transcribe.py <video>")


if __name__ == "__main__":
    main()
