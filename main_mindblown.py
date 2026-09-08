"""
MindBlown - Pipeline Top 10 Viral Moments - Version 1.2

Top 10 de datos, records y comparaciones extremas.
Todo con material libre de derechos de Pexels.
Sin copyright, alta viralidad, formato entretenido.
"""
import os
import io
import re
import time
import random
import requests
import asyncio
import json
import base64
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

RESOLUCION = (1080, 1920)
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

DURACION_HOOK = 1.8
CLIP_MIN, CLIP_MAX = 1.2, 2.5

NEGATIVE_PROMPT = (
    "deformed hands, extra fingers, mutated, blurry, watermark, text, "
    "logo, disfigured face, low quality, low resolution, duplicate"
)

VOCES = [
    "en-US-AndrewNeural",
    "en-US-GuyNeural",
    "en-GB-RyanNeural",
    "en-AU-WilliamNeural",
    "en-US-ChristopherNeural",
    "en-GB-ThomasNeural",
    "en-US-JennyNeural",
    "en-GB-SoniaNeural",
]

MUSICA = [
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_5bbc9a1a1c.mp3",
    "https://cdn.pixabay.com/download/audio/2021/08/09/audio_99bbbd8a4c.mp3",
]

CATEGORIAS = {
    "mind_blowing_facts": {
        "peso": 3,
        "tags_extra": ["didyouknow", "sciencefacts", "spacefacts", "oceanfacts",
                        "historyfacts", "bodyfacts", "randomfacts", "factsdaily"],
        "temas": [
            "facts about Earth that sound fake but are true",
            "space facts so extreme they sound fake but are true",
            "facts about the ocean that sound fake but are true",
            "history facts so wild they sound like fiction",
            "science facts that sound fake but are 100% true",
            "facts about the human body that sound fake but are true",
            "facts about time and the universe that break your brain",
        ],
        "consultas_broll": [
            "space galaxy stars universe", "deep ocean underwater",
            "earth aerial view planet", "science laboratory",
            "ancient ruins historical", "microscope cells science",
            "volcano aerial dramatic", "coral reef underwater",
            "northern lights aurora", "desert aerial drone",
            "glacier ice melting", "rainforest aerial",
        ],
        "color_sub": "#9B59B6",
        "emoji_titulo": "😱",
    },
    "animal_superpowers": {
        "peso": 3,
        "tags_extra": ["animalfacts", "wildlife", "animals", "nature",
                        "rareanimals", "animalkingdom", "wildanimals", "biology"],
        "temas": [
            "animal facts that sound fake but are true",
            "animal abilities that sound made up but are real",
            "the rarest animals on Earth and why they exist",
            "animal survival abilities that sound fake but are true",
            "the most intelligent animals and what they can really do",
            "animal senses that sound impossible but are real",
            "animals with real abilities that seem like superpowers",
        ],
        "consultas_broll": [
            "eagle hunting prey slow motion", "whale breaching ocean",
            "cheetah running fast", "octopus underwater",
            "lion hunting wildlife", "dolphin jumping ocean",
            "bear catching fish river", "wolves running pack",
            "shark underwater dramatic", "bird of prey diving",
            "elephant herd wildlife", "gorilla wildlife close up",
        ],
        "color_sub": "#FF8C00",
        "emoji_titulo": "🦁",
    },
    "human_achievements": {
        "peso": 3,
        "tags_extra": ["worldrecords", "engineering", "architecture", "records",
                        "extremesports", "humanachievements", "construction", "megastructures"],
        "temas": [
            "man-made structures that defy logic",
            "structures that seem physically impossible but exist",
            "world records that sound fake but are true",
            "engineering achievements that defy logic",
            "the most extreme structures humans have ever built",
            "human achievements that sound fake but are true",
            "records that seem impossible but were actually broken",
        ],
        "consultas_broll": [
            "extreme sports athlete", "skydiving aerial view",
            "mountain climbing extreme", "motorcycle stunt",
            "construction crane building", "bridge engineering",
            "rocket launch space", "athlete breaking record",
            "parkour urban extreme", "base jumping cliff",
            "swimming competition", "gymnastics athlete",
        ],
        "color_sub": "#FFD700",
        "emoji_titulo": "🏆",
    },
    "natural_phenomena": {
        "peso": 1,
        "tags_extra": ["naturephenomena", "extremeweather", "earthfacts",
                        "naturedocumentary", "weatherfacts", "planetearth"],
        "temas": [
            "natural phenomena that sound fake but are real",
            "extreme weather events that sound fake but are true",
            "places on Earth that sound fake but are real",
            "natural events so rare they sound made up",
        ],
        "consultas_broll": [
            "extreme weather lightning storm", "tornado funnel cloud dramatic",
            "volcanic eruption lava", "aurora borealis night sky",
            "giant wave ocean storm", "earthquake destruction dramatic",
            "meteor shower night sky", "flood river overflow",
            "ice storm frozen tree", "desert sand storm",
            "waterspout ocean tornado", "hailstorm dramatic",
        ],
        "color_sub": "#00BFFF",
        "emoji_titulo": "🤯",
    },
    "extreme_comparisons": {
        "peso": 1,
        "tags_extra": ["comparison", "vs", "extremes", "sidebyside",
                        "worldfacts", "geography", "didyouknowfacts"],
        "temas": [
            "extreme comparisons that sound fake but are true",
            "the richest vs the poorest places on Earth",
            "the fastest vs the slowest things in nature",
            "extremes in the animal kingdom that sound made up",
        ],
        "consultas_broll": [
            "desert extreme heat", "arctic ice landscape",
            "skyscraper city aerial", "rural village aerial",
            "cheetah running fast", "sloth slow motion",
            "whale ocean giant", "hummingbird tiny fast",
            "ancient ruins historical", "modern city futuristic",
            "volcano aerial dramatic", "glacier ice melting",
        ],
        "color_sub": "#FF4444",
        "emoji_titulo": "🔥",
    },
}

