"""
Pipeline mejorado para Shorts - Version 3.0
Mejoras:
- Musica de fondo automatica (Pixabay, libre de derechos)
- Intro dramatico con texto animado
- Subtitulos estilo viral (palabras individuales resaltadas)
- Voz mas dramatica (AndrewNeural)
- Efectos de sonido de suspenso
- Imagenes IA con personajes
- 6 nichos: Horror, True Crime, World Records, Top 10, History, Science Facts
- Sin pantalla negra, muchos clips variados
"""

import os
import io
import re
import time
import random
import requests
import asyncio
import json
import edge_tts
import whisper
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ImageClip, concatenate_videoclips, AudioArrayClip
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

MUSICA_AMBIENTE = {
    "horror": [
        "https://cdn.pixabay.com/download/audio/2022/03/10/audio_270f4b1fbe.mp3",
        "https://cdn.pixabay.com/download/audio/2021/09/06/audio_dad6b6ef7f.mp3",
    ],
    "true_crime": [
        "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3",
        "https://cdn.pixabay.com/download/audio/2021/08/09/audio_99bbbd8a4c.mp3",
    ],
    "world_records": [
        "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
        "https://cdn.pixabay.com/download/audio/2021/11/25/audio_5bbc9a1a1c.mp3",
    ],
    "top10": [
        "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
        "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    ],
    "history_facts": [
        "https://cdn.pixabay.com/download/audio/2021/11/01/audio_cb91762d6e.mp3",
        "https://cdn.pixabay.com/download/audio/2022/02/07/audio_4a56f2830c.mp3",
    ],
    "interesting_facts": [
        "https://cdn.pixabay.com/download/audio/2022/03/10/audio_270f4b1fbe.mp3",
        "https://cdn.pixabay.com/download/audio/2021/08/09/audio_99bbbd8a4c.mp3",
    ],
}

NICHOS = {
    "horror": {
        "prompt_sistema": """You are a professional horror screenwriter.
Create a short horror story script with:
1. A main character (name, age, physical description, personality)
2. A specific terrifying location (describe in detail)
3. Narrative arc: eerie opening, building dread, shocking climax, chilling ending
4. 3 vivid scene descriptions for AI image generation
5. A hook line (first sentence that stops the scroll)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one shocking first sentence)...",
  "guion": "...(55 second narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "tags": ["horror", "scary", "creepypasta", "shorts"]
}""",
        "consultas_broll": [
            "dark forest fog night", "abandoned house interior",
            "candle flame dark room", "foggy graveyard night",
            "old door creaking dark", "flashlight dark room",
            "misty woods path night", "dark attic old house",
            "shadow silhouette dark hallway", "thunderstorm dark night",
            "creepy old mansion exterior", "dark basement horror",
        ],
        "intro_texto": "WARNING: This story is not for the faint of heart...",
        "color_subtitulo": "#FF4444",
    },
    "true_crime": {
        "prompt_sistema": """You are a professional true crime documentary writer.
Create a gripping true crime story with:
1. A fictional composite investigator (name, description, role)
2. A fictional location where events took place
3. Narrative: cold open hook, investigation, twist, unresolved ending
4. 3 vivid atmospheric scene descriptions for AI image generation
5. A hook line (first sentence that stops the scroll)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one shocking first sentence)...",
  "guion": "...(55 second narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "tags": ["truecrime", "mystery", "unsolved", "shorts"]
}""",
        "consultas_broll": [
            "dark street night fog", "police lights night city",
            "old detective office", "rain window night moody",
            "empty road night headlights", "newspaper archive old",
            "typewriter old paper", "courthouse exterior night",
            "crime scene tape", "detective investigating",
            "surveillance camera footage", "prison corridor",
        ],
        "intro_texto": "This case was never solved...",
        "color_subtitulo": "#FFD700",
    },
    "world_records": {
        "prompt_sistema": """You are an exciting documentary narrator for world records.
Create a world record script with:
1. A fictional record holder (name, description, what they achieved)
2. Location where the record was set
3. Exciting narrative with vivid numbers and mind-blowing comparisons
4. 3 dramatic scene descriptions for AI image generation
5. A hook line (first sentence that stops the scroll)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one shocking first sentence)...",
  "guion": "...(55 second narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "tags": ["worldrecord", "guinness", "amazing", "shorts"]
}""",
        "consultas_broll": [
            "stadium crowd aerial", "extreme sports action",
            "mountain climbing extreme", "ocean waves aerial",
            "athlete slow motion", "fireworks night sky",
            "skydiving aerial", "olympic stadium crowd",
            "speed racing car", "crowd cheering stadium",
            "world record attempt", "extreme challenge sport",
        ],
        "intro_texto": "You won't believe this world record...",
        "color_subtitulo": "#00FF88",
    },
    "top10": {
        "prompt_sistema": """You are a captivating top 10 countdown narrator.
Create a top 10 countdown script with:
1. A dramatic host character (name, charismatic description)
2. A dramatic countdown setting
3. Fast punchy narration building to the most shocking entry at number 1
4. 3 vivid scene descriptions for AI image generation
5. A hook line (first sentence that stops the scroll)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one shocking first sentence)...",
  "guion": "...(55 second narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "tags": ["top10", "facts", "ranking", "shorts"]
}""",
        "consultas_broll": [
            "nature landscape aerial", "city skyline timelapse",
            "ocean underwater", "desert landscape aerial",
            "mountain range aerial", "wildlife animals",
            "space stars night sky", "waterfall nature",
            "jungle aerial drone", "glacier ice aerial",
            "volcano eruption", "canyon aerial view",
        ],
        "intro_texto": "Number 1 will blow your mind...",
        "color_subtitulo": "#FF8C00",
    },
    "history_facts": {
        "prompt_sistema": """You are a fascinating history documentary narrator.
Create a script about an incredible lesser-known historical fact with:
1. A key historical figure (name, description, era)
2. The historical location or setting
3. Narrative: hook with shocking fact, context, surprising details, modern relevance
4. 3 vivid scene descriptions for AI image generation
5. A hook line (first sentence that stops the scroll)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one shocking first sentence)...",
  "guion": "...(55 second narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "tags": ["history", "historyfacts", "didyouknow", "shorts"]
}""",
        "consultas_broll": [
            "ancient ruins aerial", "medieval castle exterior",
            "old manuscript library", "ancient egypt pyramids",
            "roman colosseum", "viking ship ocean",
            "renaissance painting museum", "ancient greece temple",
            "world war historical", "old map vintage",
            "historical artifact museum", "ancient civilization ruins",
        ],
        "intro_texto": "History never told you this...",
        "color_subtitulo": "#DDA0DD",
    },
    "interesting_facts": {
        "prompt_sistema": """You are an energetic science and curiosity narrator.
Create a script about a mind-blowing interesting fact with:
1. A fictional scientist or expert (name, field, description)
2. A dramatic setting where this fact is revealed
3. Narrative: shocking hook, explanation, mind-blowing details, perspective-changing ending
4. 3 vivid scene descriptions for AI image generation
5. A hook line (first sentence that stops the scroll)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one shocking first sentence)...",
  "guion": "...(55 second narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "tags": ["facts", "science", "mindblowing", "shorts"]
}""",
        "consultas_broll": [
            "space galaxy stars", "underwater ocean deep",
            "microscope cells biology", "lightning storm",
            "volcano lava flow", "aurora borealis night",
            "brain neuron science", "dna strand science",
            "solar system planets", "deep ocean creatures",
            "science lab experiment", "nature phenomenon aerial",
        ],
        "intro_texto": "Science just broke your brain...",
        "color_subtitulo": "#00BFFF",
    },
}

CONSULTAS_RESPALDO = [
    "cinematic dark background", "abstract dark texture",
    "smoke slow motion dark", "clouds timelapse dark",
    "light rays dark room", "particles floating dark",
    "cinematic nature landscape", "dramatic sky clouds",
]


def generar_contenido(nicho: str) -> dict:
    prompt_sistema = NICHOS[nicho]["prompt_sistema"]
    body = {
        "contents": [{"parts": [{"text": prompt_sistema}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1500}
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
                    print(f"{r.status_code} en {modelo}, intento {intento+1}/3, esperando 15s...")
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
                        "personaje": {"nombre": "Unknown", "descripcion": "mysterious figure", "personalidad": "enigmatic"},
                        "lugar": {"nombre": "Unknown", "descripcion": "dramatic setting"},
                        "hook": "What happened next shocked everyone.",
                        "guion": "Something terrifying happened here that most people never knew about.",
                        "escenas": ["dark mysterious scene", "tense atmospheric moment", "chilling final scene"],
                        "titulo": "You Won't Believe This 😱",
                        "tags": [nicho, "shorts", "viral", "facts"]
                    }
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_ia") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"cinematic, dramatic lighting, high quality, 4k: {prompt}",
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
        print(f"Imagen IA: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso imagen IA: {e}")
        return None


def generar_imagenes_personaje(contenido: dict) -> list:
    rutas = []
    personaje = contenido.get("personaje", {})
    lugar = contenido.get("lugar", {})
    escenas = contenido.get("escenas", [])

    prompt_personaje = (
        f"Cinematic portrait of {personaje.get('nombre', 'mysterious person')}, "
        f"{personaje.get('descripcion', 'dramatic figure')}, "
        f"in {lugar.get('nombre', 'dramatic setting')}, "
        "dramatic cinematic lighting, film quality"
    )
    ruta = generar_imagen_ia(prompt_personaje, 0)
    if ruta:
        rutas.append(ruta)

    for i, escena in enumerate(escenas[:3]):
        ruta = generar_imagen_ia(
            f"{escena}, {lugar.get('descripcion', 'dramatic')}, cinematic quality", i + 1
        )
        if ruta:
            rutas.append(ruta)
    return rutas


def crear_intro_imagen(texto: str, nicho: str) -> str:
    """Crea una imagen de intro dramatica con texto grande"""
    img = Image.new("RGB", RESOLUCION, color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Gradiente oscuro de fondo
    for y in range(RESOLUCION[1]):
        alpha = int(30 + (y / RESOLUCION[1]) * 20)
        draw.line([(0, y), (RESOLUCION[0], y)], fill=(alpha, 0, 0))

    # Linea roja en la parte superior
    draw.rectangle([(0, 0), (RESOLUCION[0], 8)], fill=(200, 0, 0))

    # Texto centrado
    try:
        font_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_pequeño = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        font_grande = ImageFont.load_default()
        font_pequeño = ImageFont.load_default()

    # Texto principal
    palabras = texto.split()
    lineas = []
    linea_actual = ""
    for palabra in palabras:
        if len(linea_actual + " " + palabra) < 20:
            linea_actual += " " + palabra if linea_actual else palabra
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    if linea_actual:
        lineas.append(linea_actual)

    y_start = RESOLUCION[1] // 2 - (len(lineas) * 80) // 2
    for linea in lineas:
        bbox = draw.textbbox((0, 0), linea, font=font_grande)
        w = bbox[2] - bbox[0]
        x = (RESOLUCION[0] - w) // 2
        draw.text((x + 3, y_start + 3), linea, font=font_grande, fill=(0, 0, 0))
        draw.text((x, y_start), linea, font=font_grande, fill=(255, 255, 255))
        y_start += 90

    destino = "intro_imagen.png"
    img.save(destino)
    return destino


def descargar_musica(nicho: str) -> str:
    """Descarga musica de ambiente libre de derechos"""
    urls = MUSICA_AMBIENTE.get(nicho, MUSICA_AMBIENTE["horror"])
    url = random.choice(urls)
    destino = "musica_fondo.mp3"
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Musica descargada: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso musica: {e}")
        return None


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("tiny")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def _descargar_desde_consultas(consultas, headers, carpeta, indice_inicial, por_consulta=6):
    rutas = []
    indice_global = indice_inicial
    for consulta in consultas:
        url = f"https://api.pexels.com/videos/search?query={consulta}&per_page={por_consulta}"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"Aviso busqueda '{consulta}': {e}")
            continue
        videos = r.json().get("videos", [])
        print(f"'{consulta}': {len(videos)} clips")
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
            except Exception as e:
                print(f"Aviso descarga: {e}")
    return rutas, indice_global


def descargar_clips(nicho: str, carpeta: str = "clips"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = NICHOS[nicho]["consultas_broll"]
    rutas, siguiente = _descargar_desde_consultas(consultas, headers, carpeta, 0)
    if len(rutas) < 20:
        print(f"Solo {len(rutas)} clips, añadiendo respaldo...")
        extra, _ = _descargar_desde_consultas(CONSULTAS_RESPALDO, headers, carpeta, siguiente)
        rutas.extend(extra)
    print(f"Total clips: {len(rutas)}")
    return rutas


def armar_video(clips_pexels, imagenes_ia, audio_path, segmentos,
                nicho, intro_img, musica_path, salida="video_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    color_sub = NICHOS[nicho]["color_subtitulo"]

    clips_finales = []
    tiempo_acumulado = 0

    # 1. INTRO dramatico (2.5s)
    if intro_img:
        try:
            intro = ImageClip(intro_img).set_duration(2.5)
            clips_finales.append(intro)
            tiempo_acumulado += 2.5
        except Exception as e:
            print(f"Aviso intro: {e}")

    # 2. Imagenes IA (3s cada una)
    for ruta_img in imagenes_ia:
        if tiempo_acumulado >= duracion_total + 2.5:
            break
        try:
            dur = min(3.0, (duracion_total + 2.5) - tiempo_acumulado)
            c = ImageClip(ruta_img).set_duration(dur)
            clips_finales.append(c)
            tiempo_acumulado += dur
        except Exception as e:
            print(f"Aviso imagen: {e}")

    # 3. Clips de Pexels hasta cubrir el audio
    pool = clips_pexels.copy()
    random.shuffle(pool)
    puntero = 0
    ultimo = None

    while tiempo_acumulado < duracion_total + 2.5:
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

        restante = (duracion_total + 2.5) - tiempo_acumulado
        dur_clip = min(c.duration, restante, random.uniform(2.5, 5.0))
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

    # Audio: voz empieza a los 2.5s (despues del intro)
    audio_voz = audio_voz.set_start(2.5)
    audios = [audio_voz]

    # Musica de fondo a volumen bajo
    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            duracion_video = video_base.duration
            # Loopar musica si es mas corta que el video
            if musica.duration < duracion_video:
                import math
                loops = math.ceil(duracion_video / musica.duration)
                from moviepy.editor import concatenate_audioclips
                musica = concatenate_audioclips([musica] * loops)
            musica = musica.subclip(0, duracion_video).volumex(0.12)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica fondo: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)
    video_base = video_base.set_duration(duracion_total + 2.5)

    # Subtitulos estilo viral - palabras individuales resaltadas
    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        duracion_seg = seg["end"] - seg["start"]
        dur_palabra = duracion_seg / max(len(palabras), 1)

        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + 2.5 + (j * dur_palabra)
            t_fin = t_inicio + dur_palabra

            # Sombra
            sombra = TextClip(
                palabra.upper(), fontsize=90, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=4,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 3, int(RESOLUCION[1] * 0.72) + 3), True
            )

            # Texto principal con color del nicho
            txt = TextClip(
                palabra.upper(), fontsize=90, color="white",
                font="DejaVu-Sans-Bold", stroke_color=color_sub, stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.72), relative=True
            )
            subtitulos.append(sombra)
            subtitulos.append(txt)

    # Texto de intro superpuesto
    intro_txt = TextClip(
        NICHOS[nicho]["intro_texto"].upper(),
        fontsize=55, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=2,
        size=(RESOLUCION[0]-80, None), method="caption"
    ).set_start(0).set_end(2.5).set_position(("center", 0.45), relative=True)
    subtitulos.append(intro_txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total + 2.5)
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

    contenido = generar_contenido(nicho)
    print(f"Personaje: {contenido['personaje']['nombre']}")
    print(f"Hook: {contenido.get('hook', '')}")

    imagenes_ia = generar_imagenes_personaje(contenido)
    intro_img = crear_intro_imagen(contenido.get("hook", NICHOS[nicho]["intro_texto"]), nicho)
    musica_path = descargar_musica(nicho)

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    clips = descargar_clips(nicho)

    video_path = armar_video(
        clips, imagenes_ia, audio_path, segmentos,
        nicho, intro_img, musica_path
    )

    titulo = contenido.get("titulo", "You Won't Believe This 😱")
    descripcion = f"{contenido['guion']}\n\n#{nicho.replace('_', '')} #shorts"
    tags = contenido.get("tags", [nicho, "shorts", "viral"])
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
