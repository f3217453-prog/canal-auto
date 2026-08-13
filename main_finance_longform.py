"""
WealthSnap - Pipeline Longform Finanzas - Version 1.0

Videos de 3-4 minutos sobre finanzas personales.
Alterna entre: explicaciones profundas de un concepto financiero,
top 5 habitos/errores/secretos desarrollados, y casos reales de
personas que construyeron riqueza desde cero.
CPM objetivo: $18-$45 (categoria Education en YouTube).
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

RESOLUCION = (1920, 1080)  # Landscape para video largo
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

NEGATIVE_PROMPT = (
    "deformed hands, extra fingers, mutated, blurry, watermark, text, "
    "logo, low quality, low resolution"
)

VOCES_FINANCE = [
    "en-US-AndrewNeural",
    "en-US-ChristopherNeural",
    "en-GB-RyanNeural",
    "en-AU-WilliamNeural",
    "en-US-GuyNeural",
]

MUSICA_FINANCE = [
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
]

FORMATOS_LONGFORM = {
    "explicacion": {
        "temas": [
            "how compound interest actually works and why starting at 25 vs 35 costs you $500,000",
            "the real reason most people never build wealth despite earning good salaries",
            "how the 50/30/20 budget rule works and why most people apply it wrong",
            "what index fund investing actually means and why Warren Buffett recommends it",
            "how credit scores actually work and the fastest ways to improve yours",
            "the real difference between assets and liabilities and why it determines your wealth",
            "how inflation silently destroys savings and what to do about it",
            "what passive income actually means and the realistic paths to get there",
        ],
        "prompt": """You are a clear, trustworthy finance educator for WealthSnap YouTube channel.
Create a 3-4 minute explainer script about: {tema}

Structure:
- HOOK (50 words): Start with a surprising stat or counterintuitive fact. Make them need to know more.
- EXPLANATION (150 words): Break down the concept clearly. Use a specific real-world example with numbers.
- WHY IT MATTERS (100 words): Show the real financial impact with specific dollar amounts or percentages.
- ACTION STEP (50 words): One specific thing they can do TODAY. Not vague advice.

Total: 350-400 words STRICT. ENGLISH ONLY. Be accurate — cite real data where possible.

Also provide:
- 5 scene descriptions for AI image generation (professional finance aesthetic)
- Hook line (under 10 words, reveals a surprising financial truth)
- Chapter timestamps:
  0:00 The Surprising Truth
  1:00 How It Actually Works
  2:30 What This Means For You
  3:30 What To Do Today

TITLE: Specific, educational, no clickbait. Add 💰 emoji. No hashtags.
Example: "Why Saving $200/Month at 25 Makes You a Millionaire 💰"

Return ONLY valid JSON:
{{
"hook": "...(under 10 words)...",
"guion": "...(350-400 words STRICT)...",
"escenas": ["scene 1", "scene 2", "scene 3", "scene 4", "scene 5"],
"capitulos": "0:00 The Surprising Truth\\n1:00 How It Actually Works\\n2:30 What This Means For You\\n3:30 What To Do Today",
"titulo": "...(educational title + 💰, NO hashtags)...",
"tags": ["finance", "personalfinance", "money", "investing", "wealth", "financialfreedom", "budgeting", "savemoney", "moneytips", "wealthbuilding"]
}}""",
        "consultas_broll": [
            "financial planning desk", "investment charts growth",
            "businessman working office", "money savings bank",
            "calculator budget spreadsheet", "stock market data screen",
            "luxury home family wealth", "retirement planning couple",
        ],
    },
    "top5_longform": {
        "temas": [
            "5 financial habits that separate millionaires from everyone else",
            "5 money mistakes that destroy wealth silently over decades",
            "5 things rich people buy that poor people think are wasteful",
            "5 investment strategies that outperform most financial advisors",
            "5 ways the wealthy use debt to build more wealth",
            "5 financial books that changed how millionaires think about money",
            "5 passive income streams that actually work in 2026",
        ],
        "prompt": """You are a trusted finance narrator for WealthSnap YouTube channel.
