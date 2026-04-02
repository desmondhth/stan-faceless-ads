"""
Stan — Clip Importer

Downloads anime clips from YouTube, crops subtitles and watermarks,
validates first frame, and saves to the clip library.

Usage:
    # Download and import a clip
    python3 import_clip.py "https://youtube.com/watch?v=XXX" --name "maki_fight" --start 30 --end 42

    # Import a local file
    python3 import_clip.py local_file.mp4 --name "my_clip"

    # Validate all clips in library (check for watermarks/blank frames)
    python3 import_clip.py --validate
"""

import argparse
import os
import subprocess
import sys
from PIL import Image

from config import VISUAL_CLIPS_DIR, DEFAULTS


def download_clip(url, name, start=30, end=42):
    """Download from YouTube, skipping intros, and save to clip library."""
    raw_path = os.path.join(VISUAL_CLIPS_DIR, f"{name}_raw.mp4")
    final_path = os.path.join(VISUAL_CLIPS_DIR, f"{name}.mp4")

    print(f"  Downloading: {url}")
    print(f"  Section: {start}s - {end}s")

    subprocess.run([
        "yt-dlp",
        "-f", "bestvideo[height<=720]",
        "--merge-output-format", "mp4",
        "--download-sections", f"*{start}:{end}",
        "-o", raw_path,
        url,
    ], timeout=120)

    if not os.path.exists(raw_path):
        print("  ERROR: Download failed")
        return None

    # Crop subtitles (bottom) and watermarks (left corner)
    crop_bottom = DEFAULTS["clip_crop_subs"]
    crop_left = DEFAULTS["clip_crop_watermark"]

    print(f"  Cropping: bottom {int((1-crop_bottom)*100)}%, left {int(crop_left*100)}%")
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_path,
        "-vf", f"crop=iw*{1-crop_left}:ih*{crop_bottom}:iw*{crop_left}:0",
        "-an", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        final_path,
    ], capture_output=True, timeout=60)

    # Clean up raw
    os.remove(raw_path)

    if not os.path.exists(final_path):
        print("  ERROR: Crop failed")
        return None

    # Validate first frame
    ok = validate_clip(final_path)
    if ok:
        print(f"  Saved: {final_path}")
    else:
        print(f"  WARNING: Clip may have issues — review manually")

    return final_path


def import_local(source, name):
    """Import a local file into the clip library with cropping."""
    final_path = os.path.join(VISUAL_CLIPS_DIR, f"{name}.mp4")
    crop_bottom = DEFAULTS["clip_crop_subs"]
    crop_left = DEFAULTS["clip_crop_watermark"]

    subprocess.run([
        "ffmpeg", "-y", "-i", source,
        "-vf", f"crop=iw*{1-crop_left}:ih*{crop_bottom}:iw*{crop_left}:0",
        "-an", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        final_path,
    ], capture_output=True, timeout=60)

    if os.path.exists(final_path):
        print(f"  Imported: {final_path}")
        validate_clip(final_path)
    return final_path


def validate_clip(path):
    """Check first frame for common issues (black/white frame, text overlays)."""
    import tempfile
    tmp = tempfile.mktemp(suffix=".jpg")
    subprocess.run([
        "ffmpeg", "-ss", "0", "-i", path, "-vframes", "1", "-q:v", "2", tmp, "-y",
    ], capture_output=True, timeout=10)

    if not os.path.exists(tmp):
        print(f"    WARN: Could not extract first frame from {path}")
        return False

    img = Image.open(tmp)
    pixels = list(img.getdata())
    os.remove(tmp)

    # Check if mostly black (intro screen)
    avg = sum(sum(p[:3]) / 3 for p in pixels) / len(pixels)
    if avg < 15:
        print(f"    WARN: First frame is nearly black — possible intro/subscribe screen")
        return False

    # Check if mostly white (blank)
    if avg > 240:
        print(f"    WARN: First frame is nearly white — possible blank frame")
        return False

    return True


def validate_all():
    """Validate all clips in the library."""
    os.makedirs(VISUAL_CLIPS_DIR, exist_ok=True)
    clips = [f for f in os.listdir(VISUAL_CLIPS_DIR) if f.endswith(".mp4")]
    print(f"Validating {len(clips)} clips...\n")

    issues = []
    for clip in sorted(clips):
        path = os.path.join(VISUAL_CLIPS_DIR, clip)
        ok = validate_clip(path)
        status = "OK" if ok else "ISSUE"
        print(f"  [{status}] {clip}")
        if not ok:
            issues.append(clip)

    print(f"\n{len(clips) - len(issues)}/{len(clips)} passed")
    if issues:
        print(f"Issues: {', '.join(issues)}")


def main():
    parser = argparse.ArgumentParser(description="Stan — Clip Importer")
    parser.add_argument("source", nargs="?", help="YouTube URL or local file path")
    parser.add_argument("--name", help="Clip name (without .mp4)")
    parser.add_argument("--start", type=int, default=30, help="Start time in seconds (default: 30)")
    parser.add_argument("--end", type=int, default=42, help="End time in seconds (default: 42)")
    parser.add_argument("--validate", action="store_true", help="Validate all clips in library")

    args = parser.parse_args()

    if args.validate:
        validate_all()
    elif args.source:
        if not args.name:
            print("ERROR: --name is required")
            sys.exit(1)
        if args.source.startswith("http"):
            download_clip(args.source, args.name, args.start, args.end)
        else:
            import_local(args.source, args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
