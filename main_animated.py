"""
Pipeline de historias animadas con personajes consistentes estilo stick figure
Genera personajes, escenas y historias cortas virales
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
HF_TOKEN = os.environ["HF_TOKEN"]

VOZ = "en-US-AndrewNeural"
RESOLUCION = (1080, 1920)
HF_MODEL = "black-forest-labs/FLUX.1-schnell"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

ESTILO_PERSONAJE = (
    "simple stick figure character, cartoon illustration style, "
    "white background, clean lines, minimal color, "
    "children book illustration, flat design, consistent character design"
)

TEMAS = [
    "a caveman discovering fire for the first time",
    "a medieval knight who is secretly afraid of everything",
    "an ancient Egyptian pharaoh who hates sand",
    "a Viking who wants to be a chef instead of a warrior",
    "a Roman gladiator who keeps winning by accident",
    "a pirate who gets seasick on every voyage",
    "a samurai who is terrified of mice",
    "a cowboy in the Wild West who is allergic to horses",
    "a ninja who always sneezes at the wrong moment",
    "a Greek hero who is completely lost without GPS",
    "a time traveler who keeps accidentally changing history",
    "an astronaut who forgot their lunch on Earth",
]

MUSICA = [
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
]

HASHTAGS_BASE = [
    "#animation #story #funny #history #cartoon #shorts",
    "#stickfigure #animated #viral #comedy #history",
    "#historystory #animatedshorts #funny #cartoon #viral",
    "#storytelling #animation #comedy #shorts #trending",
]


def generar_contenido(tema: str) -> dict:
    prompt = f"""You are a viral animated YouTube Shorts creator.
Create a 55-second animated story script in ENGLISH ONLY about: {tema}

Rules for maximum virality:
1. First line MUST be hilarious or shocking - stops the scroll instantly
2. Simple clear story with a funny twist or unexpected ending
3. Written as narration for an animated stick figure video
4. Each scene described clearly for illustration
5. Humor should be universal - works for any age

IMPORTANT: ENGLISH ONLY. Return ONLY valid JSON, no markdown:
{{
  "personaje_nombre": "...(funny name for the character)...",
  "personaje_descripcion": "...(simple stick figure description, what they wear)...",
  "locacion": "...(historical setting, described simply)...",
  "hook": "...(first hilarious sentence that stops the scroll)...",
  "guion": "...(full 55 second narration, funny and engaging)...",
  "escenas": [
    "...(scene 1: character introduction, what they look like, setting)...",
    "...(scene 2: the main problem or situation)...",
    "...(scene 3: funny twist or resolution)..."
  ],
  "titulo": "...(viral title with emoji, max 60 chars)...",
  "descripcion_youtube": "...(3-4 sentences, funny and engaging, with call to action)...",
  "hashtags": "...(20-25 relevant hashtags for maximum reach)..."
}}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.95, "maxOutputTokens": 1500}
    }

    for modelo in MODELOS_GEMINI:
        for intento in range(3):
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={GEMINI_API_KEY}"
                )
                r = requests.post(url, json=body, timeout=60)
                if r.status_code in (503, 429):
                    time.sleep(15)
                    continue
                r.raise_for_status()
                data = r.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r"```json|```", "", texto).strip()
                try:
                    return json.loads(texto)
                except json.JSONDecodeError:
                    return {
                        "personaje_nombre": "Bob",
                        "personaje_descripcion": "simple stick figure with a funny hat",
                        "locacion": "ancient times",
                        "hook": "This guy had the worst day in human history.",
                        "guion": f"Meet {tema}. Everything was going fine until it wasn't.",
                        "escenas": ["character standing confused", "chaos happening", "funny resolution"],
                        "titulo": "The Most Unlucky Guy in History 😂",
                        "descripcion_youtube": "This animated story will make your day. Subscribe for daily animated stories!",
                        "hashtags": "#animation #funny #history #shorts #viral #cartoon #comedy #storytelling"
                    }
            except Exception as e:
                print(f"Error {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Gemini failed")