Create a top 5 countdown script about: {tema}

Structure:
- INTRO (50 words): Hook immediately. Tease #1. Tell them it will change how they see money.
- ENTRIES 5 through 1 (60 words each = 300 words): 
  Each entry with specific data, real examples, and actionable insight.
  Build value — each entry more impactful than the last.
  At #3 tease #1: "but the most powerful one is coming..."
  #1 must be the most counterintuitive or impactful.
- OUTRO (30 words): Encourage them to apply entry #1 this week. Ask them to comment.

Total: 350-400 words STRICT. ENGLISH ONLY. Use real numbers and data.

Also provide:
- 5 scene descriptions for AI image generation
- Hook line (under 10 words)
- Chapter timestamps:
  0:00 Introduction
  0:45 #5
  1:30 #4
  2:00 #3
  2:45 #2
  3:15 #1

TITLE: "Top 5 [topic] 💰" format. Educational and specific.

Return ONLY valid JSON:
{{
"hook": "...(under 10 words)...",
"guion": "...(350-400 words STRICT)...",
"escenas": ["scene 1", "scene 2", "scene 3", "scene 4", "scene 5"],
"capitulos": "0:00 Introduction\\n0:45 #5\\n1:30 #4\\n2:00 #3\\n2:45 #2\\n3:15 #1",
"titulo": "...(Top 5 title + 💰, NO hashtags)...",
"tags": ["finance", "personalfinance", "money", "top5", "wealth", "investing", "financetips", "moneytips", "rich", "millionaire"]
}}""",
        "consultas_broll": [
            "businessman luxury lifestyle", "investment portfolio screen",
            "money growth chart", "wealthy person working",
            "financial success achievement", "stock market trading",
            "real estate investment", "passive income laptop",
        ],
    },
}

CONSULTAS_RESPALDO = [
    "financial success money", "business professional office",
    "investment wealth growth", "money management",
]


def generar_contenido() -> tuple:
    formato_key = random.choice(list(FORMATOS_LONGFORM.keys()))
    formato = FORMATOS_LONGFORM[formato_key]
    tema = random.choice(formato["temas"])
    prompt = formato["prompt"].format(tema=tema)

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 4000}
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
                    time.sleep(20)
                    continue
                r.raise_for_status()
                data = r.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r"```json|```", "", texto).strip()
                contenido = json.loads(texto)
                palabras = len(contenido.get("guion", "").split())
                print(f"Formato: {formato_key} | Tema: {tema} | {palabras} palabras")
                return contenido, formato
            except Exception as e:
                print(f"Error {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_finance_long") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": (
            f"professional financial photography, clean corporate aesthetic, "
            f"high quality, 4k: {prompt}"
        ),
        "parameters": {
            "width": 1344, "height": 768,
            "negative_prompt": NEGATIVE_PROMPT
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
        return destino
    except Exception as e:
        print(f"Aviso imagen {indice}: {e}")
        return None


def generar_imagenes(escenas: list) -> list:
    # Reducido a 3 imagenes (antes 5) para ahorrar RAM y tiempo de generacion
    return [
        ruta for i, escena in enumerate(escenas[:3])
        if (ruta := generar_imagen_ia(f"{escena}, professional finance", i))
    ]


def generar_thumbnail(titulo: str, imagen_ia_path: str, salida: str = "thumbnail_finance.jpg") -> str:
    """
    Thumbnail clickbait basado en datos 2026:
    - Fondo muy oscuro con imagen IA
    - Texto grande en verde brillante (color del dinero) + dorado para numeros
    - Texto del titulo completo visible (no solo 3 palabras)
    - Badge WealthSnap en esquina inferior izquierda
    - Borde verde brillante para separar del fondo blanco de YouTube
    Patron ganador en finanzas: clean background + big readable text + emotional hook
    """
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), color=(8, 8, 8))

    # Fondo: imagen IA muy oscurecida (85% oscuro) — el texto es el protagonista
    if imagen_ia_path and os.path.exists(imagen_ia_path):
        try:
            fondo = Image.open(imagen_ia_path).convert("RGB")
            escala = max(W / fondo.width, H / fondo.height)
            nuevo_w = int(fondo.width * escala)
            nuevo_h = int(fondo.height * escala)
            fondo = fondo.resize((nuevo_w, nuevo_h), Image.LANCZOS)
            x = (nuevo_w - W) // 2
            y = (nuevo_h - H) // 2
            fondo = fondo.crop((x, y, x + W, y + H))
            # Overlay muy oscuro para que el texto resalte
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 200))
            fondo_rgba = fondo.convert("RGBA")
            img = Image.alpha_composite(fondo_rgba, overlay).convert("RGB")
        except Exception as e:
            print(f"Aviso fondo thumbnail: {e}")

    draw = ImageDraw.Draw(img)

    # Borde verde brillante (color del dinero)
    draw.rectangle([(0, 0), (W-1, H-1)], outline=(0, 220, 80), width=8)

    try:
        font_titulo = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 85
        )
        font_sub = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
        )
        font_badge = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36
        )
    except Exception:
        font_titulo = ImageFont.load_default()
        font_sub = font_titulo
        font_badge = font_titulo

    # Texto principal: titulo limpio sin hashtags ni emojis
    texto_limpio = (
        titulo
        .replace("💰","").replace("📈","").replace("🤑","")
        .replace("#Shorts","").replace("#Finance","").replace("#finance","")
        .strip()
    )

    # Dividir en lineas de maximo 18 chars para que quepa en el thumbnail
    palabras = texto_limpio.split()
    lineas = []
    linea_actual = ""
    for palabra in palabras:
        if len(linea_actual + " " + palabra) <= 18:
            linea_actual += " " + palabra if linea_actual else palabra
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    if linea_actual:
        lineas.append(linea_actual)
    lineas = lineas[:4]  # maximo 4 lineas

    # Centrar verticalmente el bloque de texto
    alto_bloque = len(lineas) * 100
    y_start = (H - alto_bloque) // 2 - 20

    for i, linea in enumerate(lineas):
        # Color alternado: primera linea en dorado, resto en verde brillante
        color_linea = (255, 215, 0) if i == 0 else (0, 255, 80)

        bbox = draw.textbbox((0, 0), linea.upper(), font=font_titulo)
        w_texto = bbox[2] - bbox[0]
        x_pos = (W - w_texto) // 2  # centrado horizontal

        # Sombra negra para legibilidad
        for dx, dy in [(-3,-3),(3,3),(-3,3),(3,-3),(0,4),(4,0)]:
            draw.text((x_pos+dx, y_start+dy), linea.upper(),
                     font=font_titulo, fill=(0,0,0))
        # Texto principal
        draw.text((x_pos, y_start), linea.upper(),
                 font=font_titulo, fill=color_linea)
        y_start += 100

    # Badge WealthSnap en esquina inferior izquierda
    draw.rectangle([(12, H-62), (270, H-12)], fill=(0, 180, 60))
    draw.text((22, H-54), "💰 WEALTHSNAP", font=font_badge, fill=(255,255,255))

    img.save(salida, "JPEG", quality=92, optimize=True)
    print(f"Thumbnail generado: {salida}")
    return salida


async def _tts(texto, salida, voz):
    await edge_tts.Communicate(texto, voz).save(salida)


def generar_audio(texto, salida="audio_finance_long.mp3"):
    voz = random.choice(VOCES_FINANCE)
    print(f"Voz: {voz}")
    asyncio.run(_tts(texto, salida, voz))
    return salida


def transcribir(audio_path):
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path, language="en")["segments"]
    # Liberar memoria RAM inmediatamente despues de transcribir
    del modelo
    import gc
    gc.collect()
    return resultado


def _buscar_clips(consulta, headers, carpeta, indice, por_consulta=10):
    rutas = []
    idx = indice
    try:
        r = requests.get(
            f"https://api.pexels.com/videos/search?query={consulta}&per_page={por_consulta}",
            headers=headers, timeout=30
        )
        r.raise_for_status()
        for v in r.json().get("videos", []):
            archivos = sorted(v["video_files"], key=lambda f: f.get("width", 0))
            if not archivos:
                continue
            enlace = archivos[len(archivos)//2]["link"]  # calidad media, no maxima
            destino = f"{carpeta}/clip_{idx}.mp4"
            try:
                with requests.get(enlace, stream=True, timeout=60) as resp:
                    with open(destino, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                rutas.append(destino)
                idx += 1
            except Exception:
                pass
    except Exception as e:
        print(f"Aviso busqueda '{consulta}': {e}")
    return rutas, idx


def descargar_clips(escenas, formato, carpeta="clips_finance_long"):
    """Descarga clips reducidos para no agotar la RAM del runner (exit code 143)."""
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    indice = 0
    clips_por_escena = []
    for escena in escenas:
        # Reducido a 5 clips por escena (antes 10) para ahorrar RAM
        rutas, indice = _buscar_clips(escena, headers, carpeta, indice, 5)
        clips_por_escena.append(rutas)
    pool_generico = []
    for consulta in formato["consultas_broll"]:
        # Reducido a 5 clips por consulta (antes 10)
        rutas, indice = _buscar_clips(consulta, headers, carpeta, indice, 5)
        pool_generico.extend(rutas)
    total = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    if total < 15:
        for consulta in CONSULTAS_RESPALDO:
            extra, indice = _buscar_clips(consulta, headers, carpeta, indice, 5)
            pool_generico.extend(extra)
    print(f"Total clips: {sum(len(c) for c in clips_por_escena) + len(pool_generico)}")
    return clips_por_escena, pool_generico


def _preparar_clip(ruta, dur_max):
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
    dur_clip = min(c.duration, dur_max, random.uniform(3.0, 6.0))
    if dur_clip <= 0:
        c.close()
        return None
    return c.subclip(0, dur_clip)


def _rellenar_con_pool(clips_finales, tiempo_acumulado, limite, pool):
    if not pool:
        return tiempo_acumulado
    pool_s = list(pool)
    random.shuffle(pool_s)
    idx = 0
    intentos = 0
    while tiempo_acumulado < limite and intentos < len(pool_s) * 3:
        c = _preparar_clip(pool_s[idx % len(pool_s)], limite - tiempo_acumulado)
        idx += 1
        intentos += 1
        if c is None:
            continue
        clips_finales.append(c)
        tiempo_acumulado += c.duration
    return tiempo_acumulado


def armar_video(clips_por_escena, pool_generico, imagenes_ia, audio_path,
                 segmentos, hook_texto, musica_path, salida="video_finance_long.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    print(f"Duracion audio: {duracion_total:.1f}s ({duracion_total/60:.1f} min)")

    n_escenas = max(len(clips_por_escena), 1)
    dur_por_escena = duracion_total / n_escenas
    clips_finales = []
    tiempo_acumulado = 0.0

    for i in range(n_escenas):
        limite_tramo = (i + 1) * dur_por_escena
        clips_escena = list(clips_por_escena[i]) if i < len(clips_por_escena) else []
        random.shuffle(clips_escena)

        if i < len(imagenes_ia) and imagenes_ia:
            try:
                dur = min(4.0, limite_tramo - tiempo_acumulado)
                if dur > 0.1:
                    clips_finales.append(ImageClip(imagenes_ia[i]).set_duration(dur))
                    tiempo_acumulado += dur
            except Exception:
                pass

        puntero = 0
        while tiempo_acumulado < limite_tramo and puntero < len(clips_escena):
            c = _preparar_clip(clips_escena[puntero], limite_tramo - tiempo_acumulado)
            puntero += 1
            if c is None:
                continue
            clips_finales.append(c)
            tiempo_acumulado += c.duration

        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, limite_tramo, pool_generico
        )

        if tiempo_acumulado < limite_tramo - 0.1 and imagenes_ia:
            try:
                c = ImageClip(imagenes_ia[i % len(imagenes_ia)]).set_duration(
                    limite_tramo - tiempo_acumulado
                )
                clips_finales.append(c)
                tiempo_acumulado = limite_tramo
            except Exception:
                pass

    if tiempo_acumulado < duracion_total - 0.1:
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, duracion_total, pool_generico
        )

    if not clips_finales:
        raise RuntimeError("No se pudo armar ningun clip")

    video_base = concatenate_videoclips(clips_finales, method="compose")
    video_base = video_base.set_duration(duracion_total)

    audios = [audio_voz]
    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            if musica.duration < duracion_total:
                import math
                musica = concatenate_audioclips(
                    [musica] * math.ceil(duracion_total / musica.duration)
                )
            audios.append(musica.subclip(0, duracion_total).volumex(0.10))
        except Exception as e:
            print(f"Aviso musica: {e}")

    video_base = video_base.set_audio(CompositeAudioClip(audios))

    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        dur_palabra = (seg["end"] - seg["start"]) / max(len(palabras), 1)
        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + j * dur_palabra
            t_fin = t_inicio + dur_palabra

            subtitulos.append(TextClip(
                palabra.upper(), fontsize=65, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 2, int(RESOLUCION[1] * 0.85) + 2), True
            ))
            subtitulos.append(TextClip(
                palabra.upper(), fontsize=65, color="white",
                font="DejaVu-Sans-Bold", stroke_color="#00C853", stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.85), relative=True
            ))

    subtitulos.append(TextClip(
        hook_texto.upper(), fontsize=52, color="white",
        font="DejaVu-Sans-Bold", stroke_color="#FFD700", stroke_width=3,
        size=(RESOLUCION[0]-200, None), method="caption"
    ).set_start(0).set_end(min(3.0, duracion_total)).set_position(
        ("center", 0.35), relative=True
    ))

    final = CompositeVideoClip([video_base, *subtitulos]).set_duration(duracion_total)
    final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=4, preset="ultrafast", bitrate="4000k"
    )
    return salida


def subir_youtube(video_path, titulo, descripcion, tags, thumbnail_path=None):
    creds = Credentials(
        token=None, refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID, client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": titulo[:100],
                "description": descripcion[:5000],
                "tags": tags,
                "categoryId": "27",  # Education
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    response = request.execute()
    video_id = response.get("id")
    print("Subido:", video_id)

    if thumbnail_path and video_id and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            ).execute()
            print(f"Thumbnail subido para {video_id}")
        except Exception as e:
            print(f"Aviso thumbnail: {e}")


def main():
    print("WealthSnap - Pipeline Longform Finanzas")
    contenido, formato = generar_contenido()
    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes(escenas)

    musica_url = random.choice(MUSICA_FINANCE)
    musica_path = "musica_finance_long.mp3"
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
    clips_por_escena, pool_generico = descargar_clips(escenas, formato)

    hook_texto = contenido.get("hook", "Most people never figure this out about money.")

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia,
        audio_path, segmentos, hook_texto, musica_path
    )

    titulo = contenido.get("titulo", "The Money Secret That Changes Everything 💰")
    capitulos = contenido.get("capitulos", "")
    tags = list(dict.fromkeys(
        contenido.get("tags", []) + [
            "finance", "personalfinance", "money", "investing", "wealth",
            "financialfreedom", "budgeting", "savemoney", "moneytips",
            "wealthbuilding", "financeeducation", "moneymanagement",
        ]
    ))

    HASHTAGS = ["#finance", "#personalfinance", "#money", "#investing",
                "#wealth", "#financialfreedom", "#moneytips", "#wealthsnap"]
    descripcion = (
        f"{contenido['guion'][:600]}...\n\n"
        f"💰 Subscribe to WealthSnap for daily money tips.\n\n"
        f"--- CHAPTERS ---\n{capitulos}\n\n"
        f"{' '.join(HASHTAGS)}"
    )

    imagen_thumb = imagenes_ia[0] if imagenes_ia else None
    thumbnail_path = generar_thumbnail(titulo, imagen_thumb)

    subir_youtube(video_path, titulo, descripcion, tags, thumbnail_path)


if __name__ == "__main__":
    main()
