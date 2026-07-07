"""
Pipeline 100% automático para canal de datos curiosos.
Se ejecuta solo, sin intervención humana, disparado por GitHub Actions.

Pasos:
1. Genera un guion con Gemini (API gratuita)
2. Convierte el guion en audio con edge-tts (gratis, sin límite)
3. Transcribe el audio con timestamps usando whisper (gratis, local)
4. Descarga clips de video relacionados desde Pexels (API gratuita)
5. Arma el video final con moviepy (clips + audio + subtítulos)
6. Sube el video a YouTube usando la API de YouTube Data v3
"""

import os
import json
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

# ------------------------------------------------------------------
# CONFIGURACIÓN (todo viene de variables de entorno / GitHub Secrets)
# ------------------------------------------------------------------
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

TEMAS = [
    "Ancient Egypt", "Space and astronomy", "Deep oceans",
    "History of Rome", "Strange animals", "The human brain",
    "Lost civilizations", "Weird science", "Vikings", "Dinosaurs"
]

VOZ = "en-US-GuyNeural"  # voz en inglés, natural
RESOLUCION = (1080, 1920)  # formato vertical (Shorts/Reels/TikTok)


# ------------------------------------------------------------------
# 1. GENERAR GUION CON GEMINI (capa gratuita)
# ------------------------------------------------------------------
def generar_guion(tema: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = textwrap.dedent(f"""
        Write a 55-second script in English, curious and dynamic tone,
        with 5 little-known facts about: {tema}.
        Short sentences. Strong hook in the first sentence.
        Only the script, no titles or numbering, as if narrated by a single voice.
    """)
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


# ------------------------------------------------------------------
# 2. GUION -> AUDIO (edge-tts, gratis)
# ------------------------------------------------------------------
async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


# ------------------------------------------------------------------
# 3. AUDIO -> SUBTÍTULOS CON TIMESTAMPS (whisper, gratis, local)
# ------------------------------------------------------------------
def transcribir(audio_path: str):
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]  # cada uno: start, end, text


# ------------------------------------------------------------------
# 4. BUSCAR Y DESCARGAR CLIPS EN PEXELS (gratis)
# ------------------------------------------------------------------
def descargar_clips(tema: str, cantidad: int = 6, carpeta: str = "clips"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={tema}&per_page={cantidad}&orientation=portrait"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    videos = r.json().get("videos", [])
    rutas = []
    for i, v in enumerate(videos):
        # elegir el archivo de menor resolución razonable para ahorrar espacio/tiempo
        archivos = sorted(v["video_files"], key=lambda f: f.get("width", 0))
        enlace = archivos[len(archivos)//2]["link"]
        destino = f"{carpeta}/clip_{i}.mp4"
        with requests.get(enlace, stream=True, timeout=60) as resp:
            with open(destino, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        rutas.append(destino)
    return rutas


# ------------------------------------------------------------------
# 5. ARMAR EL VIDEO FINAL (moviepy)
# ------------------------------------------------------------------
def armar_video(clips_rutas, audio_path, segmentos, salida="video_final.mp4"):
    audio = AudioFileClip(audio_path)
    duracion_total = audio.duration

    # repetir/recortar clips hasta cubrir la duración total
    clips = []
    tiempo_acumulado = 0
    i = 0
    while tiempo_acumulado < duracion_total:
        ruta = clips_rutas[i % len(clips_rutas)]
        c = VideoFileClip(ruta).without_audio()
        c = c.resize(height=RESOLUCION[1]).crop(
            x_center=c.w/2, width=RESOLUCION[0]
        )
        restante = duracion_total - tiempo_acumulado
        c = c.subclip(0, min(c.duration, restante, 6))
        clips.append(c)
        tiempo_acumulado += c.duration
        i += 1

    video_base = concatenate_videoclips(clips, method="compose")
    video_base = video_base.set_audio(audio)

    # subtítulos quemados en el video, segmento por segmento
    subtitulos = []
    for seg in segmentos:
        txt = TextClip(
            seg["text"].strip(), fontsize=60, color="white",
            font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
            size=(RESOLUCION[0]-100, None), method="caption"
        ).set_start(seg["start"]).set_end(seg["end"]).set_position(("center", "bottom"))
        subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)
    final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac")
    return salida


# ------------------------------------------------------------------
# 6. SUBIR A YOUTUBE
# ------------------------------------------------------------------
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
            "tags": ["datos curiosos", "historia", "shorts"],
            "categoryId": "27",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("Subido:", response.get("id"))


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    tema = random.choice(TEMAS)
    print("Tema elegido:", tema)

    guion = generar_guion(tema)
    print("Guion generado:\n", guion)

    audio_path = generar_audio(guion)
    segmentos = transcribir(audio_path)
    clips = descargar_clips(tema)
    video_path = armar_video(clips, audio_path, segmentos)

    titulo = f"5 SHOCKING Facts About {tema} 😱"
    descripcion = f"{guion}\n\n#didyouknow #{tema.replace(' ', '')} #shorts"
    subir_youtube(video_path, titulo, descripcion)


if __name__ == "__main__":
    main()
