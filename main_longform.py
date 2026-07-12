"""
Pipeline mejorado para videos LARGOS (12-15 min) - Version 3.0
Mejoras:
- Musica de fondo cinematografica automatica
- Intro dramatico con texto animado
- Subtitulos estilo viral palabra por palabra
- Voz dramatica AndrewNeural
- Imagenes IA de personajes y escenas
- 6 nichos: Horror, True Crime, World Records, Top 10, History, Science
- Muchos clips variados, sin pantalla negra
- Guiones nivel Netflix/BBC/Vsauce
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
        "prompt_sistema": """You are a professional horror documentary screenwriter at the level of Netflix originals.
Write a gripping 13-minute horror documentary script in ENGLISH ONLY with:
1. A compelling main character (name, detailed physical description, backstory, what makes them tragic)
2. A terrifying specific location with rich atmospheric detail (sounds, smells, visual details)
3. Structure: cold open with shocking hook that makes viewers unable to look away, slow backstory buildup creating dread, escalating terrifying events, shocking climax, haunting unresolved ending
4. Dialogue-like narration that feels personal and real
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. Aim for 2000-2200 words in the guion.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one sentence that stops the scroll)...",
  "guion": "...(full 13 min narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["horror", "scary", "haunted", "documentary", "horrorstory"]
}""",
        "consultas_broll": [
            "dark forest fog night", "abandoned house interior",
            "candle flame dark room", "foggy graveyard night",
            "old door creaking dark", "flashlight dark room",
            "misty woods path night", "dark attic old house",
            "shadow silhouette dark hallway", "thunderstorm dark night",
            "creepy old mansion exterior", "dark basement horror",
            "abandoned hospital corridor", "spider web dusty room",
            "old rocking chair dark room", "broken window abandoned",
            "dirt road night forest", "old cemetery moonlight",
        ],
        "intro_texto": "The following story will keep you awake at night...",
        "color_subtitulo": "#FF4444",
    },
    "true_crime": {
        "prompt_sistema": """You are a Netflix-level true crime documentary writer.
Write a gripping 13-minute true crime documentary script in ENGLISH ONLY with:
1. A fictional composite investigator (name, background, what drives them to solve cases)
2. A fictional but realistic case set in a specific detailed location
3. Structure: shocking cold open that hooks immediately, victim backstory creating empathy, crime details building suspense, investigation with multiple twists, trial or outcome, haunting unanswered questions
4. Pacing that creates genuine tension and keeps viewers engaged
5. 4 vivid atmospheric scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. Aim for 2000-2200 words. Do not use real named victims.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one sentence that stops the scroll)...",
  "guion": "...(full 13 min narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["truecrime", "mystery", "unsolved", "documentary", "crimestory"]
}""",
        "consultas_broll": [
            "dark street night fog", "police lights night city",
            "old detective office", "rain window night moody",
            "empty road night headlights", "newspaper archive old",
            "typewriter old paper", "courthouse exterior night",
            "crime scene tape", "detective investigating",
            "surveillance camera footage", "prison corridor",
            "courtroom interior", "police station night",
            "evidence board detective", "handcuffs arrest",
            "missing person poster", "newspaper headline crime",
        ],
        "intro_texto": "This case was never meant to be solved...",
        "color_subtitulo": "#FFD700",
    },
    "world_records": {
        "prompt_sistema": """You are a world-class documentary narrator for incredible achievements.
Write a gripping 13-minute world records documentary script in ENGLISH ONLY with:
1. A fictional but inspiring record holder (name, background, what drove them to attempt the impossible)
2. The dramatic location and context of the record attempt
3. Structure: mind-blowing opening stat, character backstory and motivation, training and preparation montage narration, dramatic record attempt with real tension, aftermath and global impact
4. Numbers and comparisons so vivid viewers can actually feel the scale
5. 4 dramatic scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. Aim for 2000-2200 words.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one sentence that stops the scroll)...",
  "guion": "...(full 13 min narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["worldrecord", "guinness", "incredible", "documentary", "amazing"]
}""",
        "consultas_broll": [
            "stadium crowd aerial", "extreme sports action",
            "mountain climbing extreme", "ocean waves aerial",
            "athlete slow motion", "fireworks night sky",
            "skydiving aerial", "olympic stadium crowd",
            "speed racing car", "crowd cheering stadium",
            "world record attempt", "extreme challenge sport",
            "marathon runner crowd", "weightlifting competition",
            "swimming competition pool", "gymnastics performance",
            "extreme altitude mountain", "base jumping cliff",
        ],
        "intro_texto": "No one believed this was humanly possible...",
        "color_subtitulo": "#00FF88",
    },
    "top10": {
        "prompt_sistema": """You are a viral YouTube top 10 documentary creator.
