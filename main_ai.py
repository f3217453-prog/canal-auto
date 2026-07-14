"""
Pipeline para canal de IA y tecnologia - Version 1.0
Contenido: noticias de IA, herramientas, comparativas, tutoriales
Formato: vertical 1080x1920 (TikTok/Reels/Shorts)
Guiones virales nivel MrBeast/MKBHD del mundo tech
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
RESOLUCION = (1080, 1920)
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

MUSICA_AMBIENTE = [
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_5bbc9a1a1c.mp3",
]

TEMAS_AI = [
    {
        "tema": "ChatGPT vs Claude vs Gemini - which AI is actually better in 2025",
        "angulo": "comparison battle format, each AI has a personality, dramatic reveal of winner",
        "color": "#00BFFF",
        "tags": ["chatgpt", "claude", "gemini", "aitools", "artificialintelligence"],
    },
    {
        "tema": "5 AI tools that will replace your entire workflow in 2025",
        "angulo": "list format, each tool more shocking than the last, emphasis on time saved and money made",
        "color": "#00FF88",
        "tags": ["aitools", "productivity", "automation", "artificialintelligence", "tech"],
    },
    {
        "tema": "How to make $500 per day using free AI tools",
        "angulo": "step by step method, specific tools named, realistic but exciting income claims",
        "color": "#FFD700",
        "tags": ["makemoneyonline", "aitools", "passiveincome", "artificialintelligence"],
    },
    {
        "tema": "This AI tool just made Photoshop completely obsolete",
        "angulo": "before and after comparison, dramatic claims backed by specific features, call to action",
        "color": "#FF4444",
        "tags": ["aitools", "photoshop", "design", "artificialintelligence", "tech"],
    },
    {
        "tema": "OpenAI just dropped something that changes everything",
        "angulo": "breaking news style, build anticipation, specific feature reveals, implications",
        "color": "#00BFFF",
        "tags": ["openai", "chatgpt", "aitools", "technews", "artificialintelligence"],
    },
    {
        "tema": "The AI tool that writes better than most humans",
        "angulo": "show specific examples, compare outputs, reveal surprising capabilities",
        "color": "#FF8C00",
        "tags": ["aiwriting", "aitools", "contentcreation", "artificialintelligence"],
    },
    {
        "tema": "5 things AI can do right now that will shock you",
        "angulo": "each fact more unbelievable than the last, specific real examples, end with most mind-blowing",
        "color": "#DDA0DD",
        "tags": ["aitools", "artificialintelligence", "mindblowing", "tech", "future"],
    },
    {
        "tema": "This free AI tool generates $10,000 websites in 30 seconds",
        "angulo": "specific tool named, exact steps shown through narration, income potential emphasized",
        "color": "#00FF88",
        "tags": ["aitools", "webdesign", "makemoneyonline", "artificialintelligence"],
    },
    {
        "tema": "Google just released an AI that makes Siri look like a toy",
        "angulo": "comparison format, specific capabilities listed, dramatic reactions, future implications",
        "color": "#FFD700",
        "tags": ["google", "gemini", "aitools", "technews", "artificialintelligence"],
    },
    {
        "tema": "The dark side of AI that nobody is talking about",
        "angulo": "expose format, specific real examples of AI risks, balanced but alarming, thought provoking",
        "color": "#FF4444",
        "tags": ["artificialintelligence", "airisks", "tech", "future", "darkside"],
    },
    {
        "tema": "How I automated my entire business with free AI tools",
        "angulo": "personal story format, specific tools used, before and after income, step by step",
        "color": "#00BFFF",
        "tags": ["automation", "aitools", "entrepreneur", "passiveincome", "tech"],
    },
    {
        "tema": "The AI video generator that is making YouTubers nervous",
        "angulo": "dramatic reveals of capabilities, show what it can create, implications for content creators",
        "color": "#FF8C00",
        "tags": ["aivideo", "aitools", "youtube", "contentcreation", "artificialintelligence"],
    },
]

CONSULTAS_BROLL_AI = [
    "futuristic technology computer screen", "artificial intelligence robot",
    "data visualization holographic", "coding programming screen",
    "neural network visualization", "technology abstract blue",
    "smartphone technology future", "server room data center",
    "digital transformation technology", "machine learning visualization",
    "cyber technology neon", "tech startup office modern",
    "holographic display futuristic", "binary code digital",
    "robot hand human hand", "brain technology interface",
]

CONSULTAS_RESPALDO = [
    "technology background abstract", "digital network connection",
    "futuristic city night", "circuit board closeup",
    "neon lights technology", "computer keyboard closeup",
]


def generar_contenido(tema_info: dict) -> dict:
    prompt = f"""You are a viral tech content creator at the level of MKBHD and Marques Brownlee combined.
