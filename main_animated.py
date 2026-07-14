"""
Pipeline de historias animadas LARGAS (10-12 minutos)
Personajes consistentes estilo stick figure
Historias completas con arco narrativo, personajes desarrollados
Formato horizontal 1920x1080
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
RESOLUCION = (1920, 1080)
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

ESTILO_BASE = (
    "simple stick figure character illustration, "
    "beige cream background, clean minimal lines, "
    "flat 2D cartoon style, educational animation style, "
    "consistent character design, children book illustration"
)

TEMAS = [
    {"tema": "a caveman who accidentally invents everything", "epoca": "10,000 BC Stone Age"},
    {"tema": "a medieval knight who is secretly a coward", "epoca": "Medieval Europe 1200 AD"},
    {"tema": "an Egyptian pharaoh who hates being pharaoh", "epoca": "Ancient Egypt 1300 BC"},
    {"tema": "a Viking explorer who keeps getting lost", "epoca": "Viking Age 900 AD"},
    {"tema": "a Roman gladiator who wins by total accident", "epoca": "Ancient Rome 100 AD"},
    {"tema": "a pirate captain who is terrified of water", "epoca": "Golden Age of Piracy 1700s"},
    {"tema": "a samurai who wants to be a gardener", "epoca": "Feudal Japan 1600 AD"},
    {"tema": "a cowboy who is allergic to everything in the West", "epoca": "Wild West 1880s"},
    {"tema": "a ninja whose stealth always fails at wrong moments", "epoca": "Edo Period Japan"},
    {"tema": "an ancient Greek hero who needs GPS to find Troy", "epoca": "Ancient Greece 800 BC"},
    {"tema": "a medieval wizard whose spells always backfire", "epoca": "Medieval Fantasy 1100 AD"},
    {"tema": "a Renaissance artist who cannot draw straight lines", "epoca": "Renaissance Italy 1500s"},
]

MUSICA = [
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_5bbc9a1a1c.mp3",
]


def generar_guion_extension(tema: str, guion_corto: str) -> str:
    palabras_actuales = len(guion_corto.split())
    prompt = f"""You are an animated story writer.
The following story about {tema} is too short ({palabras_actuales} words).
Extend it to at least 1800 words total IN ENGLISH ONLY.
Add more scenes, character development, funny moments, plot twists.
Return ONLY the complete extended narration, no JSON, no titles:

{guion_corto}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 6000}
    }
    for modelo in MODELOS_GEMINI:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{modelo}:generateContent?key={GEMINI_API_KEY}"
            )
            r = requests.post(url, json=body, timeout=120)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Error extendiendo: {e}")
            time.sleep(5)
    return guion_corto


