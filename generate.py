"""
Stan — CLI for generating faceless video ads.

Usage:
    # From a brief JSON
    python3 generate.py video brief.json [--open]

    # Quick mode (auto-generates brief)
    python3 generate.py quick \\
        --name "my_ad" \\
        --hook "POV: your life has a quest log" \\
        --clips clip1.mp4 clip2.mp4 \\
        --pov-start 0 --pov-end 10 \\
        --pov-text "Reset your life in 66 days" \\
        --audio track.mp3 \\
        --open

    # Batch mode (all briefs in a folder)
    python3 generate.py batch briefs/my_batch/ [--open]
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

from compose import compose
from config import OUTPUT_DIR, BRIEFS_DIR


def cmd_video(args):
    with open(args.brief) as f:
        brief = json.load(f)
    out = compose(brief)
    if out and args.open:
        subprocess.run(["open", out])


def cmd_batch(args):
    folder = args.folder
    briefs = sorted([f for f in os.listdir(folder) if f.endswith(".json")])
    print(f"Batch: {len(briefs)} briefs in {folder}\n")

    success, failed = 0, []
    for i, bf in enumerate(briefs, 1):
        with open(os.path.join(folder, bf)) as f:
            brief = json.load(f)
        print(f"[{i}/{len(briefs)}] {brief.get('name', bf)}...", end=" ", flush=True)
        try:
            out = compose(brief)
            if out:
                print(f"OK ({os.path.getsize(out) // 1024}KB)")
                success += 1
            else:
                print("FAILED")
                failed.append(bf)
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append(bf)

    print(f"\nDone: {success}/{len(briefs)} success, {len(failed)} failed")
    if failed:
        print(f"Failed: {', '.join(failed)}")


def cmd_quick(args):
    name = args.name or f"stan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    sections = []

    if args.hook:
        sections.append({
            "type": "text_hook",
            "duration": float(args.hook_duration),
            "text": args.hook,
            "bg": args.hook_bg,
        })

    if args.clips:
        for clip in args.clips:
            is_img = clip.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            sec = {"type": "visual_clip", "source": clip, "scale_mode": "fit"}
            if is_img:
                sec["duration"] = float(args.clip_duration)
            else:
                sec["duration"] = float(args.clip_duration)
            if args.clip_text:
                sec["text_overlays"] = [
                    {"text": t, "position": "top", "appear_at": 0, "font_size": 56}
                    for t in args.clip_text
                ]
            sections.append(sec)

    pov = args.pov or "pov_demo.mov"
    pov_sec = {"type": "pov_demo", "source": pov, "start": float(args.pov_start), "end": float(args.pov_end)}
    if args.pov_text:
        pov_sec["text_overlays"] = [
            {"text": t, "position": "center", "appear_at": i * 4.0, "duration": 3.5, "font_size": 44}
            for i, t in enumerate(args.pov_text)
        ]
    sections.append(pov_sec)

    brief = {"name": name, "sections": sections}
    if args.audio:
        brief["audio"] = {"source": args.audio, "volume": 0.8}

    # Save brief
    os.makedirs(BRIEFS_DIR, exist_ok=True)
    brief_path = os.path.join(BRIEFS_DIR, f"{name}.json")
    with open(brief_path, "w") as f:
        json.dump(brief, f, indent=2)
    print(f"Brief: {brief_path}")

    out = compose(brief)
    if out and args.open:
        subprocess.run(["open", out])


def main():
    parser = argparse.ArgumentParser(description="Stan — Faceless Video Ad Generator")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("video", help="From brief JSON")
    p.add_argument("brief")
    p.add_argument("--open", action="store_true")

    p = sub.add_parser("batch", help="All briefs in a folder")
    p.add_argument("folder")
    p.add_argument("--open", action="store_true")

    p = sub.add_parser("quick", help="Inline args")
    p.add_argument("--name")
    p.add_argument("--hook")
    p.add_argument("--hook-duration", default="3")
    p.add_argument("--hook-bg", default="white")
    p.add_argument("--clips", nargs="+")
    p.add_argument("--clip-duration", default="3.5")
    p.add_argument("--clip-text", nargs="+")
    p.add_argument("--pov")
    p.add_argument("--pov-start", default="0")
    p.add_argument("--pov-end", default="10")
    p.add_argument("--pov-text", nargs="+")
    p.add_argument("--audio")
    p.add_argument("--open", action="store_true")

    args = parser.parse_args()
    if args.cmd == "video":
        cmd_video(args)
    elif args.cmd == "batch":
        cmd_batch(args)
    elif args.cmd == "quick":
        cmd_quick(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
