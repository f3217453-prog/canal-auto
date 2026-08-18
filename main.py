"""
Pipeline de AI Clipping (100% gratis, sin API de pago)
------------------------
1. Transcribe el video con Whisper
2. Le pide a un modelo local (Ollama, gratis) que marque los mejores momentos
3. Corta cada momento con ffmpeg, lo reencuadra a 9:16 y le quema subtítulos
4. Sube cada clip a YouTube Shorts

Uso: python main.py input/stream.mp4
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path

import whisper
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else "input/stream.mp4"
CLIPS_DIR = Path("clips")
CLIPS_DIR.mkdir(exist_ok=True)

YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_CLIPS_REFRESH_TOKEN = os.environ["YOUTUBE_CLIPS_REFRESH_TOKEN"]

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"


def transcribe(video_path: str):
    print("Transcribiendo con Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(video_path, verbose=False)
    return result["segments"]


def find_viral_moments(segments):
    print("Pidiendo al modelo local que marque los mejores momentos...")
    transcript_text = "\n".join(
        f"[{s['start']:.1f}-{s['end']:.1f}] {s['text'].strip()}" for s in segments
    )

    prompt = f"""Aqui esta la transcripcion de un stream con timestamps en segundos.

{transcript_text}

Marca los 5 a 8 momentos con mayor potencial viral para clips cortos (gracioso, sorprendente, polemico, emotivo).
Cada clip debe durar entre 20 y 60 segundos.
Responde SOLO con JSON valido, sin texto adicional ni backticks, con este formato exacto:
[
  {{"start": 123.4, "end": 145.0, "title": "Titulo llamativo para el short", "reason": "por que es viral"}}
]
"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=600,
    )
    response.raise_for_status()
    raw = response.json()["response"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    start = raw.find("[")
    end = raw.rfind("]") + 1
    return json.loads(raw[start:end])


def write_srt(segments, start, end, out_path: Path):
    def fmt(t):
        h, rem = divmod(max(t, 0), 3600)
        m, s = divmod(rem, 60)
        ms = int((s - int(s)) * 1000)
        return f"{int(h):02}:{int(m):02}:{int(s):02},{ms:03}"

    lines = []
    idx = 1
    for seg in segments:
        if seg["end"] < start or seg["start"] > end:
            continue
        rel_start = max(seg["start"] - start, 0)
        rel_end = min(seg["end"] - start, end - start)
        lines.append(str(idx))
        lines.append(f"{fmt(rel_start)} --> {fmt(rel_end)}")
        lines.append(seg["text"].strip())
        lines.append("")
        idx += 1

    out_path.write_text("\n".join(lines), encoding="utf-8")


def cut_clip(video_path: str, start: float, end: float, srt_path: Path, out_path: Path):
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-vf",
        f"crop=ih*9/16:ih,scale=1080:1920,subtitles={srt_path}:force_style='FontSize=18,PrimaryColour=&HFFFFFF&'",
        "-c:a", "aac",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def upload_to_youtube(file_path: Path, title: str, description: str):
    creds = Credentials(
        None,
        refresh_token=YOUTUBE_CLIPS_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "categoryId": "24",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=str(file_path),
    )
    response = request.execute()
    print(f"Subido: https://youtube.com/shorts/{response['id']}")


def main():
    segments = transcribe(VIDEO_PATH)
    moments = find_viral_moments(segments)
    print(f"El modelo encontro {len(moments)} momentos virales")

    for i, m in enumerate(moments):
        clip_path = CLIPS_DIR / f"clip_{i}.mp4"
        srt_path = CLIPS_DIR / f"clip_{i}.srt"

        write_srt(segments, m["start"], m["end"], srt_path)
        cut_clip(VIDEO_PATH, m["start"], m["end"], srt_path, clip_path)
        upload_to_youtube(clip_path, m["title"], m.get("reason", ""))


if __name__ == "__main__":
    main()
