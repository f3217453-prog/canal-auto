"""
Pipeline Long-Form Videos - Version 1.0

Videos de 5-10 minutos para horror y top10 dark/mystery.
Diferencias clave respecto a los Shorts:
- Guion de 1200-1500 palabras (~8-10 minutos narrados)
- Estructura multi-acto (5 actos para horror, intro+10+cierre para top10)
- 150-200+ clips descargados para cubrir la duracion sin repeticion visible
- Resolucion horizontal 1920x1080 (YouTube recomienda landscape para videos largos)
- Render con preset="fast" para no superar el timeout de 120 min del workflow
- Capitulos en la descripcion (YouTube los detecta automaticamente)
- Thumbnail generado como imagen separada (1280x720)
- Whisper "small" para mayor precision en transcripcion larga
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
# Videos largos van en landscape (1920x1080), no vertical
RESOLUCION = (1920, 1080)
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

NEGATIVE_PROMPT = (
    "deformed hands, extra fingers, mutated, blurry, watermark, text, "
    "logo, disfigured face, low quality, low resolution, duplicate"
)

MUSICA_HORROR = [
    "https://cdn.pixabay.com/download/audio/2022/03/10/audio_270f4b1fbe.mp3",
    "https://cdn.pixabay.com/download/audio/2021/09/06/audio_dad6b6ef7f.mp3",
]

TEMAS_TOP10_LONGFORM = [
    "most disturbing unsolved mysteries in human history",
    "scariest places on Earth that scientists cannot explain",
    "most chilling true crime cases that shocked the world",
    "darkest government secrets that were finally revealed",
    "most terrifying paranormal events ever documented",
    "most disturbing things ever found in abandoned places",
    "scariest deep sea discoveries that changed everything",
    "most chilling last words of people who disappeared",
    "most disturbing ancient rituals ever documented",
    "darkest moments in history that textbooks don't teach",
]

CONSULTAS_BROLL_HORROR = [
    "dark forest fog night cinematic", "abandoned house interior dark",
    "candle flame dark room horror", "foggy graveyard night cinematic",
    "flashlight dark hallway", "misty woods path night",
    "dark attic old house", "shadow silhouette dark hallway",
    "thunderstorm dramatic night", "creepy mansion exterior night",
    "dark basement horror cinematic", "empty hallway flickering light",
    "broken mirror dark room", "rain window night horror",
    "old door creaking dark", "dark staircase horror",
    "forest path night fog", "abandoned corridor dark",
    "candlelight flickering shadows", "dark lake night fog",
]

CONSULTAS_BROLL_TOP10 = [
    "dark mysterious location cinematic", "abandoned place horror",
    "dark forest fog cinematic", "old ruins night dramatic",
    "shadowy figure silhouette", "dramatic sky dark clouds",
    "creepy empty hallway", "dark water reflection night",
    "fog misty landscape night", "dramatic cliff edge ocean",
    "old cemetery night cinematic", "thunderstorm dramatic sky",
    "underwater dark ocean depth", "ancient ruins dark dramatic",
    "dramatic mountain storm", "government building night",
    "crime scene dark dramatic", "police lights night fog",
    "dark cave entrance", "deep ocean creatures darkness",
]

CONSULTAS_RESPALDO = [
    "cinematic dark background", "abstract dark texture",
    "smoke slow motion dark", "dramatic sky dark clouds",
    "particles floating dark", "light rays dark room",
    "cinematic nature landscape dark", "fog atmospheric cinematic",
]

# ---------- PROMPTS ----------

PROMPT_HORROR_LONGFORM = """You are a professional horror narrator for YouTube, 
similar to channels like Nexpo, Barely Sociable, or Night Mind.
Your videos are 8-10 minutes long and deeply atmospheric.

Create a full horror narrative script with this structure:
- ACT 1 - THE HOOK (150 words): Open mid-action or with the most disturbing detail. 
  Establish character and location vividly. Create immediate dread.