Create a 55-second TikTok/Shorts script in ENGLISH ONLY about: {tema_info['tema']}

Angle: {tema_info['angulo']}

Rules for maximum virality:
1. First sentence MUST make people stop scrolling immediately
2. Use specific numbers, tool names, and real examples
3. Every sentence should make viewer want to hear the next one
4. End with something that makes them want to share or save
5. Conversational tone like you are talking to a friend, not reading a script
6. Include a clear call to action at the end (follow for more, try this tool, etc.)

Also create:
- A main character (tech expert or user discovering these tools, with name and description)
- A setting (modern tech environment)
- 3 visual scene descriptions for AI image generation (tech focused, professional)

IMPORTANT: Write EVERYTHING in ENGLISH ONLY. The guion MUST be at least 200 words minimum. Write enough content to fill 75-90 seconds when read aloud. DO NOT write less than 200 words. Be specific, use real examples, and fill every second with valuable content.
Return ONLY valid JSON, no markdown, no backticks:
{{
  "personaje": {{"nombre": "...", "descripcion": "...", "personalidad": "tech savvy, excited, relatable"}},
  "lugar": {{"nombre": "...", "descripcion": "modern tech environment..."}},
  "hook": "...(first sentence that stops the scroll)...",
  "guion": "...(full 55 second script in ENGLISH, conversational and viral)...",
  "escenas": ["tech scene 1", "tech scene 2", "tech scene 3"],
  "titulo": "...(viral YouTube/TikTok title in ENGLISH with emoji, max 60 chars)...",
  "tags": {json.dumps(tema_info['tags'])}
}}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.95, "maxOutputTokens": 3000}
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
                        "personaje": {"nombre": "Alex", "descripcion": "tech expert", "personalidad": "excited"},
                        "lugar": {"nombre": "Tech Lab", "descripcion": "modern office with screens"},
                        "hook": "This AI tool just changed everything.",
                        "guion": f"You need to know about this. {tema_info['tema']}. This is going to blow your mind.",
                        "escenas": ["futuristic tech screen", "ai visualization", "modern workspace"],
                        "titulo": "This AI Tool Changes EVERYTHING 🤯",
                        "tags": tema_info["tags"]
                    }
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_ai") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"professional tech photography, cinematic, 4k, high quality: {prompt}",
        "parameters": {"width": 768, "height": 1344}
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
        f"Professional tech content creator, {personaje.get('nombre', 'Alex')}, "
        f"{personaje.get('descripcion', 'tech expert')}, "
        f"in {lugar.get('nombre', 'modern tech office')}, "
        "professional lighting, youtube thumbnail style, 4k"
    )
    ruta = generar_imagen_ia(prompt_personaje, 0)
    if ruta:
        rutas.append(ruta)

    for i, escena in enumerate(escenas[:3]):
        ruta = generar_imagen_ia(
            f"{escena}, {lugar.get('descripcion', 'tech environment')}, "
            "professional tech photography, 4k cinematic", i + 1
        )
        if ruta:
            rutas.append(ruta)
    return rutas


def crear_intro_imagen(hook: str, color: str) -> str:
    img = Image.new("RGB", RESOLUCION, color=(5, 5, 15))
    draw = ImageDraw.Draw(img)

    # Gradiente azul tech
    for y in range(RESOLUCION[1]):
        ratio = y / RESOLUCION[1]
        r_val = int(0 + ratio * 10)
        g_val = int(10 + ratio * 20)
        b_val = int(30 + ratio * 50)
        draw.line([(0, y), (RESOLUCION[0], y)], fill=(r_val, g_val, b_val))

    # Lineas de acento
    accent_color = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    draw.rectangle([(0, 0), (RESOLUCION[0], 6)], fill=accent_color)
    draw.rectangle([(0, RESOLUCION[1]-6), (RESOLUCION[0], RESOLUCION[1])], fill=accent_color)

    try:
        font_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 68)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_grande = ImageFont.load_default()
        font_small = font_grande

    # Badge "AI EXPLAINED" arriba
    badge_text = "⚡ AI EXPLAINED"
    bbox = draw.textbbox((0, 0), badge_text, font=font_small)
    bw = bbox[2] - bbox[0]
    bx = (RESOLUCION[0] - bw) // 2
    draw.text((bx, 80), badge_text, font=font_small, fill=accent_color)

    # Texto principal
    palabras = hook.split()
    lineas = []
    linea_actual = ""
    for palabra in palabras:
        test = linea_actual + " " + palabra if linea_actual else palabra
        if len(test) < 22:
            linea_actual = test
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    if linea_actual:
        lineas.append(linea_actual)

    y_start = RESOLUCION[1] // 2 - (len(lineas) * 85) // 2
    for linea in lineas:
        bbox = draw.textbbox((0, 0), linea, font=font_grande)
        w = bbox[2] - bbox[0]
        x = (RESOLUCION[0] - w) // 2
        # Sombra
        draw.text((x+3, y_start+3), linea, font=font_grande, fill=(0, 0, 0))
        # Texto blanco
        draw.text((x, y_start), linea, font=font_grande, fill=(255, 255, 255))
        y_start += 90

    destino = "intro_ai.png"
    img.save(destino)
    return destino