CONSULTAS_RESPALDO = [
    "dramatic nature cinematic", "slow motion water",
    "aerial drone landscape", "extreme weather dramatic",
]

# Formatos variables para dar mas ritmo y evitar que todo se sienta igual.
# Top 5 pesa mas porque suele retener mejor en Shorts (video mas corto y rapido).
FORMATOS = [
    {"nombre": "Top 3", "inicio": 3, "palabras": "35-50", "peso": 2},
    {"nombre": "Top 5", "inicio": 5, "palabras": "55-75", "peso": 4},
    {"nombre": "Top 10", "inicio": 10, "palabras": "100-130", "peso": 2},
]


def elegir_formato() -> dict:
    pesos = [f["peso"] for f in FORMATOS]
    return random.choices(FORMATOS, weights=pesos, k=1)[0]


PROMPT_SISTEMA = """You are a viral YouTube Shorts narrator for MindBlown channel.
You create fast-paced {formato_nombre} countdowns about mind-blowing facts, extreme records, and incredible comparisons.
Your proven winning formula is the "sounds fake but is true" / "defies logic" angle —
this style has consistently gotten the most views on this channel.
Your style is like a fast-paced trivia narrator — calm but enthusiastic, with genuine amazement.

Create a {formato_nombre} countdown about: {tema}

HOOK RULES (most critical — determines 70-90% of views):
- Under 8 words
- Vary naturally between these proven patterns — do NOT repeat the exact same
  wording every time, pick whichever fits the specific facts best:
  * SOUNDS FAKE: "This sounds fake but it's 100% real."
  * IMPOSSIBILITY: "This should not be scientifically possible."
  * SHOCK: "Number 1 will break your brain."
  * CURIOSITY: "Scientists still cannot fully explain number 3."
  * CHALLENGE: "Bet you didn't know number 1."
- Must stop someone mid-scroll instantly

COUNTDOWN RULES:
- Start with hook IMMEDIATELY — no intro, no filler
- Number from {formato_inicio} down to 1
- Each entry: 1-2 punchy sentences with ONE specific, verifiable, mind-blowing detail
- Build amazement progressively — each entry more incredible than the last
- Near the middle, add ONE short line of tension like "but wait, it gets crazier..."
- #1: the most jaw-dropping, unbelievable entry — must deliver on the hype
- Keep it PG — no violence, no gore, family-friendly amazement
- END the script with a short direct challenge to the viewer, for example:
  "Comment which number surprised you the most." or
  "Bet you only knew 2 of these — tell me which ones."
  This closing line is separate from the countdown entries and should
  feel natural, not forced.
- Never claim "caught on camera" or "recorded live" — frame everything as
  facts, records, and things that exist or are true, not footage of an event.

TITLE RULES:
- Under 40 characters (mobile truncates longer)
- Start with "{formato_nombre}" (e.g. "{formato_nombre} Facts You Won't Believe")
- Vary the wording naturally — "Sound(s) Fake", "Defies Logic", "Will Shock You",
  "Nobody Believes" are all good options, but do not repeat the exact same
  phrase in every single title
- Add {emoji} and #Shorts at end

3 filmable scene descriptions for Pexels search (nature, science, animals, structures — generic and illustrative)

Also provide a short "miniatura" line: 3-5 words in ALL CAPS summarizing the single
most shocking fact from the whole list (used as bold text on the video thumbnail,
separate from the hook and title).

STRICT: {formato_palabras} words ENGLISH ONLY for the countdown, plus a short viewer-challenge closing line. Every word earns its place.

Return ONLY valid JSON, no markdown, no backticks:
{{
"hook": "...(under 8 words, stops scroll instantly)...",
"guion": "...({formato_palabras} words STRICT countdown {formato_inicio} to 1, plus a short viewer-challenge closing line)...",
"escenas": ["pexels search phrase 1", "pexels search phrase 2", "pexels search phrase 3"],
"titulo": "...(under 40 chars, starts with {formato_nombre} + {emoji} + #Shorts)...",
"miniatura": "...(3-5 words ALL CAPS, the single most shocking fact)...",
"tags": ["mindblown", "{formato_tag}", "viral", "shorts", "facts", "soundsfake", "science", "wow", "trivia", "mindblowing"]
}}"""