Write a gripping 13-minute top 10 countdown documentary script in ENGLISH ONLY with:
1. A charismatic fictional host narrator (name, personality, expertise)
2. A dramatic framing for the countdown
3. Structure: explosive promise hook, countdown from 10 to 1 with each entry more shocking than the last, each entry has 2-3 paragraphs of rich detail, jaw-dropping number 1 reveal, mind-blowing conclusion that makes viewers share
4. The kind of facts that make people say "no way" out loud
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. Aim for 2000-2200 words.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one sentence that stops the scroll)...",
  "guion": "...(full 13 min narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["top10", "facts", "countdown", "documentary", "mindblowing"]
}""",
        "consultas_broll": [
            "nature landscape aerial drone", "city skyline timelapse night",
            "ocean underwater deep", "desert landscape aerial",
            "mountain range aerial", "wildlife animals nature",
            "space stars galaxy night", "waterfall nature aerial",
            "jungle aerial drone", "glacier ice aerial",
            "volcano eruption lava", "canyon aerial grand",
            "northern lights aurora", "tornado storm dramatic",
            "deep sea creatures ocean", "arctic landscape polar",
        ],
        "intro_texto": "Number 1 on this list defies all logic...",
        "color_subtitulo": "#FF8C00",
    },
    "history_facts": {
        "prompt_sistema": """You are a BBC-level history documentary writer.
Write a gripping 13-minute history documentary script in ENGLISH ONLY about a fascinating lesser-known historical event with:
1. The key historical figure (name, era, vivid physical and personality description, what made them remarkable)
2. The historical setting with rich period atmosphere
3. Structure: shocking hook fact that reframes everything viewer thought they knew, historical context that builds the world, dramatic events with real stakes, turning point moment, legacy and why it matters today
4. Details that make history feel cinematic and alive
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. Aim for 2000-2200 words.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one sentence that stops the scroll)...",
  "guion": "...(full 13 min narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["history", "historyfacts", "documentary", "historical", "didyouknow"]
}""",
        "consultas_broll": [
            "ancient ruins aerial", "medieval castle exterior",
            "old manuscript library", "ancient egypt pyramids aerial",
            "roman colosseum interior", "viking ship ocean",
            "renaissance painting museum", "ancient greece temple",
            "world war historical", "old map vintage paper",
            "historical artifact museum", "ancient civilization ruins",
            "medieval battle reenactment", "old city cobblestone street",
            "ancient scroll writing", "historical ship ocean",
            "royal palace historic", "ancient warrior armor museum",
        ],
        "intro_texto": "This is the history they never taught you...",
        "color_subtitulo": "#DDA0DD",
    },
    "interesting_facts": {
        "prompt_sistema": """You are a Vsauce-level science and curiosity documentary creator.
Write a mind-blowing 13-minute documentary script in ENGLISH ONLY about an incredible scientific fact with:
1. A fictional expert scientist narrator (name, field, charismatic personality, why they are passionate about this)
2. A dramatic setting where this discovery unfolds
3. Structure: perspective-shattering opening fact, layered mind-blowing details that build on each other, rabbit hole of connected surprising facts, philosophical implications that make viewers question reality, ending that permanently changes how viewers see the world
4. The kind of content that makes people pause the video to think
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. Aim for 2000-2200 words.
Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "hook": "...(one sentence that stops the scroll)...",
  "guion": "...(full 13 min narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["facts", "science", "mindblowing", "documentary", "interesting"]
}""",
        "consultas_broll": [
            "space galaxy stars nebula", "underwater ocean deep creatures",
            "microscope cells biology closeup", "lightning storm dramatic",
            "volcano lava flow eruption", "aurora borealis night sky",
            "brain neuron science visualization", "dna strand science",
            "solar system planets space", "deep ocean bioluminescent",
            "science lab experiment", "nature phenomenon aerial",
            "black hole space visualization", "coral reef underwater",
            "tornado formation storm", "supernova star explosion",
        ],
        "intro_texto": "What you are about to learn will change everything...",
        "color_subtitulo": "#00BFFF",
    },
}

CONSULTAS_RESPALDO = [
    "cinematic landscape aerial", "dramatic sky clouds sunset",
    "city lights night aerial", "nature forest aerial drone",
    "ocean waves slow motion", "mountain landscape fog",
    "abstract dark cinematic", "smoke particles cinematic",
]


def generar_guion_extension(nicho: str, guion_corto: str) -> str:
    """Si el guion es muy corto, pide a Gemini que lo extienda"""
    palabras_actuales = len(guion_corto.split())
    palabras_necesarias = 2000 - palabras_actuales
    prompt = f"""You are a documentary writer. 
