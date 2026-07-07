"""
Pipeline para videos LARGOS (10-12 minutos) de true crime / misterios.
Corre semanalmente (ver longform.yml), en paralelo al pipeline diario de Shorts.
Mismo canal de YouTube, mismo nicho, pero formato horizontal y guion mucho más largo.
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

TEMAS_LARGOS = [
    "the disappearance that baffled investigators for decades",
    "a cold case cracked open by a single overlooked clue",
    "a criminal who evaded capture using a shocking method",
    "an unsolved case with too many suspects and no answers",
    "a mysterious death ruled accidental that many still question",
]

VOZ = "en-US-GuyNeural"
RESOLUCION = (1920, 1080)  # horizontal, para video largo


def generar_guion_largo(tema: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = textwrap.dedent(f"""
        Write an 11-minute true crime / mystery documentary-style narration
        script in English about: {tema}.
        Structure: cold open hook, background/setup, escalating investigation,
        twist or revelation, and an unresolved or thought-provoking ending.
        Suspenseful, narrative tone, like a documentary voiceover.
        Aim for approximately 1700-1900 words total.
        Do not use real named victims or real named suspects; keep it general
        and composite so no real person or case is misrepresented.
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


def descargar_clips_largos(cantidad: int = 24, carpeta: str = "clips_largo"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas_ambiente = [
        "dark street night fog", "police lights night city",
        "old detective office", "rain window night moody",
        "empty road night car headlights", "vintage photographs desk",
        "typewriter old paper", "city night aerial", "courthouse exterior",
        "newspaper archive", "flashlight dark room", "evidence board string"
    ]
    clips_por_consulta = max(1, cantidad // len(consultas_ambiente))
    rutas = []
    indice_global = 0
    for consulta in consultas_ambiente:
        url = f"https://api.pexels.com/videos/search?query={consulta}&per_page={clips_por_consulta}&orientation=landscape"
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        videos = r.json().get("videos", [])
        for v in videos:
            archivos = sorted(v["video_files"], key=lambda f: f.get("width", 0))
            enlace = archivos[len(archivos)//2]["link"]
            destino = f"{carpeta}/clip_{indice_global}.mp4"
            with requests.get(enlace, stream=True, timeout=60) as resp:
                with open(destino, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            rutas.append(destino)
            indice_global += 1
    return rutas


def armar_video_largo(clips_rutas, audio_path, segmentos, salida="video_largo_final.mp4"):
    audio = AudioFileClip(audio_path)
    duracion_total = audio.duration

    clips = []
    tiempo_acumulado = 0
    i = 0
    while tiempo_acumulado < duracion_total:
        ruta = clips_rutas[i % len(clips_rutas)]
        c = VideoFileClip(ruta).without_audio()
        c = c.resize(height=RESOLUCION[1])
        if c.w > RESOLUCION[0]:
            c = c.crop(x_center=c.w/2, width=RESOLUCION[0])
        restante = duracion_total - tiempo_acumulado
        duracion_clip = min(c.duration, restante, 8)
        c = c.subclip(0, duracion_clip)
        clips.append(c)
        tiempo_acumulado += duracion_clip
        i += 1

    video_base = concatenate_videoclips(clips, method="compose")
    video_base = video_base.set_audio(audio)

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


def subir_youtube(video_path: str, titulo: str, descripcion: str):
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
            "tags": ["true crime", "mystery", "unsolved", "documentary"],
            "categoryId": "27",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("Subido (largo):", response.get("id"))


def main():
    tema = random.choice(TEMAS_LARGOS)
    print("Tema elegido (largo):", tema)

    guion = generar_guion_largo(tema)
    print("Guion generado, longitud:", len(guion.split()), "palabras")

    audio_path = generar_audio(guion)
    segmentos = transcribir(audio_path)
    clips = descargar_clips_largos()
    video_path = armar_video_largo(clips, audio_path, segmentos)

    titulo = "Unsolved: A True Crime Mystery Documentary"
    descripcion = f"{guion[:400]}...\n\n#truecrime #mystery #unsolved #documentary"
    subir_youtube(video_path, titulo, descripcion)


if __name__ == "__main__":
    main()