def generar_contenido() -> tuple:
    claves = list(CATEGORIAS.keys())
    pesos = [CATEGORIAS[k]["peso"] for k in claves]
    categoria_key = random.choices(claves, weights=pesos, k=1)[0]
    categoria = CATEGORIAS[categoria_key]
    tema = random.choice(categoria["temas"])
    emoji = categoria["emoji_titulo"]
    formato = elegir_formato()
    print(f"Formato: {formato['nombre']}")

    prompt = PROMPT_SISTEMA.format(
        tema=tema, emoji=emoji,
        formato_nombre=formato["nombre"],
        formato_inicio=formato["inicio"],
        formato_palabras=formato["palabras"],
        formato_tag=formato["nombre"].lower().replace(" ", ""),
    )
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
                contenido = json.loads(texto)
                print(f"Categoria: {categoria_key} | Tema: {tema}")
                print(f"Hook: {contenido.get('hook', '')}")
                return contenido, categoria
            except Exception as e:
                print(f"Error {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_mindblown") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": (
            f"cinematic, dramatic, high quality, 4k, "
            f"photorealistic, stunning visual: {prompt}"
        ),
        "parameters": {
            "width": 768, "height": 1344,
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


def generar_imagenes(escenas: list, categoria: dict) -> list:
    return [
        ruta for i, escena in enumerate(escenas[:3])
        if (ruta := generar_imagen_ia(
            f"{escena}, cinematic dramatic", i
        ))
    ]


def generar_miniatura(imagen_base: str, texto: str, color_sub: str,
                       destino: str = "miniatura_mindblown.jpg") -> str:
    try:
        img = Image.open(imagen_base).convert("RGB")
        img = img.resize((720, 1280))
        lienzo = Image.new("RGB", (1280, 720), (0, 0, 0))
        x_offset = (1280 - 720) // 2
        lienzo.paste(img, (x_offset, 0))

        overlay = Image.new("RGBA", lienzo.size, (0, 0, 0, 110))
        lienzo = Image.alpha_composite(lienzo.convert("RGBA"), overlay).convert("RGB")

        draw = ImageDraw.Draw(lienzo)
        try:
            fuente = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80
            )
        except Exception:
            fuente = ImageFont.load_default()

        texto = texto.upper()
        palabras = texto.split()
        lineas, linea_actual = [], ""
        for palabra in palabras:
            prueba = f"{linea_actual} {palabra}".strip()
            bbox = draw.textbbox((0, 0), prueba, font=fuente)
            if bbox[2] - bbox[0] > 1100 and linea_actual:
                lineas.append(linea_actual)
                linea_actual = palabra
            else:
                linea_actual = prueba
        if linea_actual:
            lineas.append(linea_actual)

        alto_total = len(lineas) * 95
        y = (720 - alto_total) // 2
        for linea in lineas:
            bbox = draw.textbbox((0, 0), linea, font=fuente)
            ancho = bbox[2] - bbox[0]
            x = (1280 - ancho) // 2
            for dx, dy in [(-3,-3),(-3,3),(3,-3),(3,3),(0,0)]:
                color = color_sub if (dx, dy) == (0, 0) else "black"
                draw.text((x+dx, y+dy), linea, font=fuente, fill=color)
            y += 95

        lienzo.save(destino, quality=92)
        return destino
    except Exception as e:
        print(f"Aviso miniatura: {e}")
        return None