- ACT 2 - BUILDING DREAD (300 words): Develop the atmosphere. Strange events begin. 
  The character investigates. First signs something is deeply wrong.
- ACT 3 - ESCALATION (300 words): Things get worse. The horror reveals itself gradually. 
  Tension peaks. The character is in real danger.
- ACT 4 - THE CLIMAX (250 words): The full horror is revealed. The most disturbing moment. 
  A shocking twist or revelation.
- ACT 5 - THE AFTERMATH (200 words): Chilling resolution. Something is left unanswered. 
  A final line that haunts the viewer.

Character: Give them a specific name, age, appearance, and personality.
Location: Specific, detailed, atmospheric. Not generic.
Total: 1200-1500 words STRICT. Write EVERYTHING in ENGLISH ONLY.

Also provide:
- 8 scene descriptions for AI image generation (filmable, 5-8 words each, spread across all 5 acts)
- A devastating hook line (under 10 words, creates immediate dread)
- Chapter timestamps in this exact format (adjust times based on word count):
  0:00 The Beginning
  2:30 Something Is Wrong
  5:00 It Gets Worse
  7:00 The Truth
  9:00 What Happened After

TITLE RULES:
- Specific detail or number ("The House on Miller Road", "3 Days in Room 12")
- Power word: haunted / cursed / forbidden / disappeared / survived
- Emoji at end: 😱 or 👁️ or ☠️
- Do NOT add hashtags to the title (this is a long-form video, not a Short)

Return ONLY valid JSON, no markdown, no backticks:
{
"personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
"lugar": {"nombre": "...", "descripcion": "..."},
"hook": "...(under 10 words)...",
"actos": {
  "act1": "...(150 words)...",
  "act2": "...(300 words)...",
  "act3": "...(300 words)...",
  "act4": "...(250 words)...",
  "act5": "...(200 words)..."
},
"guion": "...(full script 1200-1500 words, all 5 acts concatenated)...",
"escenas": ["scene 1", "scene 2", "scene 3", "scene 4", "scene 5", "scene 6", "scene 7", "scene 8"],
"capitulos": "0:00 The Beginning\\n2:30 Something Is Wrong\\n5:00 It Gets Worse\\n7:00 The Truth\\n9:00 What Happened After",
"titulo": "...(specific horror title with power word + emoji, NO hashtags)...",
"tags": ["horror", "scary", "creepypasta", "horrorstory", "scarystories", "paranormal", "horrornarrative", "scaryvideo", "horrorfan", "truescaryhorror"]
}"""

PROMPT_TOP10_LONGFORM = """You are a viral YouTube documentary narrator like Top 5s or Dark5.
Your videos are 8-10 minutes long. You cover dark mysteries, disturbing history, and unexplained events.

Create a full top 10 countdown script about: {tema}

