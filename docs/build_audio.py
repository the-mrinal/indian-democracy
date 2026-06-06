#!/usr/bin/env python3
"""
build_audio.py — Podcast build orchestrator for the Indian Democracy site.

Per episode:
  1. Script generation via Gemini 2.5 Pro + audio_prompts/system_prompt.md
  2. TTS synthesis via Gemini 2.5 Flash Native Audio (multi-speaker)
  3. Encoding to MP3 + Opus/WebM via ffmpeg
  4. Cover art generation via Pillow
  5. Per-episode JSON manifest (per-turn timings, no per-word)

Two-level cache (script + audio) hashed independently so editing only the
voice config doesn't re-run script generation.

Run:
  GEMINI_API_KEY=... python3 docs/build_audio.py
  GEMINI_API_KEY=... python3 docs/build_audio.py --only 06-lok-sabha
  GEMINI_API_KEY=... python3 docs/build_audio.py --force
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Install Pillow: pip install Pillow")

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("Install google-genai: pip install google-genai")

# Reuse the canonical chapter list
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site import CHAPTERS  # noqa: E402

# ------------------------------------------------------------------ #
# Paths
# ------------------------------------------------------------------ #
DOCS = Path(__file__).resolve().parent
MD_DIR = DOCS / "markdown"
THEMED_DIR = DOCS / "themed"
PROMPT_FILE = DOCS / "audio_prompts" / "system_prompt.md"
SCRIPTS_DIR = DOCS / "audio_prompts" / "scripts"   # hand/Claude-written scripts
SITE_PODCAST = DOCS / "site" / "assets" / "podcast"
CACHE_DIR = DOCS / ".cache" / "podcast"
SCRIPT_CACHE = CACHE_DIR / "scripts"
AUDIO_CACHE = CACHE_DIR / "audio"

for p in (SITE_PODCAST, SCRIPT_CACHE, AUDIO_CACHE, SCRIPTS_DIR):
    p.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ #
# Engine config (bumping the version invalidates caches)
# ------------------------------------------------------------------ #
SCRIPT_MODEL = "gemini-2.5-pro"
SCRIPT_FALLBACK = "gemini-2.5-flash"
SCRIPT_TEMPERATURE = 0.7
SCRIPT_CACHE_VERSION = "v1"

TTS_MODEL = "gemini-2.5-flash-preview-tts"
VOICE_A = "Kore"   # Person1 in script
VOICE_B = "Puck"   # Person2 in script
SPEAKER_A = "Host1"
SPEAKER_B = "Host2"
TURNS_PER_TTS_CHUNK = 8
INTER_CHUNK_SILENCE_MS = 200
AUDIO_CACHE_VERSION = "v1"

TURN_RE = re.compile(r"<(Person[12])>(.*?)</\1>", re.DOTALL)

# ------------------------------------------------------------------ #
# Themed episodes (sibling to chapters)
# ------------------------------------------------------------------ #
THEMED_EPISODES = [
    ("foundations",                  "Foundations: How India Became a Republic",   "Themed Briefs"),
    ("how-government-works",         "How Indian Government Actually Works",       "Themed Briefs"),
    ("how-elections-really-happen",  "How Elections Really Happen",                "Themed Briefs"),
    ("power-money-and-reality",      "Power, Money & Reality",                     "Themed Briefs"),
]

# ------------------------------------------------------------------ #
@dataclass
class Episode:
    slug: str
    title: str
    section: str
    kind: str         # "chapter" | "theme"
    source: Path


def all_episodes() -> list[Episode]:
    eps: list[Episode] = []
    for slug, title, section in CHAPTERS:
        src = MD_DIR / f"{slug}.md"
        if src.exists():
            eps.append(Episode(slug, title, section, "chapter", src))
    for slug, title, section in THEMED_EPISODES:
        src = THEMED_DIR / f"{slug}.md"
        if src.exists():
            eps.append(Episode(slug, title, section, "theme", src))
    return eps


# ------------------------------------------------------------------ #
# Caching
# ------------------------------------------------------------------ #
def script_hash(markdown_text: str, system_prompt: str) -> str:
    h = hashlib.sha256()
    h.update(SCRIPT_CACHE_VERSION.encode())
    h.update(SCRIPT_MODEL.encode())
    h.update(f"temp={SCRIPT_TEMPERATURE}".encode())
    h.update(system_prompt.encode())
    h.update(markdown_text.encode())
    return h.hexdigest()[:16]


def audio_hash(script: str) -> str:
    h = hashlib.sha256()
    h.update(AUDIO_CACHE_VERSION.encode())
    h.update(TTS_MODEL.encode())
    h.update(f"{VOICE_A}|{VOICE_B}".encode())
    h.update(f"silence={INTER_CHUNK_SILENCE_MS}|chunk={TURNS_PER_TTS_CHUNK}".encode())
    h.update(script.encode())
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ #
# Gemini call wrapper with retry
# ------------------------------------------------------------------ #
def get_client_for_tts() -> genai.Client:
    """Gemini client is required for TTS (and as a fallback for missing scripts)."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("Set GEMINI_API_KEY (needed for TTS, and as script-gen fallback)")
    return genai.Client(api_key=key)


