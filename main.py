"""
Pipeline mejorado para Shorts con:
- Guiones cinematográficos con personajes, lugares y estructura narrativa real
- Imágenes de personajes y escenas generadas por IA (FLUX.1 via Hugging Face, gratis)
- Sin pantalla negra garantizado
- Pool grande de clips variados sin repetición
"""

import os
import io
import random
import textwrap
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

# ------------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------------
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

VOZ = "en-US-GuyNeural"
RESOLUCION = (1080, 1920)
HF_MODEL = "black-forest-labs/FLUX.1-schnell"

# ------------------------------------------------------------------
# NICHOS
# ------------------------------------------------------------------
NICHOS = {
    "horror": {
        "prompt_sistema": """You are a professional horror screenwriter. 
Create a short horror story script with:
1. A main character (give them a name, age, physical description, personality)
2. A specific terrifying location (describe it in detail)
3. A clear narrative arc: eerie opening, building dread, shocking climax, chilling ending
4. 3 vivid scene descriptions for AI image generation (each scene described in one sentence)

Return ONLY valid JSON in this exact format:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(55 second narration script)...",
  "escenas": ["scene 1 description", "scene 2 description", "scene 3 description"],
  "titulo": "...(YouTube title with emoji)...",
  "tags": ["tag1", "tag2", "tag3", "tag4"]
}""",
        "consultas_broll": [
            "dark forest fog night", "abandoned house interior",
            "candle flame dark room", "foggy graveyard night",
            "old door creaking dark", "flashlight dark room",
            "misty woods path night", "dark attic old house",
        ],
    },
    "true_crime": {
        "prompt_sistema": """You are a professional true crime documentary writer.
Create a gripping true crime story script with:
1. A composite fictional investigator character (name, description, role)
2. A specific fictional location where events took place
3. Clear narrative: cold open hook, investigation, twist, unresolved ending
4. 3 vivid atmospheric scene descriptions for AI image generation

Return ONLY valid JSON in this exact format:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(55 second narration script)...",
  "escenas": ["scene 1 description", "scene 2 description", "scene 3 description"],
  "titulo": "...(YouTube title with emoji)...",
  "tags": ["tag1", "tag2", "tag3", "tag4"]
}""",
        "consultas_broll": [
            "dark street night fog", "police lights night city",
            "old detective office", "rain window night moody",
            "empty road night headlights", "newspaper archive old",
            "typewriter old paper", "courthouse exterior night",
        ],
    },
    "world_records": {
        "prompt_sistema": """You are an exciting documentary narrator specializing in world records.
Create a world record script with:
1. A real or composite record holder (fictional name, description)
2. The specific location where the record was set
3. Exciting narrative with vivid numbers and comparisons
4. 3 dramatic scene descriptions for AI image generation

Return ONLY valid JSON in this exact format:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(55 second narration script)...",
  "escenas": ["scene 1 description", "scene 2 description", "scene 3 description"],
  "titulo": "...(YouTube title with emoji)...",
  "tags": ["tag1", "tag2", "tag3", "tag4"]
}""",
        "consultas_broll": [
            "stadium crowd aerial", "extreme sports action",
            "mountain climbing extreme", "ocean waves aerial",
            "athlete slow motion", "fireworks night sky",
            "skydiving aerial", "olympic stadium crowd",
        ],
    },
    "top10": {
        "prompt_sistema": """You are a captivating documentary narrator for top 10 countdowns.
Create a top 10 countdown script with:
1. A fictional narrator character (name, description)
2. A dramatic setting for the countdown
3. Fast-paced punchy narration building to the most shocking entry
4. 3 vivid scene descriptions for AI image generation

Return ONLY valid JSON in this exact format:
{
  "personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
  "lugar": {"nombre": "...", "descripcion": "..."},
  "guion": "...(55 second narration script)...",
  "escenas": ["scene 1 description", "scene 2 description", "scene 3 description"],
  "titulo": "...(YouTube title with emoji)...",
  "tags": ["tag1", "tag2", "tag3", "tag4"]
}""",
        "consultas_broll": [
            "nature landscape aerial", "city skyline timelapse",
            "ocean underwater", "desert landscape aerial",
            "mountain range aerial", "wildlife animals",
            "space stars night sky", "waterfall nature",
        ],
    },
}

CONSULTAS_RESPALDO = [
    "cinematic dark background", "abstract dark texture",
    "smoke slow motion dark", "clouds timelapse dark",
    "light rays dark room", "particles floating dark",
]


