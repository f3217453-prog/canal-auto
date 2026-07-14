"""
Pipeline estilo "Mr. Finance" - The Economics of owning a business
Videos de 20-25 minutos explicando la economia de diferentes negocios
Estilo: voz profesional + imagenes IA de infografias + miniaturas llamativas
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

NEGOCIOS = [
    "a Movie Theater", "a Gas Station", "a Car Wash",
    "a McDonald's Franchise", "a Hotel", "a Gym",
    "a Laundromat", "a Parking Lot", "a Bowling Alley",
    "a Coffee Shop", "a Nightclub", "a Car Dealership",
    "a Supermarket", "a Pharmacy", "a Golf Course",
    "an Airport", "a Casino", "a Football Stadium",
    "a Shopping Mall", "a Solar Farm", "a Storage Unit Facility",
    "a Trucking Company", "a Pizza Franchise", "a Barbershop",
    "a Tattoo Shop", "a Dental Office", "a Food Truck",
    "a Brewery", "a Vineyard", "a Ski Resort",
]

MUSICA_FONDO = [
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_5bbc9a1a1c.mp3",
]

CONSULTAS_BROLL = {
    "general": [
        "business office professional", "money cash business",
        "entrepreneur working laptop", "business meeting professional",
        "financial charts graphs", "city aerial business district",
        "handshake business deal", "successful businessman",
    ],
    "costos": [
        "construction building site", "equipment machinery industrial",
        "invoice receipt business", "calculator financial planning",
        "bank loan documents", "real estate commercial property",
    ],
    "operaciones": [
        "employee working team", "customer service business",
        "supply chain logistics", "inventory warehouse",
        "marketing advertising business", "technology business tools",
    ],
    "ganancias": [
        "profit growth chart", "successful business revenue",
        "investor meeting business", "financial success money",
        "luxury lifestyle entrepreneur", "stock market trading",
    ],
}

CONSULTAS_RESPALDO = [
    "business professional office", "entrepreneur success",
    "financial planning charts", "modern office building",
]


def generar_guion_extension(negocio: str, guion_corto: str) -> str:
    palabras_actuales = len(guion_corto.split())
    palabras_necesarias = 3000 - palabras_actuales
    prompt = f"""You are a financial documentary writer.
The following script about {negocio} is too short ({palabras_actuales} words).
Extend it by {palabras_necesarias} more words IN ENGLISH ONLY.
Add more specific financial details, real examples, deeper analysis.
Return ONLY the complete extended narration, no JSON, no titles:

{guion_corto}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 8000}
    }
    for modelo in MODELOS_GEMINI:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{modelo}:generateContent?key={GEMINI_API_KEY}"
            )
            r = requests.post(url, json=body, timeout=180)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Error extendiendo guion: {e}")
            time.sleep(5)
    return guion_corto