def generar_imagen_personaje(nombre: str, descripcion: str, escena: str, indice: int, carpeta: str = "imagenes_animated") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/escena_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    prompt_completo = (
        f"{ESTILO_PERSONAJE}, "
        f"character named {nombre}, {descripcion}, "
        f"scene: {escena}, "
        "beige/cream background, educational illustration style, "
        "character sheet style, detailed but simple"
    )

    payload = {
        "inputs": prompt_completo,
        "parameters": {"width": 768, "height": 1344}
    }
    try:
        r = requests.post(
            f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}",
            headers=headers, json=payload, timeout=90
        )
        r.raise_for_status()
        imagen = Image.open(io.BytesIO(r.content))
        imagen = imagen.resize(RESOLUCION, Image.LANCZOS)
        imagen.save(destino)
        print(f"Escena {indice}: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso imagen {indice}: {e}")
        return None


def generar_todas_imagenes(contenido: dict) -> list:
    rutas = []
    nombre = contenido.get("personaje_nombre", "Bob")
    descripcion = contenido.get("personaje_descripcion", "stick figure")
    escenas = contenido.get("escenas", [])

    # Imagen de presentación del personaje (estilo character sheet)
    ruta = generar_imagen_personaje(
        nombre, descripcion,
        f"character sheet showing {nombre} from front, standing pose, full body, with name label",
        0
    )
    if ruta:
        rutas.append(ruta)

    # Cada escena de la historia
    for i, escena in enumerate(escenas[:3]):
        ruta = generar_imagen_personaje(nombre, descripcion, escena, i + 1)
        if ruta:
            rutas.append(ruta)

    return rutas


