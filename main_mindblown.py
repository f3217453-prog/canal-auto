"""
MindBlown - Pipeline Top 10 Viral Moments - Version 1.1

Top 10 de datos increibles, comparaciones sorprendentes, records,
fenomenos naturales, animales, etc.
Todo con material libre de derechos de Pexels.
Sin copyright, alta viralidad, formato entretenido.

Referencia: Daily Dose of Internet (20M subs, $140K-$400K/mes)

CAMBIOS v1.1:
- Prompt reenfocado de "momentos captados en camara" a "datos e
  informacion verificable" para que el video de stock no choque con
  lo que promete el hook (evita rechazo/reportes de clickbait).
- Nueva categoria de comparaciones/contraste (X vs Y).
- Cierre de "reto al espectador" en todos los guiones para subir
  comentarios y shares.
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

RESOLUCION = (1080, 1920)
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MODELOS_GEMINI = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

NEGATIVE_PROMPT = (
    "deformed hands, extra fingers, mutated, blurry, watermark, text, "
    "logo, disfigured face, low quality, low resolution, duplicate"
)

# Voces variadas - energeticas y entusiastas para contenido viral
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

# Categorias que alternan para dar variedad al canal.
# Reenfocadas hacia informacion/datos verificables (no "esto paso en
# camara") para que el material de stock de Pexels nunca contradiga
# lo que promete el hook.
CATEGORIAS = {
    "mind_blowing_facts": {
        "temas": [
            "facts about Earth that will make you see the planet differently",
            "space facts so extreme they are almost impossible to believe",
            "things about the ocean that will terrify and amaze you",
            "history facts so wild they sound like fiction",
            "science discoveries that changed everything we knew",
            "facts about the human body that will blow your mind",
            "things about time and the universe that break your brain",
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
    "natural_phenomena": {
        "temas": [
            "natural phenomena so extreme scientists still study them",
            "the most powerful natural forces on planet Earth",
            "rare weather events that happen once in a lifetime",
            "geological wonders that took millions of years to form",
            "natural events so massive they can be seen from space",
            "the most extreme places that actually exist on Earth",
        ],
        "consultas_broll": [
            "extreme weather lightning storm", "tornado funnel cloud dramatic",
            "volcanic eruption lava", "aurora borealis night sky",
            "giant wave ocean storm", "meteor shower night sky",
            "ice storm frozen tree", "desert sand storm",
            "waterspout ocean tornado", "hailstorm dramatic",
        ],
        "color_sub": "#00BFFF",
        "emoji_titulo": "🌪️",
    },
    "animal_facts": {
        "temas": [
            "animal abilities that sound like actual superpowers",
            "the most surprising things science discovered about animals",
            "the rarest animals that actually exist on Earth",
            "animal survival tricks evolution took millions of years to build",
            "the most intelligent animal behaviors ever studied",
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
        "temas": [
            "the most insane world records ever broken",
            "things humans built that seem physically impossible",
            "engineering achievements that changed the world forever",
            "the most extreme sports records ever set",
            "human body records that push the limits of biology",
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
    "extreme_comparisons": {
        "temas": [
            "the fastest vs the slowest animals on Earth compared",
            "the richest vs the poorest countries and what separates them",
            "the biggest vs the smallest structures humans ever built",
            "the hottest vs the coldest places humans actually live",
            "the deepest vs the highest points on planet Earth",
            "ancient technology vs modern technology and the gap between them",
        ],
        "consultas_broll": [
            "cheetah running fast", "desert aerial drone",
            "city skyline aerial night", "rural village aerial",
            "mountain peak snow aerial", "ocean trench deep blue",
            "skyscraper aerial view", "ancient architecture ruins",
            "modern technology factory", "arctic ice landscape",
            "tropical landscape aerial", "urban aerial drone",
        ],
        "color_sub": "#FF4444",
        "emoji_titulo": "⚖️",
    },
}

CONSULTAS_RESPALDO = [
    "dramatic nature cinematic", "slow motion water",
    "aerial drone landscape", "extreme weather dramatic",
]

PROMPT_SISTEMA = """You are a viral YouTube Shorts narrator for MindBlown channel.
You create top 10 countdowns about mind-blowing, real, verifiable facts and comparisons.
Your style is like Daily Dose of Internet — calm but enthusiastic, with genuine amazement.
Reference channel: 20 million subscribers. Formula: simple narration + incredible visuals.

Create a top 10 countdown about: {tema}

CRITICAL RULE: Every entry must be a real, verifiable FACT or COMPARISON —
never claim something was "caught on camera" or "filmed" or "happened".
Frame everything as information/knowledge, not as a captured moment.
Good: "This animal can survive being frozen solid." 
Bad: "Watch what this animal did on camera."

HOOK RULES (most critical — determines 70-90% of views):
- Under 8 words
- Must use ONE of these proven viral patterns:
  * DISBELIEF: "This fact sounds fake but it's real."
  * SHOCK: "Number 1 on this list will change how you think."
  * CURIOSITY: "Scientists still cannot fully explain number 3."
  * CHALLENGE: "Bet you don't know number 1 on this list."
- Must stop someone mid-scroll instantly