def descargar_musica() -> str:
    url = random.choice(MUSICA)
    destino = "musica_mindblown.mp3"
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


async def _tts(texto: str, salida: str, voz: str):
    await edge_tts.Communicate(texto, voz).save(salida)


def generar_audio(texto: str, salida: str = "audio_mindblown.mp3"):
    voz = random.choice(VOCES)
    print(f"Voz: {voz}")
    asyncio.run(_tts(texto, salida, voz))
    return salida


def transcribir(audio_path: str):
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path, language="en")["segments"]
    del modelo
    import gc
    gc.collect()
    return resultado


def _buscar_clips(consulta, headers, carpeta, indice, por_consulta=12):
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
            enlace = archivos[len(archivos)//2]["link"]
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


def descargar_clips(escenas, categoria, carpeta="clips_mindblown"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    indice = 0
    clips_por_escena = []
    for escena in escenas:
        rutas, indice = _buscar_clips(escena, headers, carpeta, indice, 12)
        clips_por_escena.append(rutas)
    pool_generico = []
    for consulta in categoria["consultas_broll"]:
        rutas, indice = _buscar_clips(consulta, headers, carpeta, indice, 12)
        pool_generico.extend(rutas)
    total = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    if total < 40:
        for consulta in CONSULTAS_RESPALDO:
            extra, indice = _buscar_clips(consulta, headers, carpeta, indice, 12)
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
    dur_clip = min(c.duration, dur_max, random.uniform(CLIP_MIN, CLIP_MAX))
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
                 segmentos, hook_texto, musica_path, categoria,
                 salida="video_mindblown.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    duracion_video = duracion_total + DURACION_HOOK
    color_sub = categoria["color_sub"]

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
                dur = min(2.5, limite_tramo - tiempo_acumulado)
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
    video_base = video_base.set_duration(duracion_video)

    audio_voz_delayed = audio_voz.set_start(DURACION_HOOK)
    audios = [audio_voz_delayed]
    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            if musica.duration < duracion_video:
                import math
                musica = concatenate_audioclips(
                    [musica] * math.ceil(duracion_video / musica.duration)
                )
            audios.append(musica.subclip(0, duracion_video).volumex(0.15))
        except Exception as e:
            print(f"Aviso musica: {e}")

    video_base = video_base.set_audio(CompositeAudioClip(audios))

    subtitulos = []

    import numpy as np
    overlay = (
        ImageClip(np.zeros((RESOLUCION[1], RESOLUCION[0], 3), dtype=np.uint8))
        .set_opacity(0.55)
        .set_start(0)
        .set_end(DURACION_HOOK)
    )

    hook_clip = TextClip(
        hook_texto.upper(),
        fontsize=78, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=4,
        size=(RESOLUCION[0]-80, None), method="caption"
    ).set_start(0).set_end(DURACION_HOOK).set_position("center")
    subtitulos.append(hook_clip)

    badge = TextClip(
        "🔥 MINDBLOWN", fontsize=45, color=color_sub,
        font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
    ).set_start(0).set_end(DURACION_HOOK).set_position(("center", 0.22), relative=True)
    subtitulos.append(badge)

    PALABRAS_CLAVE = {
        "impossible", "never", "ever", "first", "only", "record",
        "insane", "incredible", "unbelievable", "shocking", "mind-blowing",
        "fastest", "biggest", "smallest", "rarest", "deadliest",
        "survived", "discovered", "comment", "fake", "logic",
    }

    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        dur_palabra = (seg["end"] - seg["start"]) / max(len(palabras), 1)
        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + DURACION_HOOK + j * dur_palabra
            t_fin = t_inicio + dur_palabra

            es_numero = any(n in palabra for n in
                           ["10","9","8","7","6","5","4","3","2","1"])
            es_clave = palabra.lower().strip(".,!?") in PALABRAS_CLAVE
            color = "#FFD700" if es_numero else (color_sub if es_clave else "white")
            tam = 95 if es_clave or es_numero else 88

            subtitulos.append(TextClip(
                palabra.upper(), fontsize=tam, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=4,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 3, int(RESOLUCION[1] * 0.72) + 3), True
            ))
            subtitulos.append(TextClip(
                palabra.upper(), fontsize=tam, color=color,
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.72), relative=True
            ))

    dur_cta = min(3.0, duracion_video)
    t_inicio_cta = duracion_video - dur_cta
    cta_clip = TextClip(
        "SUSCRÍBETE PARA MÁS 🔔",
        fontsize=70, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=4,
        size=(RESOLUCION[0]-100, None), method="caption"
    ).set_start(t_inicio_cta).set_end(duracion_video).set_position(
        ("center", 0.15), relative=True
    )
    subtitulos.append(cta_clip)

    final = CompositeVideoClip(
        [video_base, overlay, *subtitulos]
    ).set_duration(duracion_video)

    final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=2, preset="medium", bitrate="8000k"
    )
    return salida


