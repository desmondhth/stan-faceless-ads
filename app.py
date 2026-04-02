"""
Stan Web — Browser-based faceless video ad generator.

Run:  python3 app.py
Open: http://localhost:5555
"""

import json
import os
import random
import threading
import uuid
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_from_directory

from compose import compose
from config import VISUAL_CLIPS_DIR, AUDIO_DIR, POV_DEMO_DIR, OUTPUT_DIR, BRIEFS_DIR
import config

app = Flask(__name__)

# ============================================================
# COPYWRITING ENGINE
# ============================================================

HOOK_TEMPLATES = {
    "training_arc": [
        "66 Days.\nProject {character}.",
        "POV:\n{character}'s training arc\nbut it's your real life",
        "{character} trained every day.\nWhat's your excuse?",
        "POV:\nyou unlocked\n{character}'s discipline",
    ],
    "grind": [
        "No talent. No gift.\nJust raw discipline.\nOutwork everyone.",
        "Zero excuses.\nPure discipline.\n66 days.",
        "Train in silence.\nLet results speak.",
        "The grind is lonely.\nThe results speak.",
    ],
    "transformation": [
        "66 days\nto become\nunrecognizable.",
        "Day 1: Build foundations.\nDay 22: Habits locked in.\nDay 66: They won't recognize you.",
        "POV:\nyou finally stopped\nmaking excuses",
        "Your future self\nis watching.\nMake them proud.",
    ],
    "villain_arc": [
        "POV:\nyou started your\nvillain arc",
        "Go silent. Go dark.\nCome back unrecognizable.\n66 days.",
        "They'll regret\ndoubting you.",
        "The best revenge\nis a massive glow up.",
    ],
    "rpg_life": [
        "POV:\nyour life has\na quest log now",
        "the app that turned\nmy habits into\na video game",
        "Quests. XP. Levels. Streaks.\nBut the character is you.",
        "Wake up early. +50 XP\nWorkout. +100 XP\nRead. +75 XP",
    ],
    "npc_to_main": [
        "Stop being\nan NPC.",
        "Start your\nmain character arc.\n66 days.",
        "From NPC\nto protagonist.\n66 days.",
        "You were never meant\nto be an NPC.",
    ],
    "discipline_list": [
        "If you want success:\n\nWake up early.\nCold shower.\nRead 10 pages.\nWorkout.\n\n66 days.",
        "5 habits that\nchanged my life:\n\nCold shower.\nRead daily.\nWorkout.\nNo phone before 9 AM.\nJournal.",
        "Morning routine\nof a Level 50 player:\n\n5:30 AM wake up.\nMeditate.\nWorkout.\nCold shower.",
        "Things I quit\nto level up:\n\nPorn.\nFast food.\nDoom scrolling.\nExcuses.",
    ],
    "lock_in": [
        "Lock in.",
        "Lock in.\n66 days.\nNo days off.",
        "Delete social media.\nWake up at 5 AM.\nTrain.\n66 days.",
        "Outwork everyone.\nQuietly.",
    ],
    "screen_time": [
        "Your screen time:\n7 hours.\n\nSelf-improvement:\n0.",
        "What if your phone\nmade you better\ninstead of worse?",
        "Stop scrolling.\nStart leveling up.",
        "Your phone is either\na weapon or a cage.",
    ],
}

ANIME_CHARACTERS = {
    "solo_leveling": {"character": "Sung Jinwoo", "prefix": "sl_"},
    "jjk_maki": {"character": "Maki", "prefix": "maki_"},
    "jjk_gojo": {"character": "Gojo", "prefix": "jjk_gojo"},
    "jjk_toji": {"character": "Toji", "prefix": "toji_"},
    "demon_slayer": {"character": "Tanjiro", "prefix": "ds_"},
    "naruto": {"character": "Naruto", "prefix": "naruto_"},
    "one_punch_man": {"character": "Saitama", "prefix": "opm_"},
    "dragon_ball": {"character": "Goku", "prefix": "dbz_"},
    "baki": {"character": "Baki", "prefix": "baki_"},
    "ippo": {"character": "Ippo", "prefix": "ippo_"},
    "attack_on_titan": {"character": "Eren", "prefix": "aot_"},
    "mob_psycho": {"character": "Mob", "prefix": "mob_"},
    "bleach": {"character": "Ichigo", "prefix": "bleach_"},
    "chainsaw_man": {"character": "Denji", "prefix": "csm_"},
    "megalo_box": {"character": "Joe", "prefix": "megalobox"},
    "blue_lock": {"character": "Isagi", "prefix": "blue_lock"},
    "haikyuu": {"character": "Hinata", "prefix": "haikyuu"},
}


def get_clips():
    if not os.path.exists(VISUAL_CLIPS_DIR):
        return []
    return sorted(f for f in os.listdir(VISUAL_CLIPS_DIR) if f.endswith(".mp4"))


