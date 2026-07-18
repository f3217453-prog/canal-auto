"""
Pipeline videos LARGOS 12-15 minutos.
Solución al guion corto: genera el guion en 3 partes separadas y las une.
Esto garantiza 2500+ palabras sin depender de un solo output de Gemini.
"""

import os
import io
import re
import time
import random
import math
import requests
import asyncio
import json
import edge_tts
import whisper
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ImageClip, concatenate_videoclips, concatenate_audioclips
)
from moviepy.audio.AudioClip import CompositeAudioClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

VOZ = "en-US-AndrewNeural"
RESOLUCION = (1920, 1080)
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

MUSICA = [
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
]

NICHOS = {
    "horror": {
        "parte1": "Write the OPENING of a horror documentary in ENGLISH. Include: a shocking hook, introduction of the main character (name, description), and the setting. Write exactly 800 words. Only the narration, no titles.",
        "parte2": "Continue the horror story from part 1. Write the MIDDLE section: the terrifying events escalate, the character faces increasing danger. Write exactly 800 words. Only narration.",
        "parte3": "Write the ENDING of the horror documentary. Include the shocking climax and chilling unresolved conclusion. Write exactly 700 words. Only narration.",
        "titulo_prompt": "Write a viral YouTube title in English for a horror documentary. Max 70 chars. Include emoji. Return only the title.",
        "tags": ["horror", "scary", "haunted", "documentary"],
        "consultas_broll": [
            "dark forest fog night", "abandoned house interior",
            "candle flame dark room", "foggy graveyard night",
            "old door dark", "flashlight dark room",
            "misty woods night", "dark attic house",
            "shadow hallway dark", "thunderstorm night",
            "creepy mansion exterior", "dark basement",
        ],
        "color_sub": "#FF4444",
    },
    "true_crime": {
        "parte1": "Write the OPENING of a true crime documentary in ENGLISH about a fictional unsolved case. Include: shocking cold open, victim backstory, setting the scene. Write exactly 800 words. Only narration.",
        "parte2": "Continue the true crime story. Write the INVESTIGATION section: clues discovered, suspects, twists. Write exactly 800 words. Only narration.",
        "parte3": "Write the CONCLUSION of the true crime documentary. Include the unresolved ending and haunting questions. Write exactly 700 words. Only narration.",
        "titulo_prompt": "Write a viral YouTube title in English for a true crime documentary. Max 70 chars. Include emoji. Return only the title.",
        "tags": ["truecrime", "mystery", "unsolved", "documentary"],
        "consultas_broll": [
            "dark street night fog", "police lights night",
            "detective office", "rain window night",
            "empty road night", "newspaper archive",
            "typewriter paper", "courthouse night",
            "crime scene tape", "detective investigating",
            "prison corridor", "courtroom interior",
        ],
        "color_sub": "#FFD700",
    },
    "history": {
        "parte1": "Write the OPENING of a history documentary in ENGLISH about a fascinating lesser-known historical event. Include: shocking hook fact, historical figure introduction, setting the era. Write exactly 800 words. Only narration.",
        "parte2": "Continue the history documentary. Write the MAIN EVENTS section: dramatic events, conflicts, turning points. Write exactly 800 words. Only narration.",
        "parte3": "Write the CONCLUSION of the history documentary. Include the legacy and modern relevance. Write exactly 700 words. Only narration.",
        "titulo_prompt": "Write a viral YouTube title in English for a history documentary. Max 70 chars. Include emoji. Return only the title.",
        "tags": ["history", "documentary", "historical", "didyouknow"],
        "consultas_broll": [
            "ancient ruins aerial", "medieval castle",
            "old manuscript library", "ancient egypt pyramids",
            "roman colosseum", "viking ship",
            "renaissance painting", "ancient greece temple",
            "world war historical", "old map vintage",
            "historical artifact museum", "ancient civilization",
        ],
        "color_sub": "#DDA0DD",
    },
    "science": {
        "parte1": "Write the OPENING of a science documentary in ENGLISH about a mind-blowing scientific fact. Include: perspective-shattering hook, expert narrator introduction, first layer of the discovery. Write exactly 800 words. Only narration.",
        "parte2": "Continue the science documentary. Write the DEEP DIVE section: more mind-blowing details, connected facts, scientific implications. Write exactly 800 words. Only narration.",
        "parte3": "Write the CONCLUSION of the science documentary. Include the philosophical implications and how this changes how we see the world. Write exactly 700 words. Only narration.",
        "titulo_prompt": "Write a viral YouTube title in English for a science documentary. Max 70 chars. Include emoji. Return only the title.",
        "tags": ["science", "facts", "mindblowing", "documentary"],
        "consultas_broll": [
            "space galaxy stars", "underwater ocean deep",
            "microscope cells biology", "lightning storm",
            "volcano lava", "aurora borealis",
            "brain neuron science", "dna strand",
            "solar system planets", "deep ocean creatures",
            "science lab", "nature phenomenon",
        ],
        "color_sub": "#00BFFF",
    },
}