def leer_contador() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or not token:
        return 1
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/contents/contador.txt",
            headers={"Authorization": f"token {token}"}, timeout=15
        )
        if r.status_code == 200:
            contenido = base64.b64decode(r.json()["content"]).decode().strip()
            return int(contenido)
    except Exception as e:
        print(f"Aviso contador (lectura): {e}")
    return 1


def actualizar_contador(numero: int):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or not token:
        return
    try:
        url = f"https://api.github.com/repos/{repo}/contents/contador.txt"
        headers = {"Authorization": f"token {token}"}
        r = requests.get(url, headers=headers, timeout=15)
        sha = r.json().get("sha") if r.status_code == 200 else None
        contenido_b64 = base64.b64encode(str(numero).encode()).decode()
        body = {"message": f"Actualizar contador a {numero}", "content": contenido_b64}
        if sha:
            body["sha"] = sha
        requests.put(url, headers=headers, json=body, timeout=15)
    except Exception as e:
        print(f"Aviso contador (escritura): {e}")


def subir_youtube(video_path, titulo, descripcion, tags, miniatura_path=None):
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
                "categoryId": "24",
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    respuesta = request.execute()
    video_id = respuesta.get("id")
    print("Subido:", video_id)

    if miniatura_path and video_id:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(miniatura_path)
            ).execute()
            print("Miniatura personalizada aplicada")
        except Exception as e:
            print(f"Aviso miniatura (no se pudo subir): {e}")

    return video_id


def main():
    print("MindBlown - Pipeline Top 10 Viral Moments")
    episodio = leer_contador()
    print(f"Episodio numero: {episodio}")

    contenido, categoria = generar_contenido()
    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes(escenas, categoria)
    clips_por_escena, pool_generico = descargar_clips(escenas, categoria)
    musica_path = descargar_musica()
    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    hook_texto = contenido.get("hook", "This sounds fake but it's real.")

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia,
        audio_path, segmentos, hook_texto, musica_path, categoria
    )

    miniatura_path = None
    texto_miniatura = contenido.get("miniatura", "")
    if texto_miniatura and imagenes_ia:
        miniatura_path = generar_miniatura(
            imagenes_ia[0], texto_miniatura, categoria["color_sub"]
        )

    titulo_base = contenido.get("titulo", "10 Facts That Sound Fake 😱 #Shorts")
    titulo = f"#{episodio} {titulo_base}"[:100]

    # Hashtags VISIBLES en la descripcion: YouTube solo usa los primeros 3 para
    # clasificar el Short, y un exceso de hashtags visibles en cada video puede
    # leerse como spam. Los dejamos moderados (5) y variamos el orden.
    HASHTAGS_BASE = ["#shorts", "#mindblown", "#facts"]
    HASHTAGS_EXTRA = ["#soundsfake", "#viral", "#didyouknow", "#wow", "#incredible"]
    hashtags_finales = HASHTAGS_BASE + random.sample(HASHTAGS_EXTRA, 2)

    # Campo "tags" (metadata, NO visible al espectador): aqui SI conviene ser
    # generoso y especifico, hasta el limite de 500 caracteres que exige YouTube.
    tags_categoria = categoria.get("tags_extra", [])
    tags_combinados = list(dict.fromkeys(
        contenido.get("tags", []) + tags_categoria + [
            "mindblown", "top10", "top5", "viral", "shorts", "facts",
            "soundsfake", "incredible", "science", "amazing",
            "wow", "satisfying", "nature", "records", "comparison",
            "didyouknow", "mindblowingfacts", "trivia", "factchecked",
        ]
    ))
    tags = []
    largo_actual = 0
    for t in tags_combinados:
        if largo_actual + len(t) + 1 > 480:
            break
        tags.append(t)
        largo_actual += len(t) + 1

    descripcion = (
        f"MindBlown #{episodio}\n\n"
        f"{contenido['guion']}\n\n"
        f"🔥 Subscribe to MindBlown for daily mind-blowing facts.\n\n"
        f"{' '.join(hashtags_finales)}"
    )
    subir_youtube(video_path, titulo, descripcion, tags, miniatura_path)
    actualizar_contador(episodio + 1)


if __name__ == "__main__":
    main()