def get_audio():
    if not os.path.exists(AUDIO_DIR):
        return []
    return sorted(f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3"))


def get_pov():
    if not os.path.exists(POV_DEMO_DIR):
        return []
    return sorted(f for f in os.listdir(POV_DEMO_DIR) if f.endswith((".mov", ".mp4")))


def find_anime_clips(anime_key, all_clips):
    prefix = ANIME_CHARACTERS.get(anime_key, {}).get("prefix", "")
    return [c for c in all_clips if c.startswith(prefix) or c.startswith(prefix.rstrip("_"))]


def generate_briefs(angle, anime, pov_demo, pov_start, pov_end, count, audio_pick):
    all_clips = get_clips()
    anime_clips = find_anime_clips(anime, all_clips)
    character = ANIME_CHARACTERS.get(anime, {}).get("character", "")
    hooks = HOOK_TEMPLATES.get(angle, HOOK_TEMPLATES["training_arc"])

    if not anime_clips:
        anime_clips = all_clips[:10] if all_clips else []

    briefs = []
    used = set()

    for i in range(count):
        avail = [h for h in hooks if h not in used] or hooks
        hook = random.choice(avail)
        used.add(hook)
        hook = hook.replace("{character}", character)

        if len(anime_clips) >= 2:
            c1, c2 = random.sample(anime_clips, 2)
        elif anime_clips:
            c1 = anime_clips[0]
            c2 = random.choice([c for c in all_clips if c != c1]) if len(all_clips) > 1 else c1
        else:
            c1 = c2 = all_clips[0] if all_clips else "placeholder.mp4"

        brief = {
            "name": f"gen_{angle}_{anime}_{i+1:02d}",
            "sections": [
                {"type": "visual_clip", "source": c1, "duration": 3.5, "scale_mode": "fit",
                 "text_overlays": [{"text": hook, "position": "top", "appear_at": 0, "duration": 3.5, "font_size": 58}]},
                {"type": "visual_clip", "source": c2, "duration": 3.5, "scale_mode": "fit"},
                {"type": "pov_demo", "source": pov_demo, "start": pov_start, "end": pov_end},
            ],
            "audio": {"source": audio_pick, "volume": 0.6},
        }
        briefs.append(brief)

    return briefs


# ============================================================
# JOB SYSTEM
# ============================================================

jobs = {}


def run_job(job_id, briefs):
    job = jobs[job_id]
    job["status"] = "running"
    outputs = []

    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    original_out = config.OUTPUT_DIR
    config.OUTPUT_DIR = job_dir

    for i, brief in enumerate(briefs):
        job["progress"] = i
        try:
            out = compose(brief)
            if out:
                outputs.append(os.path.basename(out))
        except Exception as e:
            print(f"  Error: {e}")

    job["progress"] = len(briefs)
    job["outputs"] = outputs
    job["status"] = "done"
    config.OUTPUT_DIR = original_out


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template_string(HTML, angles=list(HOOK_TEMPLATES.keys()),
                                  animes=ANIME_CHARACTERS, audio=get_audio(), pov=get_pov())


@app.route("/api/preview", methods=["POST"])
def preview():
    d = request.json
    briefs = generate_briefs(d["angle"], d["anime"], d["pov_demo"],
                              float(d.get("pov_start", 0)), float(d.get("pov_end", 10)),
                              int(d.get("count", 3)), d["audio"])
    return jsonify({"briefs": briefs})


@app.route("/api/generate", methods=["POST"])
def generate():
    d = request.json
    briefs = generate_briefs(d["angle"], d["anime"], d["pov_demo"],
                              float(d.get("pov_start", 0)), float(d.get("pov_end", 10)),
                              int(d.get("count", 3)), d["audio"])
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    jobs[job_id] = {"status": "queued", "progress": 0, "total": len(briefs), "outputs": []}
    threading.Thread(target=run_job, args=(job_id, briefs)).start()
    return jsonify({"job_id": job_id, "total": len(briefs)})


@app.route("/api/status/<job_id>")
def status(job_id):
    return jsonify(jobs.get(job_id, {"error": "not found"}))


@app.route("/output/<job_id>/<filename>")
def download(job_id, filename):
    return send_from_directory(os.path.join(OUTPUT_DIR, job_id), filename)


# ============================================================
# HTML
# ============================================================

HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stan — Faceless Ad Generator</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0D0D0D;color:#fff;min-height:100vh}
.c{max-width:900px;margin:0 auto;padding:24px}
h1{font-size:28px;margin-bottom:4px} h1 span{color:#FB6900}
.sub{color:#888;margin-bottom:32px;font-size:14px}
.fg{margin-bottom:20px}
label{display:block;font-size:12px;color:#aaa;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
select,input[type=number]{width:100%;padding:12px 16px;background:#1a1a1a;border:1px solid #333;border-radius:8px;color:#fff;font-size:15px;outline:0}
select:focus,input:focus{border-color:#FB6900}
.r2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.r3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.btn{padding:14px 28px;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;transition:.2s}
.bp{background:#1a1a1a;color:#FB6900;border:1px solid #FB6900} .bp:hover{background:#2a1a0a}
.bg{background:#FB6900;color:#fff} .bg:hover{background:#e07800} .bg:disabled{background:#333;color:#666;cursor:not-allowed}
.acts{display:flex;gap:12px;margin-top:24px}
.card{background:#1a1a1a;border-radius:8px;padding:16px;margin-bottom:12px;border:1px solid #222}
.card h3{font-size:14px;color:#FB6900;margin-bottom:8px}
.hook{font-size:18px;font-weight:700;white-space:pre-line;margin-bottom:8px;line-height:1.3}
.meta{font-size:12px;color:#666} .meta span{color:#888}
.tag{display:inline-block;background:#2a1a0a;color:#FB6900;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:4px}
.pbar{height:8px;background:#1a1a1a;border-radius:4px;overflow:hidden;margin:12px 0}
.pfill{height:100%;background:#FB6900;transition:width .5s;border-radius:4px}
.ptxt{font-size:13px;color:#888}
.vc{background:#1a1a1a;border-radius:8px;padding:16px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between}
.vc a{color:#FB6900;text-decoration:none;font-weight:600} .vc a:hover{text-decoration:underline}
#prog{margin-top:24px;display:none} #prev,#res{margin-top:24px}
</style></head><body>
<div class="c">
<h1><span>Stan</span> — Faceless Ad Generator</h1>
<p class="sub">Select angle, anime, and assets. Preview hooks, then bulk generate videos.</p>
<div class="r2">
<div class="fg"><label>Marketing Angle</label><select id="angle">
{% for a in angles %}<option value="{{a}}">{{a.replace('_',' ').title()}}</option>{% endfor %}
</select></div>
<div class="fg"><label>Anime / Character</label><select id="anime">
{% for k,v in animes.items() %}<option value="{{k}}">{{v.character}} ({{k.replace('_',' ').title()}})</option>{% endfor %}
</select></div></div>
<div class="r3">
<div class="fg"><label>Audio</label><select id="audio">
{% for a in audio %}<option value="{{a}}">{{a.replace('.mp3','').replace('_',' ')}}</option>{% endfor %}
</select></div>
<div class="fg"><label>POV Demo</label><select id="pov">
{% for p in pov %}<option value="{{p}}">{{p}}</option>{% endfor %}
</select></div>
<div class="fg"><label>Videos (1-10)</label><select id="cnt">
<option value="1">1</option><option value="3" selected>3</option><option value="5">5</option><option value="10">10</option>
</select></div></div>
<div class="r2">
<div class="fg"><label>POV Start (s)</label><input type="number" id="ps" value="0" min="0"></div>
<div class="fg"><label>POV End (s)</label><input type="number" id="pe" value="10" min="1"></div>
</div>
<div class="acts">
<button class="btn bp" onclick="prev()">Preview Hooks</button>
<button class="btn bg" id="gb" onclick="gen()">Generate Videos</button>
</div>
<div id="prev"></div>
<div id="prog"><div class="pbar"><div class="pfill" id="pf"></div></div><p class="ptxt" id="pt">Generating...</p></div>
<div id="res"></div>
</div>
<script>
const P=()=>({angle:$('angle').value,anime:$('anime').value,audio:$('audio').value,
pov_demo:$('pov').value,pov_start:$('ps').value,pov_end:$('pe').value,count:$('cnt').value});
const $=id=>document.getElementById(id);
async function prev(){
const r=await(await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(P())})).json();
$('prev').innerHTML=r.briefs.map((b,i)=>{
const h=b.sections[0].text_overlays[0]?.text||'';
return`<div class="card"><h3>Video ${i+1}: ${b.name}</h3><div class="hook">${h.replace(/\\n/g,'<br>')}</div>
<div class="meta"><span class="tag">${b.sections[0].source}</span><span class="tag">${b.sections[1].source}</span><span class="tag">${b.audio?.source||''}</span></div></div>`;
}).join('');
}
async function gen(){
const b=$('gb');b.disabled=true;b.textContent='Generating...';$('prog').style.display='block';$('res').innerHTML='';
const r=await(await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(P())})).json();
const poll=setInterval(async()=>{
const s=await(await fetch(`/api/status/${r.job_id}`)).json();
const p=Math.round(s.progress/s.total*100);
$('pf').style.width=p+'%';$('pt').textContent=`${s.progress}/${s.total} videos...`;
if(s.status==='done'){clearInterval(poll);
$('pt').textContent=`Done! ${s.outputs.length}/${s.total} videos.`;
$('res').innerHTML=s.outputs.map(f=>`<div class="vc"><span>${f}</span><a href="/output/${r.job_id}/${f}" target="_blank">Download</a></div>`).join('');
b.disabled=false;b.textContent='Generate Videos';}
},2000);
}
</script></body></html>"""

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("\n  Stan Web — http://localhost:5555\n")
    app.run(host="0.0.0.0", port=5555, debug=False)