# ------------------------------------------------------------------
# 1. GENERAR GUION CINEMATOGRÁFICO CON GEMINI
# ------------------------------------------------------------------
def generar_contenido(nicho: str) -> dict:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt_sistema = NICHOS[nicho]["prompt_sistema"]
    body = {
        "contents": [{"parts": [{"text": prompt_sistema}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1500}
    }
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Limpiar posibles backticks de markdown que Gemini a veces añade
    texto = texto.replace("```json", "").replace("```", "").strip()

    try:
        contenido = json.loads(texto)
    except json.JSONDecodeError:
        # Si falla el JSON, devolver estructura mínima funcional
        contenido = {
            "personaje": {"nombre": "Unknown", "descripcion": "mysterious figure", "personalidad": "enigmatic"},
            "lugar": {"nombre": "Unknown Location", "descripcion": "a dark and mysterious place"},
            "guion": texto[:500],
            "escenas": ["dark mysterious scene", "tense atmospheric moment", "chilling final scene"],
            "titulo": "You Won't Believe This 😱",
            "tags": [nicho, "shorts", "viral", "mystery"]
        }
    return contenido


# ------------------------------------------------------------------
# 2. GENERAR IMÁGENES CON IA (FLUX.1 via Hugging Face, gratis)
# ------------------------------------------------------------------
def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_ia") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"cinematic, dramatic lighting, high quality, detailed: {prompt}",
        "parameters": {"width": 768, "height": 1344}  # proporcional a 1080x1920
    }

    try:
        r = requests.post(
            f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=60
        )
        r.raise_for_status()
        imagen = Image.open(io.BytesIO(r.content))
        imagen = imagen.resize(RESOLUCION, Image.LANCZOS)
        imagen.save(destino)
        print(f"Imagen IA generada: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso: no se pudo generar imagen IA ({e}), se usará clip de Pexels en su lugar")
        return None


def generar_imagenes_personaje(contenido: dict, carpeta: str = "imagenes_ia") -> list:
    rutas = []
    personaje = contenido.get("personaje", {})
    lugar = contenido.get("lugar", {})
    escenas = contenido.get("escenas", [])

    # Imagen del personaje principal
    prompt_personaje = (
        f"Portrait of {personaje.get('nombre', 'a mysterious person')}, "
        f"{personaje.get('descripcion', 'dramatic figure')}, "
        f"in {lugar.get('nombre', 'dramatic setting')}, "
        "cinematic lighting, dramatic, high quality, film noir style"
    )
    ruta = generar_imagen_ia(prompt_personaje, 0, carpeta)
    if ruta:
        rutas.append(ruta)

    # Imágenes de cada escena
    for i, escena in enumerate(escenas[:3]):
        prompt_escena = (
            f"{escena}, in {lugar.get('descripcion', 'dramatic setting')}, "
            "cinematic, dramatic lighting, atmospheric, high quality"
        )
        ruta = generar_imagen_ia(prompt_escena, i + 1, carpeta)
        if ruta:
            rutas.append(ruta)

    return rutas


# ------------------------------------------------------------------
# 3. GUION -> AUDIO
# ------------------------------------------------------------------
async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


# ------------------------------------------------------------------
# 4. AUDIO -> SUBTÍTULOS
# ------------------------------------------------------------------
def transcribir(audio_path: str):
    modelo = whisper.load_model("tiny")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


# ------------------------------------------------------------------
# 5. DESCARGAR CLIPS DE PEXELS (pool grande, sin repetición)
# ------------------------------------------------------------------
def _descargar_desde_consultas(consultas, headers, carpeta, indice_inicial, por_consulta=5):
    rutas = []
    indice_global = indice_inicial
    for consulta in consultas:
        url = f"https://api.pexels.com/videos/search?query={consulta}&per_page={por_consulta}"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"Aviso: falló búsqueda '{consulta}': {e}")
            continue
        videos = r.json().get("videos", [])
        print(f"Búsqueda '{consulta}': {len(videos)} resultados")
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
                print(f"Aviso: falló descarga clip: {e}")
                continue
    return rutas, indice_global


