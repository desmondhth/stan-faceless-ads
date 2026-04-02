"""
Stan — Configuration

Customize brand, output specs, and default behavior here.
"""

import os

STAN_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Output Specs ──────────────────────────────────────────────────────────────
WIDTH = 1080
HEIGHT = 1920
FPS = 30

# ─── Directories ───────────────────────────────────────────────────────────────
ASSETS_DIR = os.path.join(STAN_DIR, "assets")
VISUAL_CLIPS_DIR = os.path.join(ASSETS_DIR, "visual_clips")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
POV_DEMO_DIR = os.path.join(ASSETS_DIR, "pov_demo")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
OUTPUT_DIR = os.path.join(STAN_DIR, "output")
BRIEFS_DIR = os.path.join(STAN_DIR, "briefs")

# ─── Brand (customize for your app) ───────────────────────────────────────────
BRAND = {
    "name": "Life Reset",
    "tagline": "Turn your life into a video game",
    "bg_color": "#0D0D0D",
    "accent_color": "#FB6900",
    "text_color": "#FFFFFF",
    "end_card_headline": "Life Reset",
    "end_card_subtext": "Free for 7 days",
    "end_card_cta": "Link in bio",
}

# ─── Compositor Defaults ───────────────────────────────────────────────────────
DEFAULTS = {
    "scale_mode": "fit",        # "fit" (4:3 with black bars) or "fill" (crop to fill 9:16)
    "ken_burns": True,          # Slow zoom on visual clips
    "ken_burns_pct": 6,         # Zoom percentage (6 = 6% zoom over clip duration)
    "flash_transitions": False, # White flash between cuts (off = hard cuts)
    "clip_crop_subs": 0.82,     # Crop bottom 18% to remove subtitles
    "clip_crop_watermark": 0.06,# Crop left 6% to remove corner watermarks
    "overlay_font_size": 58,    # Default text overlay font size
    "end_card_duration": 0,     # 0 = no end card (POV demo closes the video)
}

# ─── Clip Validation Rules ─────────────────────────────────────────────────────
# These are enforced when downloading/importing clips
CLIP_RULES = [
    "Always skip first 30s of YouTube source videos (avoid intro/subscribe screens)",
    "Crop bottom 18% to remove subtitles",
    "Crop left 6% to remove corner watermarks (Crunchyroll, Funimation, etc.)",
    "Verify first frame of every clip before using in production",
    "Never use a clip with visible watermarks, subscribe prompts, or channel branding",
    "Never use the same clip twice in one video",
    "If using a specific anime, use only clips from that anime (don't mix series in one section)",
]