COUNTDOWN RULES:
- Start with hook IMMEDIATELY — no intro, no filler
- Number from 10 down to 1
- Each entry: 1-2 punchy sentences with ONE specific verifiable fact or number
- Build amazement progressively — each entry more incredible than the last
- At #5: "but what's coming at number 1 will genuinely shock you..."
- #1: the most jaw-dropping, unbelievable fact — must deliver on the hype
- End with a direct challenge to the viewer, asking which fact they
  already knew or which one surprised them most — this drives comments
- Keep it PG — no violence, no gore, family-friendly amazement

TITLE RULES:
- Under 40 characters (mobile truncates longer)
- Must create immediate curiosity or promise something unbelievable
- Examples: "Top 10 Facts That Sound Fake" / "Top 10 Things Science Can't Explain"
- Add {emoji} and #Shorts at end

3 filmable scene descriptions for Pexels search (nature, sports, animals, phenomena,
landscapes — never people performing a specific filmed "moment")

STRICT: 100-120 words ENGLISH ONLY. Every word earns its place.

Return ONLY valid JSON, no markdown, no backticks:
{{
"hook": "...(under 8 words, stops scroll instantly)...",
"guion": "...(100-120 words STRICT, countdown 10 to 1, ends with a challenge to comment)...",
"escenas": ["pexels search phrase 1", "pexels search phrase 2", "pexels search phrase 3"],
"titulo": "...(under 40 chars + {emoji} + #Shorts)...",
"tags": ["mindblown", "top10", "viral", "shorts", "facts", "didyouknow", "incredible", "science", "amazing", "wow"]
}}"""


def generar_contenido() -> tuple:
    categoria_key = random.choice(list(CATEGORIAS.keys()))
    categoria = CATEGORIAS[categoria_key]
    tema = random.choice(categoria["temas"])
    emoji = categoria["emoji_titulo"]

    prompt = PROMPT_SISTEMA.format(tema=tema, emoji=emoji)
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
    dur_clip = min(c.duration, dur_max, random.uniform(2.0, 4.0))
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
    duracion_video = duracion_total + 2.5  # 2.5s de hook visual al inicio
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

    # Narracion empieza a los 2.5s, despues del hook visual
    audio_voz_delayed = audio_voz.set_start(2.5)
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

    # Hook visual: texto grande centrado sobre overlay oscuro (primeros 2.5s)
    import numpy as np
    overlay = (
        ImageClip(np.zeros((RESOLUCION[1], RESOLUCION[0], 3), dtype=np.uint8))
        .set_opacity(0.6)
        .set_start(0)
        .set_end(2.5)
    )

    hook_clip = TextClip(
        hook_texto.upper(),
        fontsize=78, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=4,
        size=(RESOLUCION[0]-80, None), method="caption"
    ).set_start(0).set_end(2.5).set_position("center")
    subtitulos.append(hook_clip)

    # Badge MindBlown en el hook
    badge = TextClip(
        "🔥 MINDBLOWN", fontsize=45, color=color_sub,
        font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
    ).set_start(0).set_end(2.5).set_position(("center", 0.22), relative=True)
    subtitulos.append(badge)

    # Subtitulos palabra por palabra desde los 2.5s
    PALABRAS_CLAVE = {
        "impossible", "never", "ever", "first", "only", "record",
        "insane", "incredible", "unbelievable", "shocking", "mind-blowing",
        "fastest", "biggest", "smallest", "rarest", "deadliest",
        "discovered", "proven", "real", "fact", "facts",
    }

    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        dur_palabra = (seg["end"] - seg["start"]) / max(len(palabras), 1)
        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + 2.5 + j * dur_palabra
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

    final = CompositeVideoClip(
        [video_base, overlay, *subtitulos]
    ).set_duration(duracion_video)

    final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=2, preset="medium", bitrate="8000k"
    )
    return salida


def subir_youtube(video_path, titulo, descripcion, tags):
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
                "categoryId": "24",  # Entertainment
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    print("Subido:", request.execute().get("id"))


def main():
    print("MindBlown - Pipeline Top 10 Viral Moments")
    contenido, categoria = generar_contenido()
    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes(escenas, categoria)
    clips_por_escena, pool_generico = descargar_clips(escenas, categoria)
    musica_path = descargar_musica()
    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    hook_texto = contenido.get("hook", "This fact sounds fake but it's real.")

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia,
        audio_path, segmentos, hook_texto, musica_path, categoria
    )

    titulo = contenido.get("titulo", "Top 10 Facts That Sound Fake 🤯 #Shorts")
    HASHTAGS = ["#shorts", "#top10", "#viral", "#mindblown", "#facts",
                "#didyouknow", "#incredible", "#science", "#amazing", "#wow"]
    tags = list(dict.fromkeys(
        contenido.get("tags", []) + [
            "mindblown", "top10", "viral", "shorts", "facts",
            "didyouknow", "incredible", "science", "amazing",
            "wow", "satisfying", "nature", "records", "comparison",
        ]
    ))
    descripcion = (
        f"{contenido['guion']}\n\n"
        f"🔥 Subscribe to MindBlown for daily mind-blowing facts.\n\n"
        f"{' '.join(HASHTAGS)}"
    )
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
