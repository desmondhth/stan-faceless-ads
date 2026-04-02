# Stan — Faceless Anime Edit Ad Generator

A Python + ffmpeg pipeline that produces faceless video ads by compositing anime/illustration clips with text overlays, POV app demos, and audio tracks.

Built for producing high-volume Meta/TikTok/Reels ad creatives at scale.

## What Stan Makes

**~17 second faceless video ads** with this structure:

```
[0-3.5s]  Anime clip + text hook overlay (4:3 in 9:16 frame, text in black bar)
[3.5-7s]  Second anime clip + supporting copy
[7-17s]   POV app demo (screen recording of your app)
           Audio track plays throughout
```

**Output:** 1080x1920 (9:16 vertical) MP4, ready for Meta Ads / Instagram Reels / TikTok.

## Requirements

- **Python 3.8+** with Pillow
- **ffmpeg** (with libx264)
- **yt-dlp** (for downloading clips from YouTube)

```bash
pip install -r requirements.txt
brew install ffmpeg yt-dlp  # macOS
```

## Quick Start

### 1. Import clips

```bash
# Download an anime clip from YouTube (auto-crops subtitles + watermarks)
python3 import_clip.py "https://youtube.com/watch?v=XXXXX" --name "maki_fight" --start 30 --end 42

# Import a local file
python3 import_clip.py local_clip.mp4 --name "my_clip"
```

### 2. Add your POV demo

Record a screen recording of your app and drop it in `assets/pov_demo/`:

```bash
cp ~/your_pov_demo.mov assets/pov_demo/pov_demo.mov
```

### 3. Add audio

Drop audio tracks (MP3) into `assets/audio/`. Trim them so the beat drop aligns with ~7s (when the POV demo starts):

```bash
ffmpeg -ss 20 -t 25 -i full_track.mp3 -c:a libmp3lame -q:a 2 assets/audio/phonk_track.mp3
```

### 4. Generate a video

**From a brief JSON:**
```bash
python3 generate.py video briefs/example.json --open
```

**Quick mode (inline args):**
```bash
python3 generate.py quick \
    --name "project_maki" \
    --clips maki_fight.mp4 maki_spear.mp4 \
    --pov-start 0 --pov-end 10 \
    --audio phonk_track.mp3 \
    --open
```

**Batch mode (all briefs in a folder):**
```bash
python3 generate.py batch briefs/my_batch/
```

## Brief JSON Format

```json
{
  "name": "my_ad_name",
  "sections": [
    {
      "type": "visual_clip",
      "source": "clip_name.mp4",
      "duration": 3.5,
      "scale_mode": "fit",
      "text_overlays": [
        {
          "text": "66 Days.\nProject Maki.",
          "position": "top",
          "appear_at": 0.0,
          "duration": 3.5,
          "font_size": 66
        }
      ]
    },
    {
      "type": "pov_demo",
      "source": "pov_demo.mov",
      "start": 0,
      "end": 10
    }
  ],
  "audio": {
    "source": "track.mp3",
    "volume": 0.6
  }
}
```

### Section Types

| Type | Description |
|---|---|
| `visual_clip` | Anime/illustration clip with optional text overlay |
| `pov_demo` | App screen recording (POV demo) |
| `text_hook` | Text-only frame on solid background |

### Text Overlay Options

| Field | Default | Description |
|---|---|---|
| `text` | required | The text to display. Use `\n` for line breaks. |
| `position` | `"center"` | `"top"`, `"center"`, or `"bottom"` |
| `appear_at` | `0` | When the text appears (seconds from section start) |
| `duration` | rest of clip | How long the text shows |
| `font_size` | `58` | Font size in pixels |

### Scale Modes

| Mode | Description |
|---|---|
| `"fit"` (default) | Fits clip in 9:16 frame with black bars. Good for 16:9/4:3 clips — text goes in the black bar area. |
| `"fill"` | Crops clip to fill entire 9:16 frame. Use when clip is already vertical or you want full bleed. |

## Clip Import Rules

The `import_clip.py` tool automatically:
- **Skips YouTube intros** (downloads from 30s+ by default)
- **Crops subtitles** (bottom 18%)
- **Crops watermarks** (left 6% — catches Crunchyroll, Funimation, etc.)
- **Validates first frame** (flags black/white frames that indicate intro screens)

```bash
# Validate all clips in your library
python3 import_clip.py --validate
```

## Production Guidelines

### Clip Rules
- Never use the same clip twice in one video
- If using a specific anime, stick to that anime's clips (don't mix series)
- Clips should be 3-4 seconds each (total hook section ~7s)
- Always verify first frame before using in production

### Text Rules
- Hook text should be large (60-80px) and punchy (under 30 characters if possible)
- Use `\n` to control line breaks for visual layout
- When using `fit` mode, set position to `"top"` so text renders in the black bar above the clip
- Use pyramid-style text arrangement for visual interest

### Audio Rules
- Trim audio so the beat drop aligns with POV demo start (~7s into the video)
- Volume 0.5-0.7 works well (not too loud, not too quiet)
- Popular genres: phonk, lo-fi, epic/cinematic

### What NOT To Do
- No clips with visible watermarks (Crunchyroll, Funimation, channel logos)
- No clips with "subscribe" screens or YouTube intros
- No blank/black/white frames at any point
- No subtitles visible in the final output
- No end card needed — the POV demo closes the video

## Customization

Edit `config.py` to change:
- Brand name, colors, tagline
- Default scale mode, font size, Ken Burns zoom
- Clip cropping percentages
- Output resolution

## File Structure

```
stan-faceless-ads/
├── compose.py           # Core video compositor
├── generate.py          # CLI entry point (video/batch/quick modes)
├── import_clip.py       # YouTube clip downloader + validator
├── config.py            # Brand config + defaults
├── requirements.txt
├── assets/
│   ├── visual_clips/    # Your anime/illustration clips (.mp4)
│   ├── audio/           # Music tracks (.mp3)
│   ├── pov_demo/        # App screen recordings (.mov/.mp4)
│   └── fonts/           # Montserrat ExtraBold (included)
├── briefs/              # JSON briefs (your ad specs)
│   └── example.json
└── output/              # Generated videos land here
```

## Batch Production

For high-volume creative production, write briefs programmatically:

```python
import json

concepts = [
    ("66 Days.\nProject Maki.", "maki_fight.mp4", "maki_spear.mp4", "phonk.mp3"),
    ("Lock in.", "gojo_domain.mp4", "toji_fight.mp4", "metamorphosis.mp3"),
]

for i, (hook, clip1, clip2, audio) in enumerate(concepts, 1):
    brief = {
        "name": f"batch_{i:02d}",
        "sections": [
            {"type": "visual_clip", "source": clip1, "duration": 3.5, "scale_mode": "fit",
             "text_overlays": [{"text": hook, "position": "top", "appear_at": 0, "duration": 3.5, "font_size": 60}]},
            {"type": "visual_clip", "source": clip2, "duration": 3.5, "scale_mode": "fit"},
            {"type": "pov_demo", "source": "pov_demo.mov", "start": 0, "end": 10},
        ],
        "audio": {"source": audio, "volume": 0.6},
    }
    with open(f"briefs/batch_{i:02d}.json", "w") as f:
        json.dump(brief, f, indent=2)
```

Then: `python3 generate.py batch briefs/`
