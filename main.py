"""
Pipeline 100% automático para Shorts (canal multi-nicho).
Se ejecuta 2 veces al día (1pm y 11pm), disparado por GitHub Actions.
Nichos: Horror Stories, True Crime, World Records, Top 10.
"""

import os
import random
import textwrap
import requests
import asyncio
import edge_tts
import whisper
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_videoclips
)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

VOZ = "en-US-GuyNeural"
RESOLUCION = (1080, 1920)

NICHOS = {
    "horror": {
        "temas": [
            "a ghost story set in an abandoned house",
            "a chilling creepypasta about something in the woods",
            "a haunted house with a dark history",
            "an urban legend that still scares people today",
            "a real reported ghost sighting with no explanation",
        ],
        "instruccion": (
            "Write it as a scary, atmospheric horror narration. Build dread "
            "slowly, use sensory details, end on a chilling unresolved note."
        ),
        "tags": ["horror", "scary story", "creepypasta", "shorts"],
    },
    "true_crime": {
        "temas": [
            "an unsolved disappearance that baffled investigators",
            "a cold case cracked open decades later",
            "a criminal who evaded capture in a shocking way",
            "a mysterious death many still question",
        ],
        "instruccion": (
            "Write it as a suspenseful true crime narration. Focus on the "
            "intrigue and timeline, not graphic violence. End with a twist "
            "or unresolved question."
        ),
        "tags": ["truecrime", "mystery", "unsolved", "shorts"],
    },
    "world_records": {
        "temas": [
            "the most extreme world record ever achieved",
            "a bizarre Guinness World Record most people don't know about",
            "a record that seems impossible but is completely real",
            "the fastest, biggest, or strangest record in its category",
        ],
        "instruccion": (
            "Write it as an exciting, fast-paced narration about a real "
            "world record. Use vivid numbers and comparisons to make it "
            "feel astonishing."
        ),
        "tags": ["worldrecord", "guinnessworldrecords", "amazing", "shorts"],
    },
    "top10": {
        "temas": [
            "top 10 most dangerous places on Earth",
            "top 10 strangest animals in the world",
            "top 10 mysteries science still can't explain",
            "top 10 most valuable things ever discovered",
        ],
        "instruccion": (
            "Write it as a punchy top 10 countdown narration. Quick hits, "
            "one sentence per fact building up to the most shocking one "
            "at the end."
        ),
        "tags": ["top10", "facts", "ranking", "shorts"],
    },
}

CONSULTAS_AMBIENTE = {
    "horror": [
        "dark forest fog night", "abandoned house interior", "old hallway dark",
        "candle flame dark room", "creepy basement", "foggy graveyard night",
        "old door creaking", "flashlight dark room",
    ],
    "true_crime": [
        "dark street night fog", "police lights night city", "old detective office",
        "rain window night moody", "empty road night headlights", "newspaper archive",
        "typewriter old paper", "evidence board string",
    ],
    "world_records": [
        "stadium crowd aerial", "extreme sports action", "fast car racing",
        "mountain climbing extreme", "ocean waves aerial", "city skyline aerial",
        "athlete running slow motion", "fireworks night sky",
    ],
    "top10": [
        "nature landscape aerial", "city skyline timelapse", "ocean underwater",
        "desert landscape aerial", "mountain range aerial", "wildlife animals",
        "space stars night sky", "waterfall nature",
    ],
}


def generar_guion(tema: str, instruccion: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = textwrap.dedent(f"""
        Write a 55-second narration script in English about: {tema}.
        {instruccion}
        Short sentences. Strong hook in the first sentence.
        Only the narration text, no titles or numbering, as if narrated by
        a single voice.
    """)
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def descargar_clips(nicho: str, carpeta: str = "clips"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = CONSULTAS_AMBIENTE[nicho]
    rutas = []
    indice_global = 0
    for consulta in consultas:
        url = f"https://api.pexels.com/videos/search?query={consulta}&per_page=4&orientation=portrait"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except requests.exceptions.RequestException:
            continue
        videos = r.json().get("videos", [])
        for v in videos:
            archivos = sorted(v["video