def call_with_retry(fn, *, max_retries=4, base_delay=2.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            transient = any(
                s in str(e).lower()
                for s in (
                    "429", "rate limit", "resource exhausted",
                    "503", "504", "deadline",
                    "no audio", "no inline_data", "internal", "unavailable",
                )
            )
            if not transient or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"      transient error ({type(e).__name__}: {e}); retry in {delay:.0f}s")
            time.sleep(delay)


# ------------------------------------------------------------------ #
# Stage 1: Script generation
# ------------------------------------------------------------------ #
def generate_script(client, ep: Episode, system_prompt: str, force: bool) -> str:
    # Preferred path: a hand-written or Claude-Code-written script on disk.
    # If present, use it verbatim — no API call, no cache.
    manual = SCRIPTS_DIR / f"{ep.slug}.md"
    if manual.exists():
        print(f"  [script] manual ({manual.relative_to(DOCS)})")
        return manual.read_text()

    markdown_text = ep.source.read_text()
    h = script_hash(markdown_text, system_prompt)
    cache_path = SCRIPT_CACHE / f"{h}.txt"
    if not force and cache_path.exists():
        print(f"  [script] cache hit ({h})")
        return cache_path.read_text()

    cfg = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=SCRIPT_TEMPERATURE,
    )
    script = None
    for model in (SCRIPT_MODEL, SCRIPT_FALLBACK):
        print(f"  [script] {model} ({len(markdown_text.split())} src words)")
        try:
            resp = call_with_retry(
                lambda m=model: client.models.generate_content(
                    model=m, contents=markdown_text, config=cfg
                )
            )
            script = resp.text
            break
        except Exception as e:
            print(f"      {model} failed: {e}")
            if model == SCRIPT_FALLBACK:
                raise
    assert script is not None
    cache_path.write_text(script)
    return script


# ------------------------------------------------------------------ #
# Stage 2: TTS synthesis
# ------------------------------------------------------------------ #
def parse_turns(script: str) -> list[tuple[str, str]]:
    return [(spk, t.strip()) for spk, t in TURN_RE.findall(script) if t.strip()]


def _tts_prompt(chunk: list[tuple[str, str]]) -> str:
    lines = ["TTS the following two-host podcast conversation:"]
    for spk, text in chunk:
        name = SPEAKER_A if spk == "Person1" else SPEAKER_B
        lines.append(f"{name}: {text}")
    return "\n".join(lines)


def _tts_config():
    return types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker=SPEAKER_A,
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_A)
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker=SPEAKER_B,
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_B)
                        ),
                    ),
                ]
            )
        ),
    )