The following narration script is too short ({palabras_actuales} words).
Extend it by adding {palabras_necesarias} more words IN ENGLISH ONLY.
Keep the same style, characters and story. Just continue and expand the narrative.
Add more details, descriptions, tension, and depth.
Return ONLY the complete extended narration text, no JSON, no titles:

{guion_corto}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4000}
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
            print(f"Error extendiendo guion: {e}")
            time.sleep(5)
    return guion_corto


def generar_contenido(nicho: str) -> dict:
    prompt_sistema = NICHOS[nicho]["prompt_sistema"]
    body = {
        "contents": [{"parts": [{"text": prompt_sistema}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 8000}
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
                    print(f"{r.status_code} en {modelo}, intento {intento+1}/3, esperando 15s...")
                    time.sleep(15)
                    continue
                r.raise_for_status()
                data = r.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r"```json|```", "", texto).strip()
                try:
                    contenido = json.loads(texto)
                    # Verificar que el guion sea suficientemente largo
                    palabras = len(contenido.get("guion", "").split())
                    print(f"Guion generado: {palabras} palabras")
                    if palabras < 1500:
                        print(f"Guion muy corto ({palabras} palabras), extendiendo...")
                        contenido["guion"] = generar_guion_extension(nicho, contenido["guion"])
                        palabras_final = len(contenido["guion"].split())
                        print(f"Guion extendido: {palabras_final} palabras")
                    return contenido
                except json.JSONDecodeError:
                    return {
                        "personaje": {"nombre": "Unknown", "descripcion": "mysterious figure", "backstory": "unknown"},
                        "lugar": {"nombre": "Unknown", "descripcion": "dramatic setting"},
                        "hook": "What happened here changed everything.",
                        "guion": "Something incredible happened here that most people never knew about. The story begins in a place few have visited and fewer have escaped unchanged. What we are about to explore defies conventional explanation and has baffled experts for decades.",
                        "escenas": ["dramatic shot", "close up detail", "wide scene", "final reveal"],
                        "titulo": "The Story Nobody Told You 😱",
                        "descripcion_video": "An incredible untold story. Subscribe for more.",
                        "tags": [nicho, "documentary", "viral", "facts"]
                    }
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_ia_largo") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"cinematic, dramatic lighting, 4k, high quality, professional: {prompt}",
        "parameters": {"width": 1344, "height": 768}
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


def generar_imagenes(contenido: dict) -> list:
    rutas = []
    personaje = contenido.get("personaje", {})
    lugar = contenido.get("lugar", {})
    escenas = contenido.get("escenas", [])

    prompt_personaje = (
        f"Cinematic portrait of {personaje.get('nombre', 'mysterious person')}, "
        f"{personaje.get('descripcion', 'dramatic figure')}, "
        f"in {lugar.get('nombre', 'dramatic setting')}, "
        "dramatic cinematic lighting, 4k film quality"
    )
    ruta = generar_imagen_ia(prompt_personaje, 0)
    if ruta:
        rutas.append(ruta)

    for i, escena in enumerate(escenas[:4]):
        ruta = generar_imagen_ia(
            f"{escena}, {lugar.get('descripcion', 'dramatic')}, cinematic 4k", i + 1
        )
        if ruta:
            rutas.append(ruta)
    return rutas


def crear_intro_imagen(hook: str, nicho: str) -> str:
    img = Image.new("RGB", RESOLUCION, color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(RESOLUCION[1]):
        alpha = int(15 + (y / RESOLUCION[1]) * 25)
        draw.line([(0, y), (RESOLUCION[0], y)], fill=(alpha, 0, 0))

    draw.rectangle([(0, 0), (RESOLUCION[0], 6)], fill=(200, 0, 0))
    draw.rectangle([(0, RESOLUCION[1]-6), (RESOLUCION[0], RESOLUCION[1])], fill=(200, 0, 0))

    try:
        font_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 65)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    except:
        font_grande = ImageFont.load_default()
        font_small = font_grande

    palabras = hook.split()
    lineas = []
    linea_actual = ""
    for palabra in palabras:
        test = linea_actual + " " + palabra if linea_actual else palabra
        if len(test) < 32:
            linea_actual = test
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
        draw.text((x+3, y_start+3), linea, font=font_grande, fill=(0, 0, 0))
        draw.text((x, y_start), linea, font=font_grande, fill=(255, 255, 255))
        y_start += 85

    destino = "intro_largo.png"
    img.save(destino)
    return destino


def descargar_musica(nicho: str) -> str:
    urls = MUSICA_AMBIENTE.get(nicho, MUSICA_AMBIENTE["horror"])
    url = random.choice(urls)
    destino = "musica_largo.mp3"
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


def generar_audio(texto: str, salida: str = "audio_largo.mp3"):
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
            print(f"Aviso '{consulta}': {e}")
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


def descargar_clips(nicho: str, carpeta: str = "clips_largo"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = NICHOS[nicho]["consultas_broll"]
    rutas, siguiente = _descargar_desde_consultas(consultas, headers, carpeta, 0)
    if len(rutas) < 40:
        print(f"Solo {len(rutas)} clips, completando...")
        extra, _ = _descargar_desde_consultas(
            CONSULTAS_RESPALDO, headers, carpeta, siguiente, por_consulta=8
        )
        rutas.extend(extra)
    print(f"Total clips: {len(rutas)}")
    return rutas


def armar_video(clips_pexels, imagenes_ia, audio_path, segmentos,
                nicho, intro_img, musica_path, salida="video_largo_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    color_sub = NICHOS[nicho]["color_subtitulo"]
    OFFSET = 4.0  # duracion del intro

    clips_finales = []
    tiempo_acumulado = 0

    # 1. Intro (4s)
    if intro_img:
        try:
            intro = ImageClip(intro_img).set_duration(OFFSET)
            clips_finales.append(intro)
            tiempo_acumulado += OFFSET
        except Exception as e:
            print(f"Aviso intro: {e}")

    # 2. Imagenes IA (5s cada una)
    for ruta_img in imagenes_ia:
        if tiempo_acumulado >= duracion_total + OFFSET:
            break
        try:
            dur = min(5.0, (duracion_total + OFFSET) - tiempo_acumulado)
            c = ImageClip(ruta_img).set_duration(dur)
            clips_finales.append(c)
            tiempo_acumulado += dur
        except Exception as e:
            print(f"Aviso imagen: {e}")

    # 3. Clips de Pexels
    pool = clips_pexels.copy()
    random.shuffle(pool)
    puntero = 0
    ultimo = None

    while tiempo_acumulado < duracion_total + OFFSET:
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

        restante = (duracion_total + OFFSET) - tiempo_acumulado
        dur_clip = min(c.duration, restante, random.uniform(4.0, 9.0))
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

    # Audio: voz empieza despues del intro
    audio_voz = audio_voz.set_start(OFFSET)
    audios = [audio_voz]

    # Musica de fondo a volumen bajo
    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            duracion_video = video_base.duration
            if musica.duration < duracion_video:
                loops = math.ceil(duracion_video / musica.duration)
                musica = concatenate_audioclips([musica] * loops)
            musica = musica.subclip(0, duracion_video).volumex(0.10)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)
    video_base = video_base.set_duration(duracion_total + OFFSET)

    # Subtitulos palabra por palabra estilo viral
    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        duracion_seg = seg["end"] - seg["start"]
        dur_palabra = duracion_seg / max(len(palabras), 1)

        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + OFFSET + (j * dur_palabra)
            t_fin = t_inicio + dur_palabra

            sombra = TextClip(
                palabra.upper(), fontsize=70, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.83), relative=True)

            txt = TextClip(
                palabra.upper(), fontsize=70, color="white",
                font="DejaVu-Sans-Bold", stroke_color=color_sub, stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.83), relative=True)

            subtitulos.append(sombra)
            subtitulos.append(txt)

    # Texto del intro
    intro_txt = TextClip(
        NICHOS[nicho]["intro_texto"].upper(),
        fontsize=50, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=2,
        size=(RESOLUCION[0]-160, None), method="caption"
    ).set_start(0).set_end(OFFSET).set_position(("center", 0.45), relative=True)
    subtitulos.append(intro_txt)

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
    nicho = random.choice(list(NICHOS.keys()))
    print(f"Nicho: {nicho}")

    contenido = generar_contenido(nicho)
    print(f"Personaje: {contenido['personaje']['nombre']}")
    print(f"Hook: {contenido.get('hook', '')}")
    palabras = len(contenido["guion"].split())
    print(f"Guion: {palabras} palabras")

    imagenes_ia = generar_imagenes(contenido)
    intro_img = crear_intro_imagen(contenido.get("hook", NICHOS[nicho]["intro_texto"]), nicho)
    musica_path = descargar_musica(nicho)

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    clips = descargar_clips(nicho)

    video_path = armar_video(
        clips, imagenes_ia, audio_path, segmentos,
        nicho, intro_img, musica_path
    )

    titulo = contenido.get("titulo", "The Story Nobody Told You 😱")
    descripcion_base = contenido.get("descripcion_video", "")
    descripcion = f"{descripcion_base}\n\n{contenido['guion'][:300]}...\n\n#{nicho.replace('_','')} #documentary"
    tags = contenido.get("tags", [nicho, "documentary", "viral"])
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
