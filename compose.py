"""
Stan — Faceless Video Compositor

Composites faceless anime/illustration edit ads from a JSON brief:
1. Stitches visual clips (anime, illustration, stock footage)
2. Burns text overlays (PIL-rendered PNGs via ffmpeg overlay filter)
3. Appends POV app demo footage
4. Applies Ken Burns zoom on visual clips
5. Lays audio track underneath
6. Outputs final 9:16 vertical mp4

Usage:
    python3 compose.py brief.json [--open]

Brief JSON format:
{
    "name": "my-ad",
    "sections": [
        {"type": "visual_clip", "source": "clip.mp4", "duration": 3.5, "scale_mode": "fit",
         "text_overlays": [{"text": "Hook text", "position": "top", "appear_at": 0, "duration": 3.5, "font_size": 58}]},
        {"type": "pov_demo", "source": "pov_demo.mov", "start": 0, "end": 10}
    ],
    "audio": {"source": "track.mp3", "volume": 0.6}
}
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from config import (
    WIDTH, HEIGHT, FPS, BRAND, DEFAULTS,
    VISUAL_CLIPS_DIR, AUDIO_DIR, POV_DEMO_DIR, FONTS_DIR, OUTPUT_DIR,
)


# ============================================================
# FONT
# ============================================================

def find_font():
    """Find best available font — prefers Montserrat ExtraBold."""
    priority = [
        os.path.join(FONTS_DIR, "Montserrat-ExtraBold.ttf"),
        os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"),
    ]
    fallbacks = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    ]
    for path in priority + fallbacks:
        if os.path.exists(path):
            return path
    return None


def get_font(size):
    """Get PIL font at given size."""
    path = find_font()
    try:
        return ImageFont.truetype(path, size) if path else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


# ============================================================
# TEXT RENDERING
# ============================================================

def render_text_frame(text, bg="black", font_size=None, position="center"):
    """Render a full-frame image with centered text. Returns PIL Image."""
    if bg == "white":
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        color = "#000000"
    else:
        img = Image.new("RGB", (WIDTH, HEIGHT), (13, 13, 13))
        color = BRAND["text_color"]

    draw = ImageDraw.Draw(img)

    if font_size is None:
        text_len = len(text)
        font_size = 80 if text_len < 30 else 68 if text_len < 50 else 58 if text_len < 80 else 48 if text_len < 150 else 40

    font = get_font(font_size)
    lines = _wrap_text(draw, text, font, WIDTH - 100)
    _draw_text_block(draw, lines, font, WIDTH, HEIGHT, position, color)
    return img


def render_end_card():
    """Render branded end card."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (13, 13, 13))
    draw = ImageDraw.Draw(img)

    font_lg = get_font(80)
    font_md = get_font(48)
    font_sm = get_font(36)

    headline = BRAND["end_card_headline"]
    subtext = BRAND["end_card_subtext"]
    cta = BRAND["end_card_cta"]

    bbox = draw.textbbox((0, 0), headline, font=font_lg)
    draw.text(((WIDTH - bbox[2] + bbox[0]) // 2, HEIGHT // 2 - 120), headline, font=font_lg, fill=BRAND["accent_color"])

    bbox = draw.textbbox((0, 0), subtext, font=font_md)
    draw.text(((WIDTH - bbox[2] + bbox[0]) // 2, HEIGHT // 2), subtext, font=font_md, fill=BRAND["text_color"])

    bbox = draw.textbbox((0, 0), cta, font=font_sm)
    draw.text(((WIDTH - bbox[2] + bbox[0]) // 2, HEIGHT // 2 + 80), cta, font=font_sm, fill="#888888")
    return img


def render_overlay_png(text, position, font_size, tmp_dir, idx):
    """Render text as transparent PNG for ffmpeg overlay. Returns path."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_font(font_size)
    lines = _wrap_text(draw, text, font, WIDTH - 100)
    _draw_text_block(draw, lines, font, WIDTH, HEIGHT, position, (255, 255, 255, 255), shadow=True)
    path = os.path.join(tmp_dir, f"ov_{idx}.png")
    img.save(path)
    return path


# ============================================================
# TEXT HELPERS
# ============================================================

def _wrap_text(draw, text, font, max_width):
    """Word-wrap text, respecting explicit \\n breaks."""
    lines = []
    for raw_line in text.split("\n"):
        words = raw_line.strip().split()
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def _draw_text_block(draw, lines, font, width, height, position, color, shadow=True):
    """Draw a block of text lines centered horizontally, positioned vertically."""
    metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        metrics.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))

    spacing = 16
    total_h = sum(m[1] for m in metrics) + (len(lines) - 1) * spacing

    if position == "top":
        y = 200
    elif position == "bottom":
        y = height - total_h - 220
    else:
        y = (height - total_h) // 2

    for i, line in enumerate(lines):
        tw, th = metrics[i]
        x = (width - tw) // 2
        if shadow:
            for sx, sy in [(4, 4), (-1, -1), (3, 0), (0, 3)]:
                draw.text((x + sx, y + sy), line, font=font, fill=(0, 0, 0, 200) if isinstance(color, tuple) else (0, 0, 0))
        draw.text((x, y), line, font=font, fill=color)
        y += th + spacing


# ============================================================
# SEGMENT BUILDERS
# ============================================================

def build_text_hook(section, tmp_dir):
    """Text-only hook segment."""
    frame = render_text_frame(section["text"], bg=section.get("bg", "black"))
    frame_path = os.path.join(tmp_dir, "hook.png")
    frame.save(frame_path)

    out = os.path.join(tmp_dir, "seg_hook.mp4")
    _run_ffmpeg([
        "-loop", "1", "-i", frame_path,
        "-t", str(section.get("duration", 3.0)), "-r", str(FPS),
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out,
    ])
    return out


def build_visual_clip(section, tmp_dir, idx):
    """Visual clip segment with scaling, Ken Burns zoom, and text overlays."""
    source = _resolve_path(section["source"], VISUAL_CLIPS_DIR)
    is_image = source.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    out = os.path.join(tmp_dir, f"seg_clip_{idx}.mp4")

    if is_image:
        img = Image.open(source).convert("RGB")
        img = _scale_to_fill(img, WIDTH, HEIGHT)
        img_path = os.path.join(tmp_dir, f"clip_{idx}.png")
        img.save(img_path)
        _run_ffmpeg([
            "-loop", "1", "-i", img_path,
            "-t", str(section.get("duration", 4.0)), "-r", str(FPS),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out,
        ])
    else:
        scale_mode = section.get("scale_mode", DEFAULTS["scale_mode"])
        duration = section.get("duration")
        dur_args = ["-t", str(duration)] if duration else []

        if scale_mode == "fit":
            vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0D0D0D"
        else:
            vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}"

        _run_ffmpeg(["-i", source, *dur_args, "-vf", vf, "-r", str(FPS), "-an",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out])

    # Ken Burns zoom
    if section.get("ken_burns", DEFAULTS["ken_burns"]):
        out = _apply_ken_burns(out, tmp_dir, f"clip_{idx}")

    # Text overlays
    overlays = section.get("text_overlays", [])
    if overlays:
        out = _burn_overlays(out, overlays, tmp_dir, f"clip_{idx}")

    return out


def build_pov_demo(section, tmp_dir):
    """POV app demo segment."""
    source = _resolve_path(section.get("source", "pov_demo.mov"), POV_DEMO_DIR)
    out = os.path.join(tmp_dir, "seg_pov.mp4")

    ss = ["-ss", str(section.get("start", 0))] if section.get("start", 0) > 0 else []
    to = ["-to", str(section["end"])] if section.get("end") else []

    _run_ffmpeg([
        *ss, "-i", source, *to,
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}",
        "-r", str(FPS), "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out,
    ])

    overlays = section.get("text_overlays", [])
    if overlays:
        out = _burn_overlays(out, overlays, tmp_dir, "pov")

    return out


def build_end_card(tmp_dir, duration=2.5):
    """Branded end card segment."""
    frame = render_end_card()
    path = os.path.join(tmp_dir, "endcard.png")
    frame.save(path)

    out = os.path.join(tmp_dir, "seg_endcard.mp4")
    _run_ffmpeg([
        "-loop", "1", "-i", path,
        "-t", str(duration), "-r", str(FPS),
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out,
    ])
    return out


# ============================================================
# EFFECTS
# ============================================================

def _apply_ken_burns(video_path, tmp_dir, prefix):
    """Subtle slow zoom-in over clip duration."""
    out = os.path.join(tmp_dir, f"{prefix}_kb.mp4")
    probe = _probe(video_path)
    if not probe:
        return video_path

    w = int(probe.get("width", WIDTH))
    h = int(probe.get("height", HEIGHT))

    _run_ffmpeg([
        "-i", video_path,
        "-vf", f"scale=iw*1.08:ih*1.08,crop={w}:{h}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out,
    ])
    return out if _valid(out) else video_path


# ============================================================
# TEXT OVERLAY BURNING
# ============================================================

def _burn_overlays(video_path, overlays, tmp_dir, prefix):
    """Burn text overlays via PIL PNGs + ffmpeg overlay filter."""
    if not overlays:
        return video_path

    vid_dur = _get_duration(video_path)
    inputs = []
    filters = []
    idx = 1

    for i, ov in enumerate(overlays):
        font_size = ov.get("font_size", DEFAULTS["overlay_font_size"])
        position = ov.get("position", "center")
        appear = ov.get("appear_at", 0)
        dur = ov.get("duration", vid_dur - appear)
        end = min(appear + dur, vid_dur)

        png = render_overlay_png(ov["text"], position, font_size, tmp_dir, f"{prefix}_{i}")
        inputs.extend(["-i", png])

        prev = f"[tmp{i}]" if i > 0 else "[0:v]"
        out_label = f"[tmp{i+1}]" if i < len(overlays) - 1 else "[outv]"
        filters.append(f"{prev}[{idx}:v]overlay=0:0:enable='between(t,{appear},{end})'{out_label}")
        idx += 1

    out = os.path.join(tmp_dir, f"{prefix}_ov.mp4")
    _run_ffmpeg([
        "-i", video_path, *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", out,
    ], timeout=120)

    return out if _valid(out) else video_path


# ============================================================
# HELPERS
# ============================================================

def _resolve_path(source, default_dir):
    """Resolve a source path — check absolute, then default_dir."""
    if os.path.isabs(source) and os.path.exists(source):
        return source
    full = os.path.join(default_dir, source)
    if os.path.exists(full):
        return full
    return source


def _scale_to_fill(img, tw, th):
    """Scale image to fill target, center-crop overflow."""
    scale = max(tw / img.width, th / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    left = (img.width - tw) // 2
    top = (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))


def _run_ffmpeg(args, timeout=60):
    """Run ffmpeg with common flags."""
    subprocess.run(["ffmpeg", "-y", *args], capture_output=True, timeout=timeout)


def _probe(video_path):
    """Get video stream info."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True,
    )
    if r.stdout:
        for s in json.loads(r.stdout).get("streams", []):
            if s["codec_type"] == "video":
                return s
    return None


def _get_duration(video_path):
    """Get video duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
        capture_output=True, text=True,
    )
    if r.stdout:
        return float(json.loads(r.stdout).get("format", {}).get("duration", 999))
    return 999


def _valid(path):
    """Check if output file exists and has content."""
    return os.path.exists(path) and os.path.getsize(path) > 0


# ============================================================
# MAIN COMPOSITOR
# ============================================================

def compose(brief):
    """Main composition. Takes brief dict, returns output path."""
    name = brief.get("name", f"stan_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    sections = brief["sections"]
    audio_cfg = brief.get("audio", {})
    end_card = brief.get("end_card")

    print(f"\n  Stan — composing: {name}")
    print(f"  Sections: {len(sections)}" + (" + end card" if end_card else ""))

    with tempfile.TemporaryDirectory(prefix="stan_") as tmp:
        segments = []

        for i, sec in enumerate(sections):
            t = sec["type"]
            print(f"  [{i+1}/{len(sections)}] {t}...", end="", flush=True)

            if t == "text_hook":
                path = build_text_hook(sec, tmp)
            elif t == "visual_clip":
                path = build_visual_clip(sec, tmp, i)
            elif t == "pov_demo":
                path = build_pov_demo(sec, tmp)
            else:
                print(f" skip ({t})")
                continue

            if _valid(path):
                segments.append(path)
                print(" done")
            else:
                print(" FAILED")

        if end_card:
            path = build_end_card(tmp, end_card.get("duration", 2.5))
            if _valid(path):
                segments.append(path)

        if not segments:
            print("  ERROR: No segments. Aborting.")
            return None

        # Concat
        print(f"  Concatenating {len(segments)} segments...", end="", flush=True)
        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w") as f:
            for p in segments:
                f.write(f"file '{p}'\n")

        concat_out = os.path.join(tmp, "concat.mp4")
        _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_list,
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", concat_out], timeout=120)
        print(" done")

        # Audio
        audio_src = audio_cfg.get("source")
        if audio_src:
            audio_src = _resolve_path(audio_src, AUDIO_DIR)
            if os.path.exists(audio_src):
                print(f"  Audio: {os.path.basename(audio_src)}...", end="", flush=True)
                vol = audio_cfg.get("volume", 0.8)
                audio_out = os.path.join(tmp, "with_audio.mp4")
                _run_ffmpeg([
                    "-i", concat_out, "-i", audio_src,
                    "-filter_complex", f"[1:a]volume={vol},atrim=0:duration=60,apad[a]",
                    "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", audio_out,
                ])
                if _valid(audio_out):
                    concat_out = audio_out
                    print(" done")
                else:
                    print(" failed (no audio)")

        # Output
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, f"{name}.mp4")
        subprocess.run(["cp", concat_out, out_path])

        dur = _get_duration(out_path)
        size = os.path.getsize(out_path) // 1024
        print(f"\n  Output: {out_path}")
        print(f"  Duration: {dur:.1f}s | Size: {size}KB")
        return out_path


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 compose.py <brief.json> [--open]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        brief = json.load(f)

    out = compose(brief)
    if out and "--open" in sys.argv:
        subprocess.run(["open", out])