def synthesize_audio(client, script: str, force: bool) -> tuple[Path, list[tuple[float, float]]]:
    """Synthesise the stitched WAV. Returns (wav_path, chunk_boundaries_sec)."""
    h = audio_hash(script)
    cache_wav = AUDIO_CACHE / f"{h}.wav"
    cache_meta = AUDIO_CACHE / f"{h}.json"
    if not force and cache_wav.exists() and cache_meta.exists():
        print(f"  [audio]  cache hit ({h})")
        meta = json.loads(cache_meta.read_text())
        boundaries = [tuple(b) for b in meta["boundaries"]]
        return cache_wav, boundaries

    turns = parse_turns(script)
    if not turns:
        sys.exit("No turns parsed from script")
    chunks = [turns[i:i + TURNS_PER_TTS_CHUNK] for i in range(0, len(turns), TURNS_PER_TTS_CHUNK)]
    print(f"  [audio]  {len(turns)} turns → {len(chunks)} chunks")

    cfg = _tts_config()
    silence_sec = INTER_CHUNK_SILENCE_MS / 1000.0
    silence_pcm = b"\x00" * int(24000 * silence_sec) * 2  # 16-bit mono

    def _synth_one_chunk(prompt: str) -> bytes:
        """Synthesise one chunk; raise if response has no audio so retry kicks in."""
        resp = client.models.generate_content(model=TTS_MODEL, contents=prompt, config=cfg)
        cand = (resp.candidates or [None])[0]
        if cand is None or cand.content is None or not cand.content.parts:
            finish = getattr(cand, "finish_reason", None) if cand else None
            raise RuntimeError(f"TTS returned no audio (finish_reason={finish}); retrying")
        part = cand.content.parts[0]
        if not getattr(part, "inline_data", None) or not part.inline_data.data:
            raise RuntimeError("TTS part has no inline_data; retrying")
        return part.inline_data.data

    pcm_chunks: list[bytes] = []
    boundaries: list[tuple[float, float]] = []
    cursor = 0.0
    for i, chunk in enumerate(chunks):
        prompt = _tts_prompt(chunk)
        print(f"    chunk {i + 1}/{len(chunks)} ({len(chunk)} turns)...", end=" ", flush=True)
        pcm = call_with_retry(lambda: _synth_one_chunk(prompt))
        chunk_dur = len(pcm) / 2 / 24000  # 16-bit / 24 kHz mono
        start = cursor
        end = cursor + chunk_dur
        boundaries.append((round(start, 4), round(end, 4)))
        cursor = end
        if i < len(chunks) - 1:
            cursor += silence_sec
        pcm_chunks.append(pcm)
        print(f"{chunk_dur:.1f}s")

    stitched = b""
    for i, pcm in enumerate(pcm_chunks):
        stitched += pcm
        if i < len(pcm_chunks) - 1:
            stitched += silence_pcm

    with wave.open(str(cache_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(stitched)
    cache_meta.write_text(json.dumps({"boundaries": boundaries}))
    return cache_wav, boundaries


# ------------------------------------------------------------------ #
# Stage 3: Encode
# ------------------------------------------------------------------ #
def encode_audio(wav: Path, out_mp3: Path, out_webm: Path):
    print(f"  [encode] → {out_mp3.name} + {out_webm.name}")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
         "-ar", "24000", "-ac", "1", "-b:a", "96k", str(out_mp3)],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
         "-ar", "24000", "-ac", "1", "-c:a", "libopus", "-b:a", "64k",
         str(out_webm)],
        check=True,
    )


# ------------------------------------------------------------------ #
# Stage 4: Cover art (Pillow, no AI)
# ------------------------------------------------------------------ #
SAFFRON = (255, 153, 51)
GREEN   = (19, 136, 8)
CREAM   = (253, 253, 251)
NAVY    = (0, 0, 128)
INK     = (38, 38, 51)

_MAC_FONTS = [
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
]