def crear_titulo_card(contenido: dict) -> str:
    """Crea una tarjeta de titulo estilo animated story"""
    img = Image.new("RGB", RESOLUCION, color=(245, 235, 210))
    draw = ImageDraw.Draw(img)

    # Borde decorativo
    draw.rectangle([(20, 20), (RESOLUCION[0]-20, RESOLUCION[1]-20)], outline=(80, 60, 40), width=8)
    draw.rectangle([(35, 35), (RESOLUCION[0]-35, RESOLUCION[1]-35)], outline=(80, 60, 40), width=3)

    try:
        font_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 75)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_grande = ImageFont.load_default()
        font_med = font_grande
        font_small = font_grande

    # "THE STORY OF"
    texto1 = "THE STORY OF"
    bbox = draw.textbbox((0, 0), texto1, font=font_small)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUCION[0]-w)//2, 120), texto1, font=font_small, fill=(100, 80, 60))

    # Nombre del personaje
    nombre = contenido.get("personaje_nombre", "BOB").upper()
    palabras = nombre.split()
    lineas = []
    linea = ""
    for p in palabras:
        test = linea + " " + p if linea else p
        if len(test) < 14:
            linea = test
        else:
            lineas.append(linea)
            linea = p
    if linea:
        lineas.append(linea)

    y = 200
    for l in lineas:
        bbox = draw.textbbox((0, 0), l, font=font_grande)
        w = bbox[2] - bbox[0]
        draw.text(((RESOLUCION[0]-w)//2 + 3, y+3), l, font=font_grande, fill=(150, 100, 50))
        draw.text(((RESOLUCION[0]-w)//2, y), l, font=font_grande, fill=(80, 40, 10))
        y += 90

    # Hook
    hook = contenido.get("hook", "")[:60]
    palabras_h = hook.split()
    lineas_h = []
    linea_h = ""
    for p in palabras_h:
        test = linea_h + " " + p if linea_h else p
        if len(test) < 28:
            linea_h = test
        else:
            lineas_h.append(linea_h)
            linea_h = p
    if linea_h:
        lineas_h.append(linea_h)

    y_h = RESOLUCION[1] // 2 + 80
    for l in lineas_h[:3]:
        bbox = draw.textbbox((0, 0), l, font=font_small)
        w = bbox[2] - bbox[0]
        draw.text(((RESOLUCION[0]-w)//2, y_h), l, font=font_small, fill=(60, 40, 20))
        y_h += 50

    destino = "titulo_card.png"
    img.save(destino)
    return destino


def descargar_musica() -> str:
    url = random.choice(MUSICA)
    destino = "musica_animated.mp3"
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


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio_animated.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("tiny")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def armar_video(imagenes, titulo_card, audio_path, segmentos, musica_path, salida="video_animated_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    OFFSET = 3.0

    clips_finales = []
    tiempo_acumulado = 0

    # Titulo card (3s)
    if titulo_card:
        try:
            c = ImageClip(titulo_card).set_duration(OFFSET)
            clips_finales.append(c)
            tiempo_acumulado += OFFSET
        except Exception as e:
            print(f"Aviso titulo card: {e}")

    # Imagenes de escenas - cada una dura proporcional al audio
    if imagenes:
        dur_por_imagen = (duracion_total) / len(imagenes)
        for ruta_img in imagenes:
            if tiempo_acumulado >= duracion_total + OFFSET:
                break
            try:
                dur = min(dur_por_imagen, (duracion_total + OFFSET) - tiempo_acumulado)
                c = ImageClip(ruta_img).set_duration(max(dur, 1.0))
                clips_finales.append(c)
                tiempo_acumulado += dur
            except Exception as e:
                print(f"Aviso imagen: {e}")

    # Rellenar si falta tiempo
    while tiempo_acumulado < duracion_total + OFFSET and imagenes:
        try:
            ruta_img = random.choice(imagenes)
            restante = (duracion_total + OFFSET) - tiempo_acumulado
            c = ImageClip(ruta_img).set_duration(min(5.0, restante))
            clips_finales.append(c)
            tiempo_acumulado += c.duration
        except:
            break

    if not clips_finales:
        raise RuntimeError("No se pudo armar el video")

    video_base = concatenate_videoclips(clips_finales, method="compose")

    # Audio
    audio_voz = audio_voz.set_start(OFFSET)
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
    video_base = video_base.set_duration(duracion_total + OFFSET)

    # Subtitulos palabra por palabra - oscuro sobre fondo claro
    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        dur_seg = seg["end"] - seg["start"]
        dur_palabra = dur_seg / max(len(palabras), 1)

        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + OFFSET + (j * dur_palabra)
            t_fin = t_inicio + dur_palabra

            # Fondo semitransparente para legibilidad sobre imagen clara
            txt = TextClip(
                palabra.upper(), fontsize=85, color="#2C1810",
                font="DejaVu-Sans-Bold", stroke_color="#8B4513", stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.75), relative=True)
            subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total + OFFSET)
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
    tema = random.choice(TEMAS)
    print(f"Tema: {tema}")

    contenido = generar_contenido(tema)
    print(f"Personaje: {contenido['personaje_nombre']}")
    print(f"Hook: {contenido['hook']}")

    imagenes = generar_todas_imagenes(contenido)
    titulo_card = crear_titulo_card(contenido)
    musica_path = descargar_musica()

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)

    video_path = armar_video(imagenes, titulo_card, audio_path, segmentos, musica_path)

    titulo = contenido.get("titulo", "The Most Unlucky Guy in History 😂")
    descripcion = (
        f"{contenido.get('descripcion_youtube', '')}\n\n"
        f"{contenido.get('hashtags', random.choice(HASHTAGS_BASE))}"
    )
    tags = ["animation", "funny", "history", "shorts", "cartoon", "comedy", "storytelling", "animated"]

    subir_youtube(video_path, titulo, descripcion, tags)
    print(f"Video listo: {video_path}")


if __name__ == "__main__":
    main()