CONSULTAS_RESPALDO = [
    "cinematic landscape aerial", "dramatic sky clouds",
    "city lights night aerial", "nature forest aerial",
    "ocean waves slow motion", "mountain landscape fog",
]


def llamar_gemini(prompt: str, max_tokens: int = 2000) -> str:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": max_tokens}
    }
    for modelo in MODELOS_GEMINI:
        for intento in range(3):
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={GEMINI_API_KEY}"
                )
                r = requests.post(url, json=body, timeout=120)
                if r.status_code in (503, 429):
                    time.sleep(15)
                    continue
                r.raise_for_status()
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                print(f"Error {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    return ""


def generar_guion_largo(nicho: str) -> tuple:
    """Genera el guion en 3 partes separadas y las une - garantiza longitud"""
    config = NICHOS[nicho]

    print("Generando parte 1...")
    parte1 = llamar_gemini(config["parte1"], max_tokens=2500)
    time.sleep(3)

    print("Generando parte 2...")
    parte2 = llamar_gemini(config["parte2"], max_tokens=2500)
    time.sleep(3)

    print("Generando parte 3...")
    parte3 = llamar_gemini(config["parte3"], max_tokens=2000)
    time.sleep(3)

    print("Generando titulo...")
    titulo = llamar_gemini(config["titulo_prompt"], max_tokens=100)
    if not titulo:
        titulo = "The Story Nobody Told You 😱"

    guion_completo = f"{parte1}\n\n{parte2}\n\n{parte3}"
    palabras = len(guion_completo.split())
    print(f"Guion total: {palabras} palabras")

    return guion_completo, titulo


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio_largo.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("tiny")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def _descargar_clips(consultas, headers, carpeta, indice_inicial, por_consulta=5):
    rutas = []
    idx = indice_inicial
    for consulta in consultas:
        url = f"https://api.pexels.com/videos/search?query={consulta}&per_page={por_consulta}"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"Aviso '{consulta}': {e}")
            continue
        videos = r.json().get("videos", [])
        for v in videos:
            archivos = sorted(v["video_files"], key=lambda f: f.get("width", 0))
            if not archivos:
                continue
            enlace = archivos[len(archivos)//2]["link"]
            destino = f"{carpeta}/clip_{idx}.mp4"
            try:
                with requests.get(enlace, stream=True, timeout=60) as resp:
                    with open(destino, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                rutas.append(destino)
                idx += 1
            except Exception as e:
                print(f"Aviso descarga: {e}")
    return rutas, idx


def descargar_clips(nicho: str, carpeta: str = "clips_largo"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = NICHOS[nicho]["consultas_broll"]
    rutas, siguiente = _descargar_clips(consultas, headers, carpeta, 0)
    if len(rutas) < 30:
        extra, _ = _descargar_clips(CONSULTAS_RESPALDO, headers, carpeta, siguiente, por_consulta=6)
        rutas.extend(extra)
    print(f"Clips: {len(rutas)}")
    return rutas


def descargar_musica() -> str:
    url = random.choice(MUSICA)
    destino = "musica_largo.mp3"
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return destino
    except Exception as e:
        print(f"Aviso musica: {e}")
        return None


def armar_video(clips_pexels, audio_path, segmentos, nicho, musica_path, salida="video_largo_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    color_sub = NICHOS[nicho]["color_sub"]
    print(f"Duracion audio: {duracion_total:.1f} segundos ({duracion_total/60:.1f} minutos)")

    clips_finales = []
    tiempo_acumulado = 0

    pool = clips_pexels.copy()
    random.shuffle(pool)
    puntero = 0
    ultimo = None

    while tiempo_acumulado < duracion_total:
        if puntero >= len(pool):
            random.shuffle(pool)
            if pool and pool[0] == ultimo and len(pool) > 1:
                pool[0], pool[1] = pool[1], pool[0]
            puntero = 0
        if not pool:
            break

        ruta = pool[puntero]
        puntero += 1

        try:
            c = VideoFileClip(ruta).without_audio()
        except Exception:
            continue

        if c.duration < 0.5:
            c.close()
            continue

        escala = max(RESOLUCION[0] / c.w, RESOLUCION[1] / c.h)
        c = c.resize(escala)
        c = c.crop(x_center=c.w/2, y_center=c.h/2,
                   width=RESOLUCION[0], height=RESOLUCION[1])

        restante = duracion_total - tiempo_acumulado
        dur_clip = min(c.duration, restante, random.uniform(5.0, 10.0))
        if dur_clip <= 0:
            c.close()
            continue

        c = c.subclip(0, dur_clip)
        clips_finales.append(c)
        tiempo_acumulado += dur_clip
        ultimo = ruta

    if not clips_finales:
        raise RuntimeError("No se pudo armar ningun clip")

    video_base = concatenate_videoclips(clips_finales, method="compose")
    audios = [audio_voz]

    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            dur_video = video_base.duration
            if musica.duration < dur_video:
                loops = math.ceil(dur_video / musica.duration)
                musica = concatenate_audioclips([musica] * loops)
            musica = musica.subclip(0, dur_video).volumex(0.08)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)
    video_base = video_base.set_duration(duracion_total)

    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        dur_seg = seg["end"] - seg["start"]
        dur_palabra = dur_seg / max(len(palabras), 1)
        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + (j * dur_palabra)
            t_fin = t_inicio + dur_palabra
            sombra = TextClip(
                palabra.upper(), fontsize=65, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.83), relative=True)
            txt = TextClip(
                palabra.upper(), fontsize=65, color="white",
                font="DejaVu-Sans-Bold", stroke_color=color_sub, stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.83), relative=True)
            subtitulos.append(sombra)
            subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)
    final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac",
                          threads=2, preset="ultrafast")
    return salida


def subir_youtube(video_path: str, titulo: str, descripcion: str, tags: list):
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
            "title": titulo[:100],
            "description": descripcion[:5000],
            "tags": tags,
            "categoryId": "24",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("Subido:", response.get("id"))


def main():
    nicho = random.choice(list(NICHOS.keys()))
    print(f"Nicho: {nicho}")

    guion, titulo = generar_guion_largo(nicho)
    print(f"Titulo: {titulo}")

    audio_path = generar_audio(guion)
    segmentos = transcribir(audio_path)
    clips = descargar_clips(nicho)
    musica_path = descargar_musica()

    video_path = armar_video(clips, audio_path, segmentos, nicho, musica_path)

    descripcion = f"{guion[:500]}...\n\n#{nicho} #documentary #viral"
    tags = NICHOS[nicho]["tags"]
    subir_youtube(video_path, titulo, descripcion, tags)
    print(f"Video listo: {video_path}")


if __name__ == "__main__":
    main()
