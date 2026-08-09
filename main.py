"""
Pipeline mejorado para Shorts - Version 4.0

Cambios respecto a v3.0:
- Nicho fijado a "horror" (consistencia de canal)
- Guion mas corto (90-130 palabras / ~35-50s) para acercarse a la ventana
  de mejor retencion en Shorts (dato 2026: 68% de las vistas de Shorts
  vienen de videos <25s; el umbral de empuje algoritmico es ~65% de
  retencion en shorts <30s)
- Sin pantalla de intro estatica: el hook se superpone como texto sobre
  el primer clip de video real, audio empieza en el segundo 0
- Clips de b-roll emparejados por escena narrativa (no solo aleatorios)
- Prompts de imagen IA con mayor consistencia de personaje + negative prompt
- Mas variedad de clips descargados, menos repeticion dentro del mismo video
- Render con mejor calidad (preset + bitrate)
- Whisper "base" en vez de "tiny" para subtitulos mas precisos
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

NEGATIVE_PROMPT = (
    "deformed hands, extra fingers, mutated, blurry, watermark, text, "
    "logo, disfigured face, low quality, low resolution, duplicate"
)

MUSICA_AMBIENTE = {
    "horror": [
        "https://cdn.pixabay.com/download/audio/2022/03/10/audio_270f4b1fbe.mp3",
        "https://cdn.pixabay.com/download/audio/2021/09/06/audio_dad6b6ef7f.mp3",
    ],
}

NICHOS = {
    "horror": {
        "prompt_sistema": """You are a viral horror YouTube Shorts writer with 10 million subscribers.
You know exactly what makes people stop scrolling and watch to the end.

Create a horror story script with:
1. A main character (name, age, physical description, personality, clothing — specific enough to keep visually consistent across AI images)
2. A specific terrifying location (concrete details)
3. Narrative arc: devastating hook → building dread → shocking twist → chilling ending that lingers
4. 3 vivid scene descriptions for AI image generation (5-8 words each, filmable and concrete)
5. A hook line: THE most important element. Must be under 10 words. Must create an immediate question or dread in the viewer's mind. Examples of great hooks: "She heard her own voice on the answering machine." / "The babysitter found a third child in the house." / "His obituary was published before he died."

TITLE RULES (critical for clicks):
- Include a number or specific detail ("The 3AM Phone Call", "Found in Room 13")
- Include 1 power word: haunted / cursed / forbidden / disappeared / survived / never found
- End with 😱 or 👁️ or ☠️
- Add #Shorts #Horror at the very end of the title string (these appear above the video)
- Example: "She Survived Room 13... But Something Followed Her Home 😱 #Shorts #Horror"

GUION RULES: 90-130 words STRICT in ENGLISH. Every sentence must earn its place.
Start with the hook. Build tension. End on a cliffhanger or revelation that makes people comment.

Return ONLY valid JSON, no markdown, no backticks:
{
"personaje": {"nombre": "...", "descripcion": "...", "personalidad": "..."},
"lugar": {"nombre": "...", "descripcion": "..."},
"hook": "...(under 10 words, creates immediate dread or question)...",
"guion": "...(90-130 words STRICT, starts with hook, ends on cliffhanger)...",
"escenas": ["filmable visual phrase 1", "filmable visual phrase 2", "filmable visual phrase 3"],
"titulo": "...(clickbait title with power word + emoji + #Shorts #Horror at end)...",
"tags": ["horror", "scary", "creepypasta", "horrorstory", "scarystories", "shorts", "viral", "paranormal", "truescaryhorror", "horrorshorts"]
}""",
        "consultas_broll": [
            "dark forest fog night", "abandoned house interior",
            "candle flame dark room", "foggy graveyard night",
            "old door creaking dark", "flashlight dark room",
            "misty woods path night", "dark attic old house",
            "shadow silhouette dark hallway", "thunderstorm dark night",
            "creepy old mansion exterior", "dark basement horror",
            "empty hallway flickering light", "footsteps dark corridor",
            "broken mirror dark room", "rain window night horror",
        ],
        "intro_texto": "WARNING: This story is not for the faint of heart...",
        "color_subtitulo": "#FF4444",
    },
}

CONSULTAS_RESPALDO = [
    "cinematic dark background", "abstract dark texture",
    "smoke slow motion dark", "clouds timelapse dark",
    "light rays dark room", "particles floating dark",
    "cinematic nature landscape", "dramatic sky clouds",
]


def extender_guion_corto(guion: str, nicho: str) -> str:
    """Si el guion es muy corto, lo extiende con una segunda llamada"""
    prompt = f"""This narration script is too short. Extend it to 90-130 words IN ENGLISH ONLY.