def _load_font(path_candidates: list[str], size: int):
    for p in path_candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_cover(ep: Episode, out_png: Path):
    size = 1024
    img = Image.new("RGB", (size, size), CREAM)
    draw = ImageDraw.Draw(img)

    # Vertical saffron→cream→green gradient (flag-inspired)
    band = size // 3
    for y in range(size):
        if y < band:
            t = y / band
            color = tuple(int(SAFFRON[c] * (1 - t) + CREAM[c] * t) for c in range(3))
        elif y < 2 * band:
            color = CREAM
        else:
            t = (y - 2 * band) / band
            color = tuple(int(CREAM[c] * (1 - t) + GREEN[c] * t) for c in range(3))
        draw.line([(0, y), (size, y)], fill=color)

    font_num     = _load_font(_MAC_FONTS, 260)
    font_title   = _load_font(_MAC_FONTS, 54)
    font_section = _load_font(_MAC_FONTS, 30)
    font_brand   = _load_font(_MAC_FONTS, 28)

    # Chapter / theme label in the middle
    label = ep.slug.split("-", 1)[0]
    if not label.isdigit():
        label = "★"
    draw.text((size // 2, size // 2 - 40), label, fill=NAVY, anchor="mm", font=font_num)

    # Title (one line, truncated if too long)
    title = ep.title
    if len(title) > 38:
        title = title[:36] + "…"
    draw.text((size // 2, size - 180), title, fill=NAVY, anchor="mm", font=font_title)

    # Section + brand strip
    draw.text((size // 2, size - 120), ep.section.upper(), fill=INK, anchor="mm", font=font_section)
    draw.text((size // 2, size - 70), "INDIAN DEMOCRACY · A GUIDE", fill=INK, anchor="mm", font=font_brand)

    img.save(out_png, "PNG", optimize=True)


# ------------------------------------------------------------------ #
# Stage 5: Per-episode + master manifests
# ------------------------------------------------------------------ #
def build_episode_manifest(
    ep: Episode, script: str, boundaries: list[tuple[float, float]], total_dur: float,
) -> dict:
    turns = parse_turns(script)
    chunks = [turns[i:i + TURNS_PER_TTS_CHUNK] for i in range(0, len(turns), TURNS_PER_TTS_CHUNK)]
    assert len(chunks) == len(boundaries), "chunk/boundary count mismatch"

    manifest_turns = []
    for chunk, (c_start, c_end) in zip(chunks, boundaries):
        c_dur = c_end - c_start
        word_counts = [max(1, len(t.split())) for _, t in chunk]
        total_words = sum(word_counts)
        t_cursor = c_start
        for (spk, text), wc in zip(chunk, word_counts):
            dur = c_dur * (wc / total_words)
            manifest_turns.append({
                "speaker": "host_a" if spk == "Person1" else "host_b",
                "start": round(t_cursor, 3),
                "end": round(t_cursor + dur, 3),
                "text": text,
            })
            t_cursor += dur

    return {
        "id": ep.slug,
        "title": ep.title,
        "section": ep.section,
        "kind": ep.kind,
        "duration": round(total_dur, 2),
        "audio": {"mp3": f"{ep.slug}.mp3", "webm": f"{ep.slug}.webm"},
        "cover": f"{ep.slug}.png",
        "voices": {"host_a": VOICE_A, "host_b": VOICE_B},
        "turns": manifest_turns,
    }


def write_master_manifest(eps_manifests: list[dict]):
    summary = [
        {
            "id": m["id"], "title": m["title"], "section": m["section"],
            "kind": m["kind"], "duration": m["duration"],
            "audio": m["audio"], "cover": m["cover"],
        }
        for m in eps_manifests
    ]
    out = SITE_PODCAST / "audio_manifest.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nMaster manifest → {out.relative_to(DOCS)}  ({len(summary)} episodes)")


# ------------------------------------------------------------------ #
# Per-episode pipeline
# ------------------------------------------------------------------ #
def process_episode(client, ep: Episode, system_prompt: str, force: bool) -> dict:
    print(f"\n=== {ep.slug}  ({ep.title}) ===")
    script = generate_script(client, ep, system_prompt, force)
    wav, boundaries = synthesize_audio(client, script, force)

    out_mp3 = SITE_PODCAST / f"{ep.slug}.mp3"
    out_webm = SITE_PODCAST / f"{ep.slug}.webm"
    encode_audio(wav, out_mp3, out_webm)

    out_png = SITE_PODCAST / f"{ep.slug}.png"
    render_cover(ep, out_png)
    print(f"  [cover]  → {out_png.name}")

    total_dur = boundaries[-1][1] + (INTER_CHUNK_SILENCE_MS / 1000.0) * (len(boundaries) - 1)
    manifest = build_episode_manifest(ep, script, boundaries, total_dur)
    (SITE_PODCAST / f"{ep.slug}.json").write_text(json.dumps(manifest, indent=2))
    print(f"  done — {total_dur:.1f}s, {len(manifest['turns'])} turns")
    return manifest


# ------------------------------------------------------------------ #
def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--only", help="Build a single episode (slug)")
    ap.add_argument("--force", action="store_true", help="Ignore all caches")
    args = ap.parse_args()

    if not PROMPT_FILE.exists():
        sys.exit(f"Missing prompt file: {PROMPT_FILE}")

    eps = all_episodes()
    if args.only:
        eps = [e for e in eps if e.slug == args.only]
        if not eps:
            sys.exit(f"No episode with slug {args.only!r}")

    system_prompt = PROMPT_FILE.read_text()
    client = get_client_for_tts()

    manifests: list[dict] = []
    for ep in eps:
        manifests.append(process_episode(client, ep, system_prompt, args.force))

    if not args.only:
        write_master_manifest(manifests)


if __name__ == "__main__":
    main()