Structure:
- INTRO (100 words): Hook the viewer immediately. Tease the most disturbing entry (#1). 
  Tell them to stay until the end.
- ENTRIES 10 through 1 (100 words each = 1000 words total): 
  Each entry fully developed with specific details, historical context, and disturbing facts.
  Build tension progressively — each entry more disturbing than the last.
  At entry #5, tease #1 again ("but nothing on this list compares to what's coming...").
  Entry #1 must be the most shocking, specific, and well-developed.
- OUTRO (100 words): Reflect on what was covered. Leave viewers with a disturbing final thought. 
  Ask them to comment which entry disturbed them most (drives engagement).

Total: 1200-1500 words STRICT. Write EVERYTHING in ENGLISH ONLY.

Also provide:
- 8 scene descriptions for AI image generation (spread across intro, entries 10/8/5/3/1, outro)
- A hook line (under 10 words, creates morbid curiosity)
- Chapter timestamps:
  0:00 Introduction
  1:00 #10
  2:00 #9
  3:00 #8
  4:00 #7
  5:00 #6
  6:00 #5 (The Turning Point)
  7:00 #4 and #3
  8:00 #2
  9:00 #1 (The Most Disturbing)

TITLE RULES:
- Start with "Top 10"
- Dramatic descriptor + power word: disturbing / classified / forbidden / never explained / cursed
- Emoji: 😱 or 👁️ or ☠️
- Do NOT add hashtags (long-form video, not a Short)

Return ONLY valid JSON, no markdown, no backticks:
{{
"tema": "...",
"hook": "...(under 10 words)...",
"guion": "...(full script 1200-1500 words)...",
"escenas": ["scene 1", "scene 2", "scene 3", "scene 4", "scene 5", "scene 6", "scene 7", "scene 8"],
"capitulos": "0:00 Introduction\\n1:00 #10\\n2:00 #9\\n3:00 #8\\n4:00 #7\\n5:00 #6\\n6:00 #5 (The Turning Point)\\n7:00 #4 and #3\\n8:00 #2\\n9:00 #1 (The Most Disturbing)",
"titulo": "...(Top 10 title with power word + emoji, NO hashtags)...",
"tags": ["top10", "scary", "horror", "mystery", "disturbing", "paranormal", "scaryfacts", "darkhistory", "truecrime", "unexplained"]
}}"""


# ---------- GENERACION DE CONTENIDO ----------

def generar_contenido_horror() -> dict:
    body = {
        "contents": [{"parts": [{"text": PROMPT_HORROR_LONGFORM}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 8192}
    }
    for modelo in MODELOS_GEMINI:
        for intento in range(3):
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={GEMINI_API_KEY}"
                )
                r = requests.post(url, json=body, timeout=90)
                if r.status_code in (503, 429):
                    print(f"{r.status_code} en {modelo}, intento {intento+1}/3, esperando 20s...")
                    time.sleep(20)
                    continue
                r.raise_for_status()
                data = r.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r"```json|```", "", texto).strip()
                contenido = json.loads(texto)
                palabras = len(contenido.get("guion", "").split())
                print(f"Horror longform: {palabras} palabras")
                return contenido
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


def generar_contenido_top10() -> dict:
    tema = random.choice(TEMAS_TOP10_LONGFORM)
    prompt = PROMPT_TOP10_LONGFORM.format(tema=tema)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.95, "maxOutputTokens": 8192}
    }
    for modelo in MODELOS_GEMINI:
        for intento in range(3):
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={GEMINI_API_KEY}"
                )
                r = requests.post(url, json=body, timeout=90)
                if r.status_code in (503, 429):
                    print(f"{r.status_code} en {modelo}, intento {intento+1}/3, esperando 20s...")
                    time.sleep(20)
                    continue
                r.raise_for_status()
                data = r.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r"```json|```", "", texto).strip()
                contenido = json.loads(texto)
                palabras = len(contenido.get("guion", "").split())
                print(f"Top10 longform ({tema}): {palabras} palabras")
                return contenido
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


# ---------- IMAGENES IA ----------

def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_longform") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": (
            f"cinematic film still, 35mm, dramatic lighting, high quality, 4k: {prompt}"
        ),
        "parameters": {
            # Landscape para video largo
            "width": 1344,
            "height": 768,
            "negative_prompt": NEGATIVE_PROMPT,
        }
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
        print(f"Imagen IA {indice}: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso imagen IA {indice}: {e}")
        return None


def generar_imagenes(escenas: list, descripcion_personaje: str = "") -> list:
    rutas = []
    for i, escena in enumerate(escenas[:8]):
        prompt = escena
        if descripcion_personaje and i < 3:
            prompt = (
                f"{escena}, featuring {descripcion_personaje}, "
                "consistent character design, cinematic quality"
            )
        ruta = generar_imagen_ia(prompt, i)
        if ruta:
            rutas.append(ruta)
    return rutas


# ---------- AUDIO ----------

async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio_longform.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    # "small" para mayor precision en narraciones largas
    modelo = whisper.load_model("small")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


# ---------- CLIPS ----------

def _buscar_clips(consulta: str, headers: dict, carpeta: str,
                   indice_inicial: int, por_consulta: int = 15):
    rutas = []
    indice_global = indice_inicial
    url = f"https://api.pexels.com/videos/search?query={consulta}&per_page={por_consulta}"
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Aviso busqueda '{consulta}': {e}")
        return rutas, indice_global

    videos = r.json().get("videos", [])
    for v in videos:
        archivos = sorted(v["video_files"], key=lambda f: f.get("width", 0))
        if not archivos:
            continue
        # Para video largo, preferir calidad mas alta
        enlace = archivos[-1]["link"] if archivos else archivos[0]["link"]
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


def descargar_clips(escenas: list, nicho: str, carpeta: str = "clips_longform"):
    """Descarga 150-200+ clips para cubrir 8-10 minutos sin repeticion visible."""
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    indice = 0

    consultas_nicho = (
        CONSULTAS_BROLL_HORROR if nicho == "horror" else CONSULTAS_BROLL_TOP10
    )

    # Clips por escena narrativa (8 escenas x 15 clips = 120 clips base)
    clips_por_escena = []
    for escena in escenas:
        rutas, indice = _buscar_clips(escena, headers, carpeta, indice, por_consulta=15)
        clips_por_escena.append(rutas)

    # Pool generico del nicho (20 consultas x 15 clips = 300 clips potenciales)
    pool_generico = []
    for consulta in consultas_nicho:
        rutas, indice = _buscar_clips(consulta, headers, carpeta, indice, por_consulta=15)
        pool_generico.extend(rutas)

    total = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    print(f"Total clips descargados: {total}")

    # Si hay menos de 80 clips, descarga respaldos
    if total < 80:
        print(f"Solo {total} clips, descargando respaldos...")
        for consulta in CONSULTAS_RESPALDO:
            extra, indice = _buscar_clips(consulta, headers, carpeta, indice, por_consulta=15)
            pool_generico.extend(extra)

    total_final = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    print(f"Total clips final: {total_final}")
    return clips_por_escena, pool_generico


# ---------- ARMADO DE VIDEO ----------

def _preparar_clip(ruta: str, dur_max: float):
    try:
        c = VideoFileClip(ruta).without_audio()
    except Exception:
        return None
    if c.duration < 0.5:
        c.close()
        return None
    escala = max(RESOLUCION[0] / c.w, RESOLUCION[1] / c.h)
    c = c.resize(escala)
    c = c.crop(x_center=c.w/2, y_center=c.h/2,
               width=RESOLUCION[0], height=RESOLUCION[1])
    # Clips mas largos para video largo (3-7s en vez de 2-4s)
    dur_clip = min(c.duration, dur_max, random.uniform(3.0, 7.0))
    if dur_clip <= 0:
        c.close()
        return None
    return c.subclip(0, dur_clip)


def _rellenar_con_pool(clips_finales, tiempo_acumulado, limite, pool):
    """Rota el pool sin limite para garantizar que no haya huecos."""
    if not pool:
        return tiempo_acumulado
    max_intentos = len(pool) * 4
    intentos = 0
    pool_idx = 0
    pool_shuffled = list(pool)
    random.shuffle(pool_shuffled)

    while tiempo_acumulado < limite and intentos < max_intentos:
        ruta = pool_shuffled[pool_idx % len(pool_shuffled)]
        pool_idx += 1
        intentos += 1
        restante = limite - tiempo_acumulado
        c = _preparar_clip(ruta, restante)
        if c is None:
            continue
        clips_finales.append(c)
        tiempo_acumulado += c.duration

    return tiempo_acumulado


def armar_video(clips_por_escena, pool_generico, imagenes_ia, audio_path,
                 segmentos, nicho, hook_texto, musica_path,
                 salida="video_longform.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    print(f"Duracion de audio: {duracion_total:.1f}s ({duracion_total/60:.1f} min)")

    n_escenas = max(len(clips_por_escena), 1)
    dur_por_escena = duracion_total / n_escenas

    clips_finales = []
    tiempo_acumulado = 0.0

    for i in range(n_escenas):
        limite_tramo = (i + 1) * dur_por_escena
        clips_escena = list(clips_por_escena[i]) if i < len(clips_por_escena) else []
        random.shuffle(clips_escena)

        # Imagen IA al inicio de cada tramo
        if i < len(imagenes_ia) and imagenes_ia:
            try:
                dur = min(4.0, limite_tramo - tiempo_acumulado)
                if dur > 0.1:
                    c = ImageClip(imagenes_ia[i]).set_duration(dur)
                    clips_finales.append(c)
                    tiempo_acumulado += dur
            except Exception as e:
                print(f"Aviso imagen {i}: {e}")

        # Clips especificos de la escena
        puntero = 0
        while tiempo_acumulado < limite_tramo and puntero < len(clips_escena):
            restante = limite_tramo - tiempo_acumulado
            c = _preparar_clip(clips_escena[puntero], restante)
            puntero += 1
            if c is None:
                continue
            clips_finales.append(c)
            tiempo_acumulado += c.duration

        # Relleno con pool generico rotando
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, limite_tramo, pool_generico
        )

        # Si aun queda hueco, reutiliza clips de escena
        if tiempo_acumulado < limite_tramo - 0.1 and clips_escena:
            random.shuffle(clips_escena)
            tiempo_acumulado = _rellenar_con_pool(
                clips_finales, tiempo_acumulado, limite_tramo, clips_escena
            )

        # Ultimo recurso: imagen IA estatica en vez de negro
        if tiempo_acumulado < limite_tramo - 0.1 and imagenes_ia:
            hueco = limite_tramo - tiempo_acumulado
            try:
                c = ImageClip(imagenes_ia[i % len(imagenes_ia)]).set_duration(hueco)
                clips_finales.append(c)
                tiempo_acumulado += hueco
            except Exception as e:
                print(f"Aviso imagen emergencia {i}: {e}")

    # Tiempo restante tras el ultimo tramo
    if tiempo_acumulado < duracion_total - 0.1:
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, duracion_total, pool_generico
        )

    # Ultimo recurso final
    if tiempo_acumulado < duracion_total - 0.1 and imagenes_ia:
        hueco = duracion_total - tiempo_acumulado
        try:
            c = ImageClip(imagenes_ia[0]).set_duration(hueco)
            clips_finales.append(c)
        except Exception as e:
            print(f"Aviso imagen final: {e}")

    if not clips_finales:
        raise RuntimeError("No se pudo armar ningun clip")

    video_base = concatenate_videoclips(clips_finales, method="compose")
    video_base = video_base.set_duration(duracion_total)

    # Audio
    audios = [audio_voz]
    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            if musica.duration < duracion_total:
                import math
                loops = math.ceil(duracion_total / musica.duration)
                musica = concatenate_audioclips([musica] * loops)
            musica = musica.subclip(0, duracion_total).volumex(0.10)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica fondo: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)

    # Subtitulos estilo viral para video largo
    # Menos frecuentes que en Shorts para no saturar la pantalla
    subtitulos = []
    color_sub = "#FF4444" if nicho == "horror" else "#FFD700"

    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        duracion_seg = seg["end"] - seg["start"]
        dur_palabra = duracion_seg / max(len(palabras), 1)

        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + (j * dur_palabra)
            t_fin = t_inicio + dur_palabra

            color_palabra = "white"
            if nicho == "top10":
                es_numero = any(
                    n in palabra for n in ["10","9","8","7","6","5","4","3","2","1"]
                )
                if es_numero:
                    color_palabra = "#FFD700"

            sombra = TextClip(
                palabra.upper(), fontsize=70, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 2, int(RESOLUCION[1] * 0.85) + 2), True
            )
            txt = TextClip(
                palabra.upper(), fontsize=70, color=color_palabra,
                font="DejaVu-Sans-Bold", stroke_color=color_sub, stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.85), relative=True
            )
            subtitulos.append(sombra)
            subtitulos.append(txt)

    # Hook superpuesto sobre el video en los primeros 3 segundos
    hook_txt = TextClip(
        hook_texto.upper(),
        fontsize=55, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=3,
        size=(RESOLUCION[0]-160, None), method="caption"
    ).set_start(0).set_end(min(3.0, duracion_total)).set_position(
        ("center", 0.35), relative=True
    )
    subtitulos.append(hook_txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)

    # preset="fast" para no superar el timeout de 120 min del workflow
    final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=4, preset="fast", bitrate="6000k",
    )
    return salida


# ---------- SUBIDA A YOUTUBE ----------

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


# ---------- MAIN ----------

def main():
    # Alterna entre horror y top10 cada dia para dar variedad al canal
    nicho = random.choice(["horror", "top10"])
    print(f"Pipeline longform: {nicho}")

    if nicho == "horror":
        contenido = generar_contenido_horror()
        descripcion_personaje = (
            f"{contenido['personaje']['nombre']}, "
            f"{contenido['personaje']['descripcion']}"
        )
        consultas_musica = MUSICA_HORROR
        HASHTAGS_FIJOS = [
            "#horror", "#scarystories", "#horrorstory", "#creepypasta",
            "#paranormal", "#scaryvideo", "#horrorfan", "#truescaryhorror",
            "#horrornarrative", "#darkstories",
        ]
        tags_base = [
            "horror", "scary", "creepypasta", "horrorstory", "scarystories",
            "paranormal", "horrornarrative", "scaryvideo", "horrorfan",
            "truescaryhorror", "darkstories", "horrorcommunity",
        ]
    else:
        contenido = generar_contenido_top10()
        descripcion_personaje = ""
        consultas_musica = MUSICA_HORROR  # misma musica oscura
        HASHTAGS_FIJOS = [
            "#top10", "#scary", "#mystery", "#disturbing", "#paranormal",
            "#scaryfacts", "#darkhistory", "#truecrime", "#unexplained", "#horror",
        ]
        tags_base = [
            "top10", "scary", "horror", "mystery", "disturbing", "paranormal",
            "scaryfacts", "darkhistory", "truecrime", "unexplained",
            "darkfacts", "horrorfacts",
        ]

    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes(escenas, descripcion_personaje)

    musica_url = random.choice(consultas_musica)
    musica_path = "musica_longform.mp3"
    try:
        r = requests.get(musica_url, timeout=30, stream=True)
        r.raise_for_status()
        with open(musica_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"Aviso musica: {e}")
        musica_path = None

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    clips_por_escena, pool_generico = descargar_clips(escenas, nicho)

    hook_texto = contenido.get("hook", "What happened here was never explained.")

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia,
        audio_path, segmentos, nicho, hook_texto, musica_path
    )

    titulo = contenido.get("titulo", "The Story Nobody Survived To Tell 😱")
    capitulos = contenido.get("capitulos", "")
    tags_gemini = contenido.get("tags", tags_base)
    tags_completos = list(dict.fromkeys(tags_gemini + tags_base))

    hashtags_desc = " ".join(HASHTAGS_FIJOS)
    descripcion = (
        f"{contenido['guion'][:800]}...\n\n"
        f"⚠️ Watch until the end.\n\n"
        f"--- CHAPTERS ---\n{capitulos}\n\n"
        f"{hashtags_desc}"
    )

    subir_youtube(video_path, titulo, descripcion, tags_completos)


if __name__ == "__main__":
    main()