def generar_contenido(tema_info: dict) -> dict:
    prompt = f"""You are a viral animated YouTube channel creator like Kurzgesagt or Oversimplified.

Write a funny 11-minute animated story IN ENGLISH ONLY about: {tema_info['tema']}
Setting: {tema_info['epoca']}

Structure (follow exactly):
1. INTRO (1 min): Hook - introduce character with their biggest flaw/problem in a hilarious way
2. BACKSTORY (2 min): Who is this character, their world, why they are the way they are
3. THE PROBLEM (2 min): The main challenge they face, why it is terrible for someone like them
4. ATTEMPTS TO SOLVE (3 min): Multiple funny failed attempts, escalating chaos
5. UNEXPECTED TWIST (2 min): Something completely unexpected changes everything
6. RESOLUTION (1 min): Funny ending that wraps everything up with a moral or ironic twist

Rules:
- FUNNY: Every paragraph should have at least one joke or ironic observation
- SPECIFIC: Use real historical details mixed with absurd humor
- ENGAGING: Each section should end making viewer want to hear what happens next
- EDUCATIONAL: Sneak in real historical facts naturally
- Aim for 1800-2000 words total

IMPORTANT: ENGLISH ONLY. Return ONLY valid JSON, no markdown, no backticks:
{{
  "personaje_nombre": "...(funny historically plausible name)...",
  "personaje_descripcion": "...(simple stick figure: what they wear, defining features)...",
  "personaje_flaw": "...(their main funny flaw in one sentence)...",
  "locacion": "...(specific historical setting with details)...",
  "personajes_secundarios": [
    {{"nombre": "...", "descripcion": "...", "rol": "..."}},
    {{"nombre": "...", "descripcion": "...", "rol": "..."}}
  ],
  "guion": "...(full 11 min narration in ENGLISH, 1800-2000 words, funny and engaging)...",
  "escenas": [
    "...(scene 1: character introduction, full body, setting visible)...",
    "...(scene 2: character facing their main problem)...",
    "...(scene 3: chaos and failed attempts)...",
    "...(scene 4: the unexpected twist moment)...",
    "...(scene 5: funny resolution and ending)...",
    "...(scene 6: all characters together, final scene)..."
  ],
  "titulo": "...(viral YouTube title with emoji, funny and intriguing, max 70 chars)...",
  "descripcion_youtube": "...(5-6 sentences, funny summary, call to action, mention historical period)...",
  "hashtags": "#animation #history #funny #animated #comedy #storytelling #educational #historymemes #cartoon #viral #shorts #animatedstory #historylesson #funnyhistory #kurzgesagt #oversimplified #historyanimated #learnhistory #historyfacts #funfacts #animatedhistory #historymeme #cartoonhistory #epichistory #historylovers"
}}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.92, "maxOutputTokens": 8000}
    }

    for modelo in MODELOS_GEMINI:
        for intento in range(3):
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={GEMINI_API_KEY}"
                )
                r = requests.post(url, json=body, timeout=180)
                if r.status_code in (503, 429):
                    print(f"{r.status_code} en {modelo}, esperando 15s...")
                    time.sleep(15)
                    continue
                r.raise_for_status()
                data = r.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r"```json|```", "", texto).strip()
                try:
                    contenido = json.loads(texto)
                    palabras = len(contenido.get("guion", "").split())
                    print(f"Guion: {palabras} palabras")
                    if palabras < 1400:
                        print(f"Muy corto, extendiendo...")
                        contenido["guion"] = generar_guion_extension(
                            tema_info["tema"], contenido["guion"]
                        )
                        print(f"Extendido: {len(contenido['guion'].split())} palabras")
                    return contenido
                except json.JSONDecodeError:
                    return {
                        "personaje_nombre": "Bob",
                        "personaje_descripcion": "stick figure with funny hat",
                        "personaje_flaw": "always does everything wrong",
                        "locacion": tema_info["epoca"],
                        "personajes_secundarios": [],
                        "guion": f"Meet Bob, the most unlucky person in {tema_info['epoca']}. Everything was going fine until it absolutely wasnt. This is his story.",
                        "escenas": [
                            "Bob standing confused full body",
                            "Bob facing big problem",
                            "chaos everywhere Bob panicking",
                            "unexpected thing happening",
                            "funny resolution Bob happy",
                            "everyone together final scene"
                        ],
                        "titulo": "The Most Unlucky Person in History 😂",
                        "descripcion_youtube": "This animated story will make your day. Subscribe for daily animated stories!",
                        "hashtags": "#animation #funny #history #animated #comedy"
                    }
            except Exception as e:
                print(f"Error {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Gemini failed")


def generar_imagen_escena(nombre: str, descripcion: str, escena: str, indice: int, carpeta: str = "imagenes_animated") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/escena_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    prompt = (
        f"{ESTILO_BASE}, "
        f"main character {nombre}: {descripcion}, "
        f"scene: {escena}, "
        "wide shot showing full scene, multiple characters if mentioned, "
        "clear storytelling illustration, funny and expressive"
    )

    payload = {
        "inputs": prompt,
        "parameters": {"width": 1344, "height": 768}
    }
    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers, json=payload, timeout=90
        )
        r.raise_for_status()
        imagen = Image.open(io.BytesIO(r.content))
        imagen = imagen.resize(RESOLUCION, Image.LANCZOS)
        imagen.save(destino)
        print(f"Escena {indice}: OK")
        return destino
    except Exception as e:
        print(f"Aviso escena {indice}: {e}")
        return None


def generar_imagen_personaje_sheet(contenido: dict) -> str:
    """Genera una character sheet estilo animated con todos los personajes"""
    nombre = contenido.get("personaje_nombre", "Bob")
    descripcion = contenido.get("personaje_descripcion", "stick figure")
    flaw = contenido.get("personaje_flaw", "always unlucky")
    locacion = contenido.get("locacion", "historical setting")

    prompt = (
        f"{ESTILO_BASE}, "
        f"character sheet for {nombre}, {descripcion}, "
        f"show character from front, side, and back views, "
        f"label showing name '{nombre}', "
        f"show character in {locacion} environment, "
        f"multiple poses showing personality: {flaw}, "
        "clean white background sections with labels, professional character reference sheet"
    )

    carpeta = "imagenes_animated"
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/character_sheet.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"width": 1344, "height": 768}
    }
    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers, json=payload, timeout=90
        )
        r.raise_for_status()
        imagen = Image.open(io.BytesIO(r.content))
        imagen = imagen.resize(RESOLUCION, Image.LANCZOS)
        imagen.save(destino)
        print(f"Character sheet: OK")
        return destino
    except Exception as e:
        print(f"Aviso character sheet: {e}")
        return None


def generar_todas_imagenes(contenido: dict) -> list:
    rutas = []
    nombre = contenido.get("personaje_nombre", "Bob")
    descripcion = contenido.get("personaje_descripcion", "stick figure")
    escenas = contenido.get("escenas", [])

    # Character sheet primero
    sheet = generar_imagen_personaje_sheet(contenido)
    if sheet:
        rutas.append(sheet)

    # Cada escena
    for i, escena in enumerate(escenas[:6]):
        ruta = generar_imagen_escena(nombre, descripcion, escena, i)
        if ruta:
            rutas.append(ruta)

    return rutas


def crear_titulo_card(contenido: dict) -> str:
    img = Image.new("RGB", RESOLUCION, color=(245, 235, 210))
    draw = ImageDraw.Draw(img)

    # Marco decorativo
    draw.rectangle([(15, 15), (RESOLUCION[0]-15, RESOLUCION[1]-15)], outline=(80, 50, 20), width=10)
    draw.rectangle([(30, 30), (RESOLUCION[0]-30, RESOLUCION[1]-30)], outline=(80, 50, 20), width=3)

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    except:
        font_big = ImageFont.load_default()
        font_med = font_big
        font_small = font_big

    # "THE STORY OF"
    t1 = "THE STORY OF"
    bbox = draw.textbbox((0, 0), t1, font=font_small)
    draw.text(((RESOLUCION[0] - (bbox[2]-bbox[0]))//2, 80), t1, font=font_small, fill=(120, 80, 40))

    # Nombre del personaje
    nombre = contenido.get("personaje_nombre", "BOB").upper()
    palabras = nombre.split()
    lineas = []
    linea = ""
    for p in palabras:
        test = linea + " " + p if linea else p
        if len(test) < 16:
            linea = test
        else:
            lineas.append(linea)
            linea = p
    if linea:
        lineas.append(linea)

    y = 160
    for l in lineas:
        bbox = draw.textbbox((0, 0), l, font=font_big)
        w = bbox[2] - bbox[0]
        draw.text(((RESOLUCION[0]-w)//2+3, y+3), l, font=font_big, fill=(150, 90, 30))
        draw.text(((RESOLUCION[0]-w)//2, y), l, font=font_big, fill=(60, 30, 10))
        y += 105

    # Linea separadora
    draw.rectangle([(80, y+15), (RESOLUCION[0]-80, y+19)], fill=(120, 70, 30))

    # Flaw del personaje
    flaw = contenido.get("personaje_flaw", "")[:70]
    palabras_f = flaw.split()
    lineas_f = []
    linea_f = ""
    for p in palabras_f:
        test = linea_f + " " + p if linea_f else p
        if len(test) < 40:
            linea_f = test
        else:
            lineas_f.append(linea_f)
            linea_f = p
    if linea_f:
        lineas_f.append(linea_f)

    y2 = y + 40
    for l in lineas_f[:2]:
        bbox = draw.textbbox((0, 0), l, font=font_small)
        w = bbox[2] - bbox[0]
        draw.text(((RESOLUCION[0]-w)//2, y2), l, font=font_small, fill=(80, 50, 20))
        y2 += 50

    # Epoca
    epoca = contenido.get("locacion", "")[:60]
    bbox = draw.textbbox((0, 0), epoca, font=font_small)
    w = bbox[2] - bbox[0]
    draw.rectangle(
        [(RESOLUCION[0]//2 - w//2 - 20, RESOLUCION[1]-120),
         (RESOLUCION[0]//2 + w//2 + 20, RESOLUCION[1]-70)],
        fill=(80, 50, 20)
    )
    draw.text(((RESOLUCION[0]-w)//2, RESOLUCION[1]-115), epoca, font=font_small, fill=(245, 235, 210))

    destino = "titulo_card_animated.png"
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
    OFFSET = 5.0  # titulo card 5 segundos

    clips_finales = []
    tiempo_acumulado = 0

    # Titulo card
    if titulo_card:
        try:
            c = ImageClip(titulo_card).set_duration(OFFSET)
            clips_finales.append(c)
            tiempo_acumulado += OFFSET
        except Exception as e:
            print(f"Aviso titulo: {e}")

    # Distribuir imagenes uniformemente a lo largo del video
    if imagenes:
        dur_por_imagen = duracion_total / len(imagenes)
        for ruta_img in imagenes:
            if tiempo_acumulado >= duracion_total + OFFSET:
                break
            try:
                dur = min(dur_por_imagen, (duracion_total + OFFSET) - tiempo_acumulado)
                c = ImageClip(ruta_img).set_duration(max(dur, 2.0))
                clips_finales.append(c)
                tiempo_acumulado += dur
            except Exception as e:
                print(f"Aviso imagen: {e}")

    # Rellenar si falta
    while tiempo_acumulado < duracion_total + OFFSET and imagenes:
        try:
            ruta_img = random.choice(imagenes)
            restante = (duracion_total + OFFSET) - tiempo_acumulado
            c = ImageClip(ruta_img).set_duration(min(8.0, restante))
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
            musica = musica.subclip(0, dur_video).volumex(0.07)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)
    video_base = video_base.set_duration(duracion_total + OFFSET)

    # Subtitulos - oscuro sobre fondo claro beige
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

            # Fondo blanco semitransparente para legibilidad
            bg = TextClip(
                palabra.upper(), fontsize=72, color="white",
                font="DejaVu-Sans-Bold", stroke_color="white", stroke_width=8,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.83), relative=True)

            txt = TextClip(
                palabra.upper(), fontsize=72, color="#2C1810",
                font="DejaVu-Sans-Bold", stroke_color="#8B4513", stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.83), relative=True)

            subtitulos.append(bg)
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
    tema_info = random.choice(TEMAS)
    print(f"Tema: {tema_info['tema']}")
    print(f"Epoca: {tema_info['epoca']}")

    contenido = generar_contenido(tema_info)
    palabras = len(contenido["guion"].split())
    print(f"Personaje: {contenido['personaje_nombre']}")
    print(f"Guion: {palabras} palabras")

    imagenes = generar_todas_imagenes(contenido)
    titulo_card = crear_titulo_card(contenido)
    musica_path = descargar_musica()

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)

    video_path = armar_video(imagenes, titulo_card, audio_path, segmentos, musica_path)

    titulo = contenido.get("titulo", "The Most Unlucky Person in History 😂")
    descripcion = (
        f"{contenido.get('descripcion_youtube', '')}\n\n"
        f"{contenido.get('hashtags', '#animation #funny #history #animated #comedy')}"
    )
    tags = ["animation", "funny", "history", "animated", "comedy",
            "storytelling", "educational", "cartoon", "viral", "historymemes"]

    subir_youtube(video_path, titulo, descripcion, tags)
    print(f"Video listo: {video_path}")


if __name__ == "__main__":
    main()
