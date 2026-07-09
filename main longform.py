"""
Pipeline para videos LARGOS diarios (12-15 minutos).
6 nichos: Horror, True Crime, World Records, Top 10, History Facts, Interesting Facts.
Guiones cinematograficos con personajes, estructura de documental profesional.
Muchos clips variados, sin pantalla negra, reintentos automaticos.
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
from PIL import Image
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ImageClip, concatenate_videoclips
)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

VOZ = "en-US-GuyNeural"
RESOLUCION = (1920, 1080)
HF_MODEL = "black-forest-labs/FLUX.1-schnell"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

NICHOS = {
    "horror": {
        "prompt_sistema": """You are a professional horror documentary screenwriter.
Write a gripping 13-minute horror documentary script in ENGLISH ONLY with:
1. A compelling main character (name, detailed description, backstory)
2. A terrifying specific location with rich atmospheric detail
3. Structure: cold open with shocking hook, backstory buildup, escalating dread, terrifying climax, haunting unresolved ending that leaves viewers wanting more
4. Real feeling details that make it feel authentic
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH. Aim for 2000-2200 words in the guion.

Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(full 13 minute narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(compelling YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["horror", "scary", "haunted", "documentary", "horror story"]
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
    },
    "true_crime": {
        "prompt_sistema": """You are a Netflix-level true crime documentary writer.
Write a gripping 13-minute true crime documentary script in ENGLISH ONLY with:
1. A fictional composite investigator (name, background, what drives them)
2. A fictional but realistic case set in a specific detailed location
3. Structure: shocking cold open, victim backstory, crime details, investigation twists, trial or outcome, haunting conclusion
4. Suspenseful pacing that keeps viewers glued to the screen
5. 4 vivid atmospheric scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH. Aim for 2000-2200 words in the guion. Do not use real named victims.

Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(full 13 minute narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(compelling YouTube description in ENGLISH, 3-4 sentences)...",
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
    },
    "world_records": {
        "prompt_sistema": """You are a world-class documentary narrator for incredible world records.
Write a gripping 13-minute world records documentary script in ENGLISH ONLY with:
1. A fictional but inspiring record holder (name, background, journey to the record)
2. The dramatic location and context of the record attempt
3. Structure: mind-blowing hook stat, character backstory, training/preparation, record attempt with tension, aftermath and impact
4. Mind-blowing comparisons and vivid numbers that make the scale real
5. 4 dramatic scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH. Aim for 2000-2200 words in the guion.

Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(full 13 minute narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(compelling YouTube description in ENGLISH, 3-4 sentences)...",
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
    },
    "top10": {
        "prompt_sistema": """You are a viral YouTube top 10 documentary creator.
Write a gripping 13-minute top 10 countdown documentary script in ENGLISH ONLY with:
1. A charismatic fictional host narrator (name, personality, description)
2. A dramatic framing for the countdown
3. Structure: explosive hook promise, countdown from 10 to 1 with each entry getting more shocking, jaw-dropping number 1 reveal, mind-blowing conclusion
4. Each entry should have 2-3 sentences of rich detail that make viewers say "no way"
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH. Aim for 2000-2200 words in the guion.

Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(full 13 minute narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(compelling YouTube description in ENGLISH, 3-4 sentences)...",
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
    },
    "history_facts": {
        "prompt_sistema": """You are a BBC-level history documentary writer.
Write a gripping 13-minute history documentary script in ENGLISH ONLY about a fascinating lesser-known historical event or person with:
1. The key historical figure (name, era, vivid description, what made them remarkable)
2. The historical setting with rich period detail
3. Structure: shocking hook fact that changes perspective, historical context, dramatic events, turning point, legacy and modern relevance
4. Details that make history feel alive and cinematic
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH. Aim for 2000-2200 words in the guion.

Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(full 13 minute narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(compelling YouTube description in ENGLISH, 3-4 sentences)...",
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
    },
    "interesting_facts": {
        "prompt_sistema": """You are a Vsauce-level science and curiosity documentary creator.
Write a mind-blowing 13-minute documentary script in ENGLISH ONLY about an incredible scientific or natural fact with:
1. A fictional expert scientist narrator character (name, field, charismatic description)
2. A dramatic setting where this discovery unfolds
3. Structure: perspective-shattering opening fact, building layers of mind-blowing detail, rabbit hole of connected facts, philosophical implications, ending that changes how viewers see the world
4. The kind of content that makes people pause and say "wait, what?"
5. 4 vivid scene descriptions for AI image generation

IMPORTANT: Write EVERYTHING in ENGLISH. Aim for 2000-2200 words in the guion.

Return ONLY valid JSON, no markdown, no backticks:
{
  "personaje": {"nombre": "...", "descripcion": "...", "backstory": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(full 13 minute narration in ENGLISH)...",
  "escenas": ["scene 1", "scene 2", "scene 3", "scene 4"],
  "titulo": "...(viral YouTube title in ENGLISH with emoji)...",
  "descripcion_video": "...(compelling YouTube description in ENGLISH, 3-4 sentences)...",
  "tags": ["facts", "science", "mindblowing", "documentary", "interesting"]
}""",
        "consultas_broll": [
            "space galaxy stars nebula", "underwater ocean deep creatures",
            "microscope cells biology closeup", "lightning storm dramatic",
            "volcano lava flow eruption", "aurora borealis night sky",
            "brain neuron science visualization", "dna strand science",
            "solar system planets space", "deep ocean creatures bioluminescent",
            "science lab experiment", "nature phenomenon aerial",
            "black hole space visualization", "coral reef underwater",
            "atomic particle physics", "tornado formation storm",
            "supernova star explosion", "quantum physics visualization",
        ],
    },
}

CONSULTAS_RESPALDO = [
    "cinematic landscape aerial", "dramatic sky clouds sunset",
    "city lights night aerial", "nature forest aerial drone",
    "ocean waves slow motion", "mountain landscape fog",
    "abstract dark cinematic", "smoke particles cinematic",
]


def generar_contenido(nicho: str) -> dict:
    prompt_sistema = NICHOS[nicho]["prompt_sistema"]
    body = {
        "contents": [{"parts": [{"text": prompt_sistema}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 4000}
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
                    print(f"JSON invalido de {modelo}, usando estructura minima")
                    return {
                        "personaje": {"nombre": "Unknown", "descripcion": "mysterious figure", "backstory": "unknown origins"},
                        "lugar": {"nombre": "Unknown", "descripcion": "dramatic setting"},
                        "guion": "Something incredible happened here. A story that changed everything. The kind of event that historians argue about for centuries. What you are about to hear will make you question everything you thought you knew.",
                        "escenas": ["dramatic establishing shot", "close up mysterious detail", "wide atmospheric scene", "final reveal scene"],
                        "titulo": "The Story Nobody Told You 😱",
                        "descripcion_video": "This documentary explores one of the most fascinating stories ever told. Subscribe for more incredible content.",
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
        "inputs": f"cinematic, dramatic lighting, high quality, 4k, detailed: {prompt}",
        "parameters": {"width": 1344, "height": 768}
    }
    try:
        r = requests.post(
            f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=90
        )
        r.raise_for_status()
        imagen = Image.open(io.BytesIO(r.content))
        imagen = imagen.resize(RESOLUCION, Image.LANCZOS)
        imagen.save(destino)
        print(f"Imagen IA generada: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso: no se pudo generar imagen IA ({e})")
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
        "dramatic cinematic lighting, 4k, film quality, professional"
    )
    ruta = generar_imagen_ia(prompt_personaje, 0)
    if ruta:
        rutas.append(ruta)

    for i, escena in enumerate(escenas[:4]):
        prompt_escena = (
            f"{escena}, {lugar.get('descripcion', 'dramatic setting')}, "
            "cinematic, dramatic lighting, atmospheric, 4k quality"
        )
        ruta = generar_imagen_ia(prompt_escena, i + 1)
        if ruta:
            rutas.append(ruta)

    return rutas


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
            print(f"Aviso: fallo busqueda '{consulta}': {e}")
            continue
        videos = r.json().get("videos", [])
        print(f"Busqueda '{consulta}': {len(videos)} resultados")
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
                print(f"Aviso: fallo descarga clip: {e}")
                continue
    return rutas, indice_global


def descargar_clips(nicho: str, carpeta: str = "clips_largo"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = NICHOS[nicho]["consultas_broll"]
    rutas, siguiente = _descargar_desde_consultas(consultas, headers, carpeta, 0, por_consulta=6)
    if len(rutas) < 40:
        print(f"Solo {len(rutas)} clips, completando con respaldo...")
        extra, siguiente = _descargar_desde_consultas(
            CONSULTAS_RESPALDO, headers, carpeta, siguiente, por_consulta=8
        )
        rutas.extend(extra)
    print(f"Total clips Pexels: {len(rutas)}")
    return rutas


def armar_video(clips_pexels, imagenes_ia, audio_path, segmentos, salida="video_largo_final.mp4"):
    audio = AudioFileClip(audio_path)
    duracion_total = audio.duration

    clips_finales = []
    tiempo_acumulado = 0

    # Imagenes IA intercaladas al inicio (5s cada una para video largo)
    duracion_imagen = 5.0
    for ruta_img in imagenes_ia:
        if tiempo_acumulado >= duracion_total:
            break
        try:
            dur = min(duracion_imagen, duracion_total - tiempo_acumulado)
            c = ImageClip(ruta_img).set_duration(dur)
            clips_finales.append(c)
            tiempo_acumulado += dur
        except Exception as e:
            print(f"Aviso: fallo imagen IA {ruta_img}: {e}")
            continue

    # Clips de Pexels sin repeticion seguida
    pool_pexels = clips_pexels.copy()
    random.shuffle(pool_pexels)
    puntero = 0
    ultimo = None

    while tiempo_acumulado < duracion_total:
        if puntero >= len(pool_pexels):
            random.shuffle(pool_pexels)
            if pool_pexels and pool_pexels[0] == ultimo and len(pool_pexels) > 1:
                pool_pexels[0], pool_pexels[1] = pool_pexels[1], pool_pexels[0]
            puntero = 0

        if not pool_pexels:
            break

        ruta = pool_pexels[puntero]
        puntero += 1

        try:
            c = VideoFileClip(ruta).without_audio()
        except Exception:
            continue

        if c.duration < 0.5:
            c.close()
            continue

        # Escalar para cubrir TODO el frame sin negro
        escala = max(RESOLUCION[0] / c.w, RESOLUCION[1] / c.h)
        c = c.resize(escala)
        c = c.crop(
            x_center=c.w / 2, y_center=c.h / 2,
            width=RESOLUCION[0], height=RESOLUCION[1]
        )

        restante = duracion_total - tiempo_acumulado
        # Clips mas largos que en Shorts (4-9s) para sensacion mas cinematografica
        duracion_clip = min(c.duration, restante, random.uniform(4.0, 9.0))
        if duracion_clip <= 0:
            c.close()
            continue

        c = c.subclip(0, duracion_clip)
        clips_finales.append(c)
        tiempo_acumulado += duracion_clip
        ultimo = ruta

    if not clips_finales:
        raise RuntimeError("No se pudo armar ningun clip valido")

    video_base = concatenate_videoclips(clips_finales, method="compose")
    video_base = video_base.set_audio(audio)
    video_base = video_base.set_duration(duracion_total)

    # Subtitulos cinematograficos
    subtitulos = []
    for seg in segmentos:
        txt = TextClip(
            seg["text"].strip(), fontsize=46, color="white",
            font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
            size=(RESOLUCION[0]-160, None), method="caption"
        ).set_start(seg["start"]).set_end(seg["end"]).set_position(("center", 0.82), relative=True)
        subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)
    final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac")
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
    print(f"Nicho elegido: {nicho}")

    contenido = generar_contenido(nicho)
    print(f"Personaje: {contenido['personaje']['nombre']}")
    print(f"Lugar: {contenido['lugar']['nombre']}")
    palabras = len(contenido['guion'].split())
    print(f"Guion generado: {palabras} palabras")

    imagenes_ia = generar_imagenes(contenido)
    print(f"Imagenes IA generadas: {len(imagenes_ia)}")

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    clips = descargar_clips(nicho)
    print(f"Clips Pexels: {len(clips)}")

    video_path = armar_video(clips, imagenes_ia, audio_path, segmentos)

    titulo = contenido.get("titulo", "The Story Nobody Told You 😱")
    descripcion_base = contenido.get("descripcion_video", "")
    descripcion = f"{descripcion_base}\n\n{contenido['guion'][:300]}...\n\n#{nicho.replace('_', '')} #documentary"
    tags = contenido.get("tags", [nicho, "documentary", "viral", "facts"])
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