Keep the same style and topic. Add specific details, do not pad with filler.
Return ONLY the extended narration text, nothing else:

{guion}"""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 500}
    }
    for modelo in MODELOS_GEMINI:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{modelo}:generateContent?key={GEMINI_API_KEY}"
            )
            r = requests.post(url, json=body, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Error extendiendo: {e}")
    return guion


def generar_contenido(nicho: str) -> dict:
    prompt_sistema = NICHOS[nicho]["prompt_sistema"]
    body = {
        "contents": [{"parts": [{"text": prompt_sistema}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2000}
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
                    contenido = json.loads(texto)
                    palabras = len(contenido.get("guion", "").split())
                    print(f"Guion generado: {palabras} palabras")
                    if palabras < 90:
                        print(f"Guion muy corto ({palabras} palabras), extendiendo...")
                        contenido["guion"] = extender_guion_corto(contenido["guion"], nicho)
                        print(f"Extendido: {len(contenido['guion'].split())} palabras")
                    return contenido
                except json.JSONDecodeError:
                    return {
                        "personaje": {"nombre": "Unknown", "descripcion": "mysterious figure in a dark coat", "personalidad": "enigmatic"},
                        "lugar": {"nombre": "Unknown", "descripcion": "dramatic setting"},
                        "hook": "This is the story nobody survived to tell.",
                        "guion": "Something terrifying happened here that most people never knew about. The kind of story that keeps you awake at night wondering if it could happen to you. Investigators tried to explain it for years, but no one ever found a satisfying answer. What we know for certain is that nothing was ever the same after that night, and the house has stood empty ever since.",
                        "escenas": ["dark mysterious hallway", "tense atmospheric room", "chilling final door"],
                        "titulo": "You Won't Believe This 😱",
                        "tags": [nicho, "shorts", "viral", "horror"]
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
        "inputs": f"cinematic film still, 35mm, shallow depth of field, dramatic lighting, high quality, 4k: {prompt}",
        "parameters": {
            "width": 768,
            "height": 1344,
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
        print(f"Imagen IA: {destino}")
        return destino
    except Exception as e:
        print(f"Aviso imagen IA: {e}")
        return None


def generar_imagenes_personaje(contenido: dict) -> list:
    """Genera imagenes reutilizando la MISMA descripcion del personaje
    en cada prompt para mantener consistencia visual entre escenas."""
    rutas = []
    personaje = contenido.get("personaje", {})
    lugar = contenido.get("lugar", {})
    escenas = contenido.get("escenas", [])

    descripcion_personaje = (
        f"{personaje.get('nombre', 'mysterious person')}, "
        f"{personaje.get('descripcion', 'dramatic figure, dark clothing')} "
        "-- consistent character design, same face, same hairstyle, same outfit in every shot"
    )

    prompt_personaje = (
        f"Cinematic portrait of {descripcion_personaje}, "
        f"in {lugar.get('nombre', 'dramatic setting')}, "
        "dramatic cinematic lighting, film quality"
    )
    ruta = generar_imagen_ia(prompt_personaje, 0)
    if ruta:
        rutas.append(ruta)

    for i, escena in enumerate(escenas[:3]):
        ruta = generar_imagen_ia(
            f"{escena}, featuring {descripcion_personaje}, "
            f"{lugar.get('descripcion', 'dramatic')}, cinematic quality", i + 1
        )
        if ruta:
            rutas.append(ruta)

    return rutas


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
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path, language="en")
    return resultado["segments"]


def _buscar_clips(consulta: str, headers: dict, carpeta: str,
                   indice_inicial: int, por_consulta: int = 10):
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


def descargar_clips_por_escena(escenas: list, nicho: str, carpeta: str = "clips"):
    """Descarga clips agrupados por escena narrativa. Devuelve una lista
    de listas (una por escena) mas un pool generico de respaldo.
    Se descargan muchos clips para garantizar que nunca haya huecos."""
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}

    indice = 0
    clips_por_escena = []
    for escena in escenas:
        # 12 clips por escena (antes 8) para tener margen amplio
        rutas, indice = _buscar_clips(escena, headers, carpeta, indice, por_consulta=12)
        clips_por_escena.append(rutas)

    # Pool generico: todas las consultas del nicho a 12 clips cada una
    consultas_nicho = NICHOS[nicho]["consultas_broll"]
    pool_generico = []
    for consulta in consultas_nicho:
        rutas, indice = _buscar_clips(consulta, headers, carpeta, indice, por_consulta=12)
        pool_generico.extend(rutas)

    # Si el pool sigue siendo pequeño, añade TODAS las consultas de respaldo
    total = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    if total < 40:
        print(f"Solo {total} clips, descargando TODOS los respaldos...")
        for consulta in CONSULTAS_RESPALDO:
            extra, indice = _buscar_clips(consulta, headers, carpeta, indice, por_consulta=12)
            pool_generico.extend(extra)

    total_final = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    print(f"Total clips: {total_final}, por escena: {[len(c) for c in clips_por_escena]}")
    return clips_por_escena, pool_generico


def _preparar_clip(ruta: str, dur_max: float):
    """Abre, escala y recorta un clip al formato vertical del canal."""
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


def _clip_emergencia(duracion: float) -> ImageClip:
    """Genera un ImageClip negro solido como ULTIMO recurso absoluto.
    Solo se usa si no hay ningun clip de video disponible en el pool.
    Evita que MoviePy deje huecos de transparencia que renderizan negro."""
    from PIL import Image as PILImage
    import numpy as np
    arr = np.zeros((RESOLUCION[1], RESOLUCION[0], 3), dtype=np.uint8)
    return ImageClip(arr).set_duration(duracion)


def _rellenar_con_pool(clips_finales, tiempo_acumulado, limite,
                        pool, usados, max_intentos=None):
    """Rellena tiempo hasta 'limite' usando clips del pool.
    Nunca deja huecos: si el pool se agota, lo reutiliza desde el principio.
    Devuelve tiempo_acumulado actualizado."""
    if not pool:
        return tiempo_acumulado
    if max_intentos is None:
        max_intentos = len(pool) * 3

    intentos = 0
    pool_idx = 0
    pool_shuffled = list(pool)
    random.shuffle(pool_shuffled)

    while tiempo_acumulado < limite and intentos < max_intentos:
        # Rota por el pool en orden para minimizar repeticion
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
                 salida="video_final.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration
    color_sub = NICHOS[nicho]["color_subtitulo"]

    n_escenas = max(len(clips_por_escena), 1)
    dur_por_escena = duracion_total / n_escenas

    clips_finales = []
    tiempo_acumulado = 0.0

    for i in range(n_escenas):
        limite_tramo = (i + 1) * dur_por_escena
        clips_escena = list(clips_por_escena[i]) if i < len(clips_por_escena) else []
        random.shuffle(clips_escena)

        # Imagen IA al inicio de cada tramo (personaje en tramo 0,
        # escena i+1 en los siguientes)
        idx_img = 0 if i == 0 else i + 1
        if idx_img < len(imagenes_ia) and imagenes_ia:
            try:
                dur = min(2.5, limite_tramo - tiempo_acumulado)
                if dur > 0.1:
                    c = ImageClip(imagenes_ia[idx_img]).set_duration(dur)
                    clips_finales.append(c)
                    tiempo_acumulado += dur
            except Exception as e:
                print(f"Aviso imagen {idx_img}: {e}")

        # Clips especificos de la escena (prioridad)
        puntero = 0
        while tiempo_acumulado < limite_tramo and puntero < len(clips_escena):
            restante = limite_tramo - tiempo_acumulado
            c = _preparar_clip(clips_escena[puntero], restante)
            puntero += 1
            if c is None:
                continue
            clips_finales.append(c)
            tiempo_acumulado += c.duration

        # Relleno con pool generico si el tramo no esta cubierto
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, limite_tramo, pool_generico, set()
        )

        # Si AUN queda tiempo sin cubrir (pool insuficiente), reutiliza
        # clips de escena desde el principio para no dejar negro
        if tiempo_acumulado < limite_tramo - 0.1 and clips_escena:
            random.shuffle(clips_escena)
            tiempo_acumulado = _rellenar_con_pool(
                clips_finales, tiempo_acumulado, limite_tramo, clips_escena, set()
            )

        # Ultimo recurso absoluto: extiende el ultimo clip en vez de negro
        if tiempo_acumulado < limite_tramo - 0.1 and clips_finales:
            hueco = limite_tramo - tiempo_acumulado
            try:
                ultimo = clips_finales[-1]
                # Repite el ultimo clip cubriendo el hueco
                ruta_ultimo = None
                # Busca en el pool un clip valido para el hueco
                for ruta in pool_generico + (clips_escena if clips_escena else []):
                    c = _preparar_clip(ruta, hueco)
                    if c is not None:
                        clips_finales.append(c)
                        tiempo_acumulado += c.duration
                        break
                else:
                    # Si no hay nada, usa imagen IA estatica en vez de negro
                    if imagenes_ia:
                        img_idx = i % len(imagenes_ia)
                        c = ImageClip(imagenes_ia[img_idx]).set_duration(hueco)
                        clips_finales.append(c)
                        tiempo_acumulado += hueco
            except Exception as e:
                print(f"Aviso ultimo recurso tramo {i}: {e}")

    # Cubre cualquier tiempo restante despues del ultimo tramo
    if tiempo_acumulado < duracion_total - 0.1:
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, duracion_total, pool_generico, set()
        )

    # Si aun hay hueco, rellena con imagen IA en vez de negro
    if tiempo_acumulado < duracion_total - 0.1 and imagenes_ia:
        hueco = duracion_total - tiempo_acumulado
        try:
            c = ImageClip(imagenes_ia[0]).set_duration(hueco)
            clips_finales.append(c)
            tiempo_acumulado += hueco
        except Exception as e:
            print(f"Aviso imagen final: {e}")

    if not clips_finales:
        raise RuntimeError("No se pudo armar ningun clip")

    video_base = concatenate_videoclips(clips_finales, method="compose")
    video_base = video_base.set_duration(duracion_total)

    # Audio: voz desde el segundo 0
    audios = [audio_voz]
    if musica_path:
        try:
            musica = AudioFileClip(musica_path)
            if musica.duration < duracion_total:
                import math
                loops = math.ceil(duracion_total / musica.duration)
                musica = concatenate_audioclips([musica] * loops)
            musica = musica.subclip(0, duracion_total).volumex(0.12)
            audios.append(musica)
        except Exception as e:
            print(f"Aviso musica fondo: {e}")

    audio_final = CompositeAudioClip(audios)
    video_base = video_base.set_audio(audio_final)

    # Subtitulos estilo viral - palabras individuales
    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        duracion_seg = seg["end"] - seg["start"]
        dur_palabra = duracion_seg / max(len(palabras), 1)

        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + (j * dur_palabra)
            t_fin = t_inicio + dur_palabra

            sombra = TextClip(
                palabra.upper(), fontsize=90, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=4,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 3, int(RESOLUCION[1] * 0.72) + 3), True
            )
            txt = TextClip(
                palabra.upper(), fontsize=90, color="white",
                font="DejaVu-Sans-Bold", stroke_color=color_sub, stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.72), relative=True
            )
            subtitulos.append(sombra)
            subtitulos.append(txt)

    # Hook superpuesto desde el segundo 0
    hook_txt = TextClip(
        hook_texto.upper(),
        fontsize=64, color="white", font="DejaVu-Sans-Bold",
        stroke_color=color_sub, stroke_width=3,
        size=(RESOLUCION[0]-100, None), method="caption"
    ).set_start(0).set_end(min(2.5, duracion_total)).set_position(
        ("center", 0.38), relative=True
    )
    subtitulos.append(hook_txt)

    final = CompositeVideoClip([video_base, *subtitulos])
    final = final.set_duration(duracion_total)

    final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=2, preset="medium", bitrate="8000k",
    )
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
    # Nicho fijado a "horror" para mantener consistencia de canal.
    nicho = "horror"
    print(f"Nicho: {nicho}")

    contenido = generar_contenido(nicho)
    print(f"Personaje: {contenido['personaje']['nombre']}")
    print(f"Hook: {contenido.get('hook', '')}")

    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes_personaje(contenido)
    clips_por_escena, pool_generico = descargar_clips_por_escena(escenas, nicho)
    musica_path = descargar_musica(nicho)
    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)

    hook_texto = contenido.get("hook", NICHOS[nicho]["intro_texto"])

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia, audio_path,
        segmentos, nicho, hook_texto, musica_path
    )

    titulo = contenido.get("titulo", "This Horror Story Will Keep You Up At Night 😱 #Shorts #Horror")

    # Hashtags fijos de nicho + hashtags generados por Gemini para ese video.
    # Regla 2026: 3-5 hashtags es lo optimo. Los primeros 3 del titulo
    # son los que YouTube muestra encima del video. El resto va en descripcion.
    # Mas de 60 hashtags hace que YouTube los ignore todos.
    HASHTAGS_HORROR_FIJOS = [
        "#horror", "#scary", "#creepypasta", "#horrorstory",
        "#scarystories", "#shorts", "#paranormal", "#horrorshorts",
        "#truescaryhorror", "#creepy", "#scaryfacts", "#horrorfan",
    ]
    tags_gemini = contenido.get("tags", ["horror", "scary", "shorts"])
    tags_completos = list(dict.fromkeys(tags_gemini + [
        "horror", "scary", "creepypasta", "horrorstory", "scarystories",
        "shorts", "viral", "paranormal", "horrorshorts", "truescaryhorror",
        "creepy", "scaryfacts", "horrorfan", "horrornarrative", "scaryshorts",
    ]))

    hashtags_desc = " ".join(HASHTAGS_HORROR_FIJOS)
    descripcion = (
        f"{contenido['guion']}\n\n"
        f"⚠️ Watch until the end — the twist will haunt you.\n\n"
        f"{hashtags_desc}"
    )
    tags = tags_completos

    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