def generar_contenido(negocio: str) -> dict:
    prompt = f"""You are a professional financial documentary writer at the level of the YouTube channel "Mr. Finance".

Write a detailed 22-minute documentary script IN ENGLISH ONLY about: "The Economics of Owning {negocio}"

Structure (follow this exactly):
1. HOOK (1 min): Start with a shocking financial fact about this business that most people don't know
2. OVERVIEW (2 min): What this business actually is, history, market size
3. STARTUP COSTS (4 min): Detailed breakdown of every cost to start this business (equipment, location, licenses, staff, inventory). Use REAL specific numbers.
4. MONTHLY OPERATING COSTS (4 min): Rent, salaries, utilities, supplies, insurance, marketing. Real numbers.
5. REVENUE STREAMS (4 min): How this business makes money, all revenue streams, realistic income ranges
6. PROFIT MARGINS (3 min): Real profit margins, what successful vs struggling versions look like, break-even point
7. CHALLENGES AND RISKS (2 min): What can go wrong, common failure reasons
8. SUCCESS SECRETS (2 min): What the most successful operators do differently

Rules:
- Use REAL specific dollar amounts throughout (ranges are fine)
- Make it feel like you are revealing insider secrets most people dont know
- Conversational but authoritative tone
- Every section should have at least one surprising or counterintuitive fact
- Aim for 3000-3500 words total

IMPORTANT: Write EVERYTHING in ENGLISH ONLY.
Return ONLY valid JSON, no markdown, no backticks:
{{
  "negocio": "{negocio}",
  "hook_stat": "...(the most shocking financial fact about this business)...",
  "guion": "...(full 22 min narration in ENGLISH, 3000-3500 words)...",
  "escenas": [
    "exterior shot of {negocio} business building professional",
    "interior business operations employees working",
    "financial documents money calculations business",
    "successful owner entrepreneur confident",
    "customers using the business service"
  ],
  "titulo": "So You Want To Own {negocio}? The Truth About The Money",
  "descripcion_video": "...(compelling YouTube description in ENGLISH about the economics of {negocio}, 4-5 sentences with keywords)...",
  "tags": ["economics", "business", "entrepreneur", "finance", "howmuchdoesmake"]
}}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 8000}
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
                    palabras = len(contenido.get("guion", "").split())
                    print(f"Guion generado: {palabras} palabras")
                    if palabras < 2000:
                        print(f"Guion corto ({palabras} palabras), extendiendo...")
                        contenido["guion"] = generar_guion_extension(negocio, contenido["guion"])
                        print(f"Guion extendido: {len(contenido['guion'].split())} palabras")
                    return contenido
                except json.JSONDecodeError:
                    return {
                        "negocio": negocio,
                        "hook_stat": f"Most people who open {negocio} fail within the first 3 years.",
                        "guion": f"So you want to own {negocio}. Before you sign any papers or write any checks, there are things you absolutely need to know about this business that most people find out too late.",
                        "escenas": [
                            f"exterior {negocio} business building",
                            "business owner working desk",
                            "financial charts money",
                            "customers business service",
                            "entrepreneur success"
                        ],
                        "titulo": f"So You Want To Own {negocio}? The Truth About The Money",
                        "descripcion_video": f"The complete financial breakdown of owning {negocio}.",
                        "tags": ["economics", "business", "entrepreneur", "finance"]
                    }
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_finance") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": (
            f"professional business infographic illustration style, "
            f"clean modern design, financial documentary: {prompt}"
        ),
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
        print(f"Imagen IA: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso imagen IA: {e}")
        return None


def generar_imagenes(contenido: dict) -> list:
    rutas = []
    negocio = contenido.get("negocio", "business")
    escenas = contenido.get("escenas", [])
    for i, escena in enumerate(escenas[:5]):
        ruta = generar_imagen_ia(escena, i)
        if ruta:
            rutas.append(ruta)
    return rutas


def crear_miniatura(negocio: str, hook_stat: str) -> str:
    """Crea miniatura estilo Mr. Finance"""
    img = Image.new("RGB", (1280, 720), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)

    # Fondo con gradiente oscuro
    for y in range(720):
        ratio = y / 720
        r_val = int(10 + ratio * 20)
        g_val = int(10 + ratio * 15)
        b_val = int(10 + ratio * 10)
        draw.line([(0, y), (1280, y)], fill=(r_val, g_val, b_val))

    # Banda roja superior
    draw.rectangle([(0, 0), (1280, 12)], fill=(220, 30, 30))

    try:
        font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    except:
        font_titulo = ImageFont.load_default()
        font_sub = font_titulo
        font_small = font_titulo

    # "SO YOU WANT TO OWN"
    texto1 = "SO YOU WANT TO OWN"
    bbox = draw.textbbox((0, 0), texto1, font=font_small)
    w = bbox[2] - bbox[0]
    x = (1280 - w) // 2
    draw.text((x, 50), texto1, font=font_small, fill=(200, 200, 200))

    # Nombre del negocio en grande y rojo
    negocio_upper = negocio.upper()
    palabras = negocio_upper.split()
    lineas = []
    linea = ""
    for p in palabras:
        test = linea + " " + p if linea else p
        if len(test) < 18:
            linea = test
        else:
            lineas.append(linea)
            linea = p
    if linea:
        lineas.append(linea)

    y_neg = 120
    for linea in lineas:
        bbox = draw.textbbox((0, 0), linea, font=font_titulo)
        w = bbox[2] - bbox[0]
        x = (1280 - w) // 2
        draw.text((x+3, y_neg+3), linea, font=font_titulo, fill=(0, 0, 0))
        draw.text((x, y_neg), linea, font=font_titulo, fill=(220, 30, 30))
        y_neg += 85

    # Linea separadora
    draw.rectangle([(100, y_neg + 10), (1180, y_neg + 14)], fill=(220, 30, 30))

    # Hook stat abajo
    hook_words = hook_stat[:80] + "..." if len(hook_stat) > 80 else hook_stat
    palabras_hook = hook_words.split()
    lineas_hook = []
    linea_h = ""
    for p in palabras_hook:
        test = linea_h + " " + p if linea_h else p
        if len(test) < 35:
            linea_h = test
        else:
            lineas_hook.append(linea_h)
            linea_h = p
    if linea_h:
        lineas_hook.append(linea_h)

    y_hook = y_neg + 30
    for linea in lineas_hook[:3]:
        bbox = draw.textbbox((0, 0), linea, font=font_small)
        w = bbox[2] - bbox[0]
        x = (1280 - w) // 2
        draw.text((x, y_hook), linea, font=font_small, fill=(255, 255, 255))
        y_hook += 48

    # Badge "THE ECONOMICS OF" abajo
    badge = "THE ECONOMICS OF"
    bbox = draw.textbbox((0, 0), badge, font=font_small)
    w = bbox[2] - bbox[0]
    x = (1280 - w) // 2
    draw.rectangle([(x-20, 650), (x+w+20, 700)], fill=(220, 30, 30))
    draw.text((x, 655), badge, font=font_small, fill=(255, 255, 255))

    destino = "miniatura_finance.png"
    img.save(destino)
    print(f"Miniatura creada: {destino}")
    return destino


def descargar_musica() -> str:
    url = random.choice(MUSICA_FONDO)
    destino = "musica_finance.mp3"
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


def generar_audio(texto: str, salida: str = "audio_finance.mp3"):
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


def descargar_clips(negocio: str, carpeta: str = "clips_finance"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}

    # Clips especificos del negocio
    negocio_limpio = negocio.lower().replace("a ", "").replace("an ", "")
    consultas_negocio = [
        f"{negocio_limpio} business exterior",
        f"{negocio_limpio} interior",
        f"{negocio_limpio} employees working",
        f"{negocio_limpio} customers",
    ]

    # Clips de negocios generales
    todas_consultas = (
        consultas_negocio +
        CONSULTAS_BROLL["general"] +
        CONSULTAS_BROLL["costos"] +
        CONSULTAS_BROLL["operaciones"] +
        CONSULTAS_BROLL["ganancias"]
    )

    rutas, siguiente = _descargar_desde_consultas(todas_consultas, headers, carpeta, 0)
    if len(rutas) < 40:
        print(f"Solo {len(rutas)} clips, completando...")
        extra, _ = _descargar_desde_consultas(
            CONSULTAS_RESPALDO, headers, carpeta, siguiente, por_consulta=8
        )
        rutas.extend(extra)
    print(f"Total clips: {len(rutas)}")
    return rutas


def armar_video(clips_pexels, imagenes_ia, audio_path, segmentos,
                musica_path, salida="video_finance_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    OFFSET = 5.0  # intro de 5 segundos

    clips_finales = []
    tiempo_acumulado = 0

    # Imagenes IA intercaladas (6s cada una)
    for ruta_img in imagenes_ia:
        if tiempo_acumulado >= duracion_total + OFFSET:
            break
        try:
            dur = min(6.0, (duracion_total + OFFSET) - tiempo_acumulado)
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

    # Audio
    audio_voz = audio_voz.set_start(OFFSET)
    audios = [audio_voz]

    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            duracion_video = video_base.duration
            if musica.duration < duracion_video:
                loops = math.ceil(duracion_video / musica.duration)
                musica = concatenate_audioclips([musica] * loops)
            musica = musica.subclip(0, duracion_video).volumex(0.08)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)
    video_base = video_base.set_duration(duracion_total + OFFSET)

    # Subtitulos word by word
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
                palabra.upper(), fontsize=65, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.82), relative=True)

            txt = TextClip(
                palabra.upper(), fontsize=65, color="white",
                font="DejaVu-Sans-Bold", stroke_color="#DC1E1E", stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(("center", 0.82), relative=True)

            subtitulos.append(sombra)
            subtitulos.append(txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total + OFFSET)
    final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac",
                          threads=2, preset="ultrafast")
    return salida


def subir_youtube(video_path: str, miniatura_path: str,
                  titulo: str, descripcion: str, tags: list):
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
            "categoryId": "27",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response.get("id")
    print(f"Video subido: {video_id}")

    # Subir miniatura
    if miniatura_path and video_id:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(miniatura_path)
            ).execute()
            print("Miniatura subida")
        except Exception as e:
            print(f"Aviso miniatura: {e}")


def main():
    negocio = random.choice(NEGOCIOS)
    print(f"Negocio elegido: {negocio}")

    contenido = generar_contenido(negocio)
    palabras = len(contenido["guion"].split())
    print(f"Guion: {palabras} palabras")
    print(f"Hook: {contenido.get('hook_stat', '')}")

    imagenes_ia = generar_imagenes(contenido)
    miniatura = crear_miniatura(negocio, contenido.get("hook_stat", ""))
    musica_path = descargar_musica()

    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    clips = descargar_clips(negocio)

    video_path = armar_video(clips, imagenes_ia, audio_path, segmentos, musica_path)

    titulo = contenido.get("titulo", f"So You Want To Own {negocio}? The Truth About The Money")
    descripcion = contenido.get("descripcion_video", "")
    descripcion += f"\n\n#economics #business #entrepreneur #finance ##{negocio.replace(' ', '').replace('a', '').strip()}"
    tags = contenido.get("tags", ["economics", "business", "entrepreneur", "finance"])

    subir_youtube(video_path, miniatura, titulo, descripcion, tags)
    print(f"\nVideo completado: {video_path}")


if __name__ == "__main__":
    main()