def descargar_musica() -> str:
    url = random.choice(MUSICA_AMBIENTE)
    destino = "musica_ai.mp3"
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Musica: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso musica: {e}")
        return None


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio_ai.mp3"):
    asyncio.run(_tts(texto, salida))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("tiny")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def _descargar_desde_consultas(consultas, headers, carpeta, indice_inicial, por_consulta=5):
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


def descargar_clips(carpeta: str = "clips_ai"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    rutas, siguiente = _descargar_desde_consultas(
        CONSULTAS_BROLL_AI, headers, carpeta, 0, por_consulta=5
    )
    if len(rutas) < 20:
        print(f"Solo {len(rutas)} clips, añadiendo respaldo...")
        extra, _ = _descargar_desde_consultas(
            CONSULTAS_RESPALDO, headers, carpeta, siguiente, por_consulta=6
        )
        rutas.extend(extra)
    print(f"Total clips: {len(rutas)}")
    return rutas


def armar_video(clips_pexels, imagenes_ia, audio_path, segmentos,
                color, intro_img, musica_path, salida="video_ai_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    OFFSET = 2.5

    clips_finales = []
    tiempo_acumulado = 0

    # Intro (2.5s)
    if intro_img:
        try:
            intro = ImageClip(intro_img).set_duration(OFFSET)
            clips_finales.append(intro)
            tiempo_acumulado += OFFSET
        except Exception as e:
            print(f"Aviso intro: {e}")

    # Imagenes IA (3s cada una)
    for ruta_img in imagenes_ia:
        if tiempo_acumulado >= duracion_total + OFFSET:
            break
        try:
            dur = min(3.0, (duracion_total + OFFSET) - tiempo_acumulado)
            c = ImageClip(ruta_img).set_duration(dur)
            clips_finales.append(c)
            tiempo_acumulado += dur
        except Exception as e:
            print(f"Aviso imagen: {e}")

    # Clips de Pexels
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
        dur_clip = min(c.duration, restante, random.uniform(1.5, 3.5))
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

    # Audio
    audio_voz = audio_voz.set_start(OFFSET)
    audios = [audio_voz]

    if musica_path:
        try:
            import math
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

    # Color accent del tema
    accent = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    hex_color = color

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
                palabra.upper(), fontsize=88, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=4,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.73), relative=True)

            txt = TextClip(
                palabra.upper(), fontsize=88, color="white",
                font="DejaVu-Sans-Bold", stroke_color=hex_color, stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.73), relative=True)

            subtitulos.append(sombra)
            subtitulos.append(txt)

    # Badge "AI TOOLS" en la parte superior durante todo el video
    badge = TextClip(
        "⚡ AI TOOLS", fontsize=42, color=hex_color,
        font="DejaVu-Sans-Bold",
    ).set_start(OFFSET).set_end(duracion_total + OFFSET).set_position(("center", 0.05), relative=True)
    subtitulos.append(badge)

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
            "categoryId": "28",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("Subido YouTube:", response.get("id"))


def main():
    tema_info = random.choice(TEMAS_AI)
    print(f"Tema: {tema_info['tema']}")

    contenido = generar_contenido(tema_info)
    print(f"Hook: {contenido.get('hook', '')}")
    print(f"Personaje: {contenido['personaje']['nombre']}")

    color = tema_info["color"]
    imagenes_ia = generar_imagenes(contenido)
    intro_img = crear_intro_imagen(contenido.get("hook", tema_info["tema"]), color)
    musica_path = descargar_musica()

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    clips = descargar_clips()

    video_path = armar_video(
        clips, imagenes_ia, audio_path, segmentos,
        color, intro_img, musica_path
    )

    titulo = contenido.get("titulo", "This AI Tool Changes EVERYTHING 🤯")
    descripcion = (
        f"{contenido['guion']}\n\n"
        f"Follow for daily AI tools and tips!\n\n"
        f"#{' #'.join(tema_info['tags'])}"
    )
    tags = tema_info["tags"] + ["aitools", "artificialintelligence", "tech", "shorts"]
    subir_youtube(video_path, titulo, descripcion, tags)

    print(f"\n✅ Video listo: {video_path}")
    print("Sube este archivo manualmente a TikTok para maxima viralidad")


if __name__ == "__main__":
    main()