def descargar_clips(nicho: str, carpeta: str = "clips"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = NICHOS[nicho]["consultas_broll"]
    rutas, siguiente = _descargar_desde_consultas(consultas, headers, carpeta, 0)
    if len(rutas) < 15:
        print(f"Solo {len(rutas)} clips, completando con respaldo...")
        extra, siguiente = _descargar_desde_consultas(CONSULTAS_RESPALDO, headers, carpeta, siguiente)
        rutas.extend(extra)
    print(f"Total clips Pexels: {len(rutas)}")
    return rutas


# ------------------------------------------------------------------
# 6. ARMAR EL VIDEO (imágenes IA + clips Pexels, sin negros, sin repetición)
# ------------------------------------------------------------------
def imagen_a_clip(ruta_imagen: str, duracion: float) -> ImageClip:
    img = Image.open(ruta_imagen).resize(RESOLUCION, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    clip = ImageClip(ruta_imagen).set_duration(duracion)
    return clip


def armar_video(clips_pexels, imagenes_ia, audio_path, segmentos, salida="video_final.mp4"):
    audio = AudioFileClip(audio_path)
    duracion_total = audio.duration

    # Mezclar imágenes IA con clips de Pexels de forma intercalada
    # Las imágenes IA aparecen al inicio (presentando personaje/lugar) y en momentos clave
    clips_finales = []
    tiempo_acumulado = 0

    # Pool de clips Pexels barajado
    pool_pexels = clips_pexels.copy()
    random.shuffle(pool_pexels)
    puntero_pexels = 0
    ultimo_pexels = None

    # Insertar imágenes IA primero (3-4 segundos cada una)
    duracion_imagen = 3.5
    for ruta_img in imagenes_ia:
        if tiempo_acumulado >= duracion_total:
            break
        try:
            c = ImageClip(ruta_img).set_duration(
                min(duracion_imagen, duracion_total - tiempo_acumulado)
            )
            clips_finales.append(c)
            tiempo_acumulado += c.duration
        except Exception as e:
            print(f"Aviso: falló imagen IA {ruta_img}: {e}")
            continue

    # Rellenar el resto con clips de Pexels
    while tiempo_acumulado < duracion_total:
        if puntero_pexels >= len(pool_pexels):
            random.shuffle(pool_pexels)
            if pool_pexels[0] == ultimo_pexels and len(pool_pexels) > 1:
                pool_pexels[0], pool_pexels[1] = pool_pexels[1], pool_pexels[0]
            puntero_pexels = 0

        ruta = pool_pexels[puntero_pexels]
        puntero_pexels += 1

        try:
            c = VideoFileClip(ruta).without_audio()
        except Exception:
            continue

        if c.duration < 0.5:
            c.close()
            continue

        # Escalar para cubrir TODO el frame sin dejar negro
        escala = max(RESOLUCION[0] / c.w, RESOLUCION[1] / c.h)
        c = c.resize(escala)
        c = c.crop(
            x_center=c.w / 2, y_center=c.h / 2,
            width=RESOLUCION[0], height=RESOLUCION[1]
        )

        restante = duracion_total - tiempo_acumulado
        duracion_clip = min(c.duration, restante, random.uniform(2.5, 5.0))
        if duracion_clip <= 0:
            c.close()
            continue

        c = c.subclip(0, duracion_clip)
        clips_finales.append(c)
        tiempo_acumulado += duracion_clip
        ultimo_pexels = ruta

    if not clips_finales:
        raise RuntimeError("No se pudo armar ningún clip válido")

    video_base = concatenate_videoclips(clips_finales, method="compose")
    video_base = video_base.set_audio(audio)
    video_base = video_base.set_duration(duracion_total)

    # Subtítulos cinematográficos
    subtitulos = []
    for seg in segmentos:
        txt = TextClip(
            seg["text"].strip(), fontsize=58, color="white",
            font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=3,
            size=(RESOLUCION[0]-80, None), method="caption"
        ).set_start(seg["start"]).set_end(seg["end"]).set_position(("center", 0.75), relative=True)
        subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)
    final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac")
    return salida


# ------------------------------------------------------------------
# 7. SUBIR A YOUTUBE
# ------------------------------------------------------------------
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
            "title": titulo,
            "description": descripcion,
            "tags": tags,
            "categoryId": "24",
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
    nicho = random.choice(list(NICHOS.keys()))
    print(f"Nicho elegido: {nicho}")

    # 1. Generar contenido cinematográfico (guion + personajes + escenas)
    contenido = generar_contenido(nicho)
    print(f"Personaje: {contenido['personaje']['nombre']}")
    print(f"Lugar: {contenido['lugar']['nombre']}")
    print(f"Guion:\n{contenido['guion']}")

    # 2. Generar imágenes con IA (personaje + escenas)
    imagenes_ia = generar_imagenes_personaje(contenido)
    print(f"Imágenes IA generadas: {len(imagenes_ia)}")

    # 3. Audio
    audio_path = generar_audio(contenido["guion"])

    # 4. Subtítulos
    segmentos = transcribir(audio_path)

    # 5. Clips de Pexels
    clips = descargar_clips(nicho)
    print(f"Clips Pexels: {len(clips)}")

    # 6. Armar video
    video_path = armar_video(clips, imagenes_ia, audio_path, segmentos)

    # 7. Subir
    titulo = contenido.get("titulo", "You Won't Believe This 😱")
    descripcion = f"{contenido['guion']}\n\n#{nicho.replace('_', '')} #shorts"
    tags = contenido.get("tags", [nicho, "shorts", "viral"])
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
