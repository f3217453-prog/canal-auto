"""
Pipeline para el video LARGO diario (12-15 minutos).
Corre 1 vez al día a las 18:00 hora España (ver longform.yml).
Mismos 4 nichos que los Shorts: Horror, True Crime, World Records, Top 10.
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
RESOLUCION = (1920, 1080)

NICHOS = {
    "horror": {
        "temas": [
            "a long, slow-burn ghost story in an abandoned mansion",
            "a chilling creepypasta that escalates over time",
            "the dark history behind a real haunted location",
            "an urban legend explored in full detail",
        ],
        "instruccion": (
            "Write it as a slow-burn horror documentary narration. Build "
            "atmosphere and dread gradually across the whole runtime, with "
            "a strong climax near the end and a chilling final line."
        ),
        "tags": ["horror", "scary story", "creepypasta", "horror stories"],
        "categoria": "22",
    },
    "true_crime": {
        "temas": [
            "the disappearance that baffled investigators for decades",
            "a cold case cracked open by a single overlooked clue",
            "a criminal who evaded capture using a shocking method",
            "an unsolved case with too many suspects and no answers",
        ],
        "instruccion": (
            "Write it as a documentary-style true crime narration. Cold "
            "open hook, background, escalating investigation, twist, and "
            "an unresolved or thought-provoking ending. Do not use real "
            "named victims or suspects; keep it general and composite."
        ),
        "tags": ["true crime", "mystery", "unsolved", "documentary"],
        "categoria": "27",
    },
    "world_records": {
        "temas": [
            "a deep dive into the most extreme world records ever achieved",
            "the strangest Guinness World Records and the people behind them",
            "records that sound fake but are completely real, explained",
        ],
        "instruccion": (
            "Write it as an engaging documentary narration exploring "
            "several jaw-dropping world records in detail, with vivid "
            "numbers, comparisons, and a sense of wonder throughout."
        ),
        "tags": ["world record", "guinness world records", "amazing facts"],
        "categoria": "24",
    },
    "top10": {
        "temas": [
            "top 10 most dangerous places on Earth, explored in depth",
            "top 10 mysteries science still can't explain",
            "top 10 most valuable discoveries in history",
        ],
        "instruccion": (
            "Write it as a documentary-style top 10 countdown, with a "
            "couple of paragraphs of context for each entry, building up "
            "to the most shocking one at the end."
        ),
        "tags": ["top10", "facts", "ranking", "documentary"],
        "categoria": "24",
    },
}

CONSULTAS_AMBIENTE = {
    "horror": [
        "dark forest fog night", "abandoned house interior", "old hallway dark",
        "candle flame dark room", "creepy basement", "foggy graveyard night",
        "old door creaking", "flashlight dark room", "abandoned mansion",
        "dark attic", "old mirror room", "misty woods path",
    ],
    "true_crime": [
        "dark street night fog", "police lights night city", "old detective office",
        "rain window night moody", "empty road night headlights", "newspaper archive",
        "typewriter old paper", "evidence board string", "courthouse exterior",
        "city night aerial", "vintage photographs desk", "filing cabinet office",
    ],
    "world_records": [
        "stadium crowd aerial", "extreme sports action", "fast car racing",
        "mountain climbing extreme", "ocean waves aerial", "city skyline aerial",
        "athlete running slow motion", "fireworks night sky", "skydiving aerial",
        "record breaking crowd", "olympic stadium", "speed motion blur",
    ],
    "top10": [
        "nature landscape aerial", "city skyline timelapse", "ocean underwater",
        "desert landscape aerial", "mountain range aerial", "wildlife animals",
        "space stars night sky", "waterfall nature", "jungle aerial",
        "glacier aerial", "volcano landscape", "canyon aerial",
    ],
}


def generar_guion_largo(tema: str, instruccion: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = textwrap.dedent(f"""
        Write a 13-minute narration script in English about: {tema}.
        {instruccion}
        Aim for approximately 2000-2200 words total.
        Only the narration text, no titles, no scene directions, no numbering.
    """)
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio_largo.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def descargar_clips_largos(nicho: str, carpeta: str = "clips_largo"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = CONSULTAS_AMBIENTE[nicho]
    rutas = []
    indice_global = 0
    for consulta in consultas:
        url = f"https://api.pexels.com/videos/search?query={consulta}&per_page=5&orientation=landscape"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except requests.exceptions.RequestException:
            continue
        videos = r.json().get("videos", [])
        for v in videos:
            archivos = sorted(v["video_files"], key=lambda f: f.get("width", 0))
            if not archivos:
                continue
            enlace = archivos[len(archivos)//2]["link"]
            destino = f"{carpeta}/clip_{indice_global}.mp4"
            try:
                with requests.get(enlace, stream=True, timeout=60) as resp:
                    with open(destino, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                rutas.append(destino)
                indice_global += 1
            except requests.exceptions.RequestException:
                continue
    return rutas


def armar_video_largo(clips_rutas, audio_path, segmentos, salida="video_largo_final.mp4"):
    if not clips_rutas:
        raise RuntimeError("No se descargó ningún clip de Pexels, no se puede armar el video")

    audio = AudioFileClip(audio_path)
    duracion_total = audio.duration

    orden = clips_rutas.copy()
    random.shuffle(orden)

    clips = []
    tiempo_acumulado = 0
    puntero = 0
    ultimo_usado = None

    while tiempo_acumulado < duracion_total:
        if puntero >= len(orden):
            random.shuffle(orden)
            if orden[0] == ultimo_usado and len(orden) > 1:
                orden[0], orden[1] = orden[1], orden[0]
            puntero = 0

        ruta = orden[puntero]
        puntero += 1

        try:
            c = VideoFileClip(ruta).without_audio()
        except Exception:
            continue

        if c.duration < 0.5:
            c.close()
            continue

        c = c.resize(height=RESOLUCION[1])
        if c.w > RESOLUCION[0]:
            c = c.crop(x_center=c.w / 2, width=RESOLUCION[0])
        elif c.w < RESOLUCION[0]:
            c = c.resize(width=RESOLUCION[0])

        restante = duracion_total - tiempo_acumulado
        duracion_clip = min(c.duration, restante, random.uniform(4.0, 8.0))
        if duracion_clip <= 0:
            c.close()
            continue

        c = c.subclip(0, duracion_clip)
        clips.append(c)
        tiempo_acumulado += duracion_clip
        ultimo_usado = ruta

    if not clips:
        raise RuntimeError("No se pudo armar ningún clip válido para el video")

    video_base = concatenate_videoclips(clips, method="compose")
    video_base = video_base.set_audio(audio)
    video_base = video_base.set_duration(duracion_total)

    subtitulos = []
    for seg in segmentos:
        txt = TextClip(
            seg["text"].strip(), fontsize=42, color="white",
            font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
            size=(RESOLUCION[0]-200, None), method="caption"
        ).set_start(seg["start"]).set_end(seg["end"]).set_position(("center", "bottom"))
        subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)
    final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac")
    return salida


def subir_youtube(video_path: str, titulo: str, descripcion: str, tags: list, categoria: str):
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": titulo,
            "description": descripcion,
            "tags": tags,
            "categoryId": categoria,
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("Subido (largo):", response.get("id"))


def generar_titulo(nicho: str) -> str:
    if nicho == "horror":
        return "A True Horror Story You Won't Forget 👻"
    if nicho == "true_crime":
        return "Unsolved: A True Crime Mystery Documentary 🔎"
    if nicho == "world_records":
        return "The Most Incredible World Records Ever 🌍"
    return "Top 10 That Will Blow Your Mind 🔥"


def main():
    nicho = random.choice(list(NICHOS.keys()))
    tema = random.choice(NICHOS[nicho]["temas"])
    instruccion = NICHOS[nicho]["instruccion"]
    tags = NICHOS[nicho]["tags"]
    categoria = NICHOS[nicho]["categoria"]

    print("Nicho elegido (largo):", nicho)
    print("Tema elegido (largo):", tema)

    guion = generar_guion_largo(tema, instruccion)
    print("Guion generado, longitud:", len(guion.split()), "palabras")

    audio_path = generar_audio(guion)
    segmentos = transcribir(audio_path)
    clips = descargar_clips_largos(nicho)
    print(f"Clips descargados: {len(clips)}")
    video_path = armar_video_largo(clips, audio_path, segmentos)

    titulo = generar_titulo(nicho)
    descripcion = f"{guion[:400]}...\n\n#{nicho.replace('_', '')} #documentary"
    subir_youtube(video_path, titulo, descripcion, tags, categoria)


if __name__ == "__main__":
    main()
