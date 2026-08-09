"""
Pipeline Top 10 - Version 1.0

Top 10 tematicos compatibles con un canal de terror/misterio:
- unsolved mysteries, scariest places, disturbing history, paranormal,
  creepy facts, dark psychology, etc.
- Mismo pipeline de horror pero con estructura de countdown 10→1
- El numero 1 es siempre el mas impactante (retencion hasta el final)
- Clips de b-roll emparejados por entrada del top
- Hook superpuesto sobre video real desde el segundo 0
- Sin pantalla de intro estatica
- Guion 100-140 palabras (~40-55s) — mas largo que horror solo porque
  el formato countdown justifica la duracion extra
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

# Temas de top 10 compatibles con audiencia de terror/misterio.
# Todos comparten la misma estetica oscura y el mismo tipo de
# espectador que ya sigue el canal.
TEMAS_TOP10 = [
    "most disturbing unsolved mysteries in history",
    "scariest places on Earth that actually exist",
    "creepiest things ever found in abandoned places",
    "darkest secrets governments tried to hide",
    "most chilling paranormal events ever recorded",
    "most disturbing true crime cases ever",
    "scariest deep sea creatures ever discovered",
    "creepiest things caught on security cameras",
    "most terrifying natural phenomena on Earth",
    "darkest moments in human history nobody talks about",
    "most mysterious disappearances never explained",
    "creepiest unsolved disappearances caught on camera",
    "most disturbing ancient rituals ever discovered",
    "scariest real places you should never visit alone",
    "most chilling last words ever recorded",
]

MUSICA_TOP10 = [
    "https://cdn.pixabay.com/download/audio/2022/03/10/audio_270f4b1fbe.mp3",
    "https://cdn.pixabay.com/download/audio/2021/09/06/audio_dad6b6ef7f.mp3",
]

CONSULTAS_BROLL_TOP10 = [
    "dark mysterious location", "abandoned place horror",
    "dark forest fog cinematic", "old ruins night",
    "shadowy figure silhouette", "dramatic sky dark clouds",
    "creepy empty hallway", "dark water reflection night",
    "fog misty landscape night", "dramatic cliff edge ocean",
    "old cemetery night", "thunderstorm dramatic sky",
    "underwater dark ocean depth", "dark cave entrance",
    "dramatic mountain storm", "ancient ruins dark",
]

CONSULTAS_RESPALDO = [
    "cinematic dark background", "abstract dark texture",
    "smoke slow motion dark", "dramatic sky dark",
    "particles floating dark", "light rays dark room",
]

PROMPT_SISTEMA = """You are a viral YouTube Shorts top 10 narrator with 10 million subscribers.
You specialize in dark, mysterious, and disturbing content. Your audience loves horror and true crime.
You know exactly what titles get clicked and what countdowns keep people watching to number 1.

Create a top 10 countdown script about: {tema}

COUNTDOWN RULES:
- Open with the hook immediately — no intro, no "hey guys", straight into the tension
- Number from 10 down to 1
- Number 1 MUST be the most shocking, disturbing, or unbelievable entry of all
- Each entry: 1-2 punchy sentences MAX, no padding
- Build tension progressively — every entry should feel more disturbing than the last
- Tease number 1 mid-countdown ("but nothing compares to number 1...") to prevent drop-off
- 3 vivid scene descriptions for AI image generation (entries 10, 5, and 1)

HOOK RULES (most important element):
- Under 10 words
- Must create immediate dread, shock, or morbid curiosity
- Examples: "Number 1 on this list was classified for 30 years." / "What happened at number 3 was never explained."

TITLE RULES (critical for clicks):
- Start with "Top 10" + dramatic descriptor
- Include a power word: disturbing / terrifying / classified / forbidden / never explained / cursed
- End with 😱 or 👁️ or ☠️
- Add #Shorts #Horror at the very end of the title string
- Example: "Top 10 Classified Secrets Governments Still Won't Explain 😱 #Shorts #Horror"

STRICT: Write EVERYTHING in ENGLISH ONLY. Guion must be 100-140 words. No filler.

Return ONLY valid JSON, no markdown, no backticks:
{{
"tema": "...(the specific top 10 topic)...",
"hook": "...(under 10 words, creates immediate dread or morbid curiosity)...",
"guion": "...(full countdown narration 100-140 words STRICT, teases #1 mid-countdown)...",
"escenas": ["filmable visual phrase entry 10", "filmable visual phrase entry 5", "filmable visual phrase entry 1"],
"titulo": "...(clickbait title with power word + emoji + #Shorts #Horror at end)...",
"tags": ["top10", "scary", "horror", "mystery", "shorts", "creepy", "disturbing", "horrorshorts", "scaryfacts", "paranormal"]
}}"""

CONSULTAS_ESCENA = {
    "unsolved mysteries": "crime scene dark mysterious",
    "scariest places": "abandoned haunted building exterior",
    "abandoned places": "creepy abandoned interior decaying",
    "governments": "government building dark dramatic",
    "paranormal": "dark foggy mysterious figure",
    "true crime": "dark crime scene dramatic",
    "deep sea": "underwater dark ocean creature",
    "security cameras": "security camera footage dark",
    "natural phenomena": "dramatic natural phenomenon",
    "history": "dark historical ruins dramatic",
    "disappearances": "foggy dark road night",
    "ancient rituals": "ancient ruins dark dramatic",
    "last words": "dramatic dark close up",
}


def generar_contenido() -> dict:
    tema = random.choice(TEMAS_TOP10)
    prompt = PROMPT_SISTEMA.format(tema=tema)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.95, "maxOutputTokens": 2000}
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
                    print(f"Tema: {tema} | Guion: {palabras} palabras")
                    return contenido
                except json.JSONDecodeError:
                    return {
                        "tema": tema,
                        "hook": "Number 1 will keep you up at night.",
                        "guion": (
                            "Top 10 most disturbing unsolved mysteries. "
                            "Number 10: A ship found drifting with no crew, food still warm. "
                            "Number 9: A town that vanished overnight, leaving everything behind. "
                            "Number 8: A lighthouse keeper who disappeared mid-shift. "
                            "Number 7: A family that walked into the woods and was never seen again. "
                            "Number 6: A recording of voices from a place no one had ever visited. "
                            "Number 5: A man who appeared with no memory of the past 30 years. "
                            "Number 4: A child who described their past life in perfect detail. "
                            "Number 3: A door in an abandoned hospital that could not be opened. "
                            "Number 2: A signal received from space that was never explained. "
                            "Number 1: And the case that even the government refuses to discuss."
                        ),
                        "escenas": [
                            "abandoned ship dark ocean fog",
                            "dark mysterious forest disappearance",
                            "government building dramatic dark night"
                        ],
                        "titulo": "Top 10 Unsolved Mysteries That Will Haunt You 😱",
                        "tags": ["top10", "scary", "horror", "mystery", "shorts"]
                    }
            except Exception as e:
                print(f"Error en {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos de Gemini fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_top10") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": (
            f"cinematic film still, 35mm, shallow depth of field, "
            f"dramatic dark lighting, high quality, 4k, dark atmosphere: {prompt}"
        ),
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


def generar_imagenes(escenas: list) -> list:
    rutas = []
    for i, escena in enumerate(escenas[:3]):
        ruta = generar_imagen_ia(
            f"{escena}, dark cinematic atmosphere, dramatic lighting", i
        )
        if ruta:
            rutas.append(ruta)
    return rutas


def descargar_musica() -> str:
    url = random.choice(MUSICA_TOP10)
    destino = "musica_top10.mp3"
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Musica descargada")
        return destino
    except Exception as e:
        print(f"Aviso musica: {e}")
        return None


async def _tts(texto: str, salida: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(salida)


def generar_audio(texto: str, salida: str = "audio_top10.mp3"):
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


def descargar_clips(escenas: list, carpeta: str = "clips_top10"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    indice = 0

    # 12 clips por escena para tener margen amplio
    clips_por_escena = []
    for escena in escenas:
        rutas, indice = _buscar_clips(escena, headers, carpeta, indice, por_consulta=12)
        clips_por_escena.append(rutas)

    # Pool generico a 12 clips por consulta
    pool_generico = []
    for consulta in CONSULTAS_BROLL_TOP10:
        rutas, indice = _buscar_clips(consulta, headers, carpeta, indice, por_consulta=12)
        pool_generico.extend(rutas)

    total = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    if total < 40:
        print(f"Solo {total} clips, descargando TODOS los respaldos...")
        for consulta in CONSULTAS_RESPALDO:
            extra, indice = _buscar_clips(consulta, headers, carpeta, indice, por_consulta=12)
            pool_generico.extend(extra)

    total_final = sum(len(c) for c in clips_por_escena) + len(pool_generico)
    print(f"Total clips: {total_final}")
    return clips_por_escena, pool_generico


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
    dur_clip = min(c.duration, dur_max, random.uniform(2.0, 4.0))
    if dur_clip <= 0:
        c.close()
        return None
    return c.subclip(0, dur_clip)


def _rellenar_con_pool(clips_finales, tiempo_acumulado, limite,
                        pool, usados, max_intentos=None):
    """Rellena tiempo hasta 'limite' rotando el pool sin dejar huecos."""
    if not pool:
        return tiempo_acumulado
    if max_intentos is None:
        max_intentos = len(pool) * 3

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
                 segmentos, hook_texto, musica_path, salida="video_top10.mp4"):
    audio_voz = AudioFileClip(audio_path)
    duracion_total = audio_voz.duration

    n_escenas = max(len(clips_por_escena), 1)
    dur_por_escena = duracion_total / n_escenas

    clips_finales = []
    tiempo_acumulado = 0.0

    for i in range(n_escenas):
        limite_tramo = (i + 1) * dur_por_escena
        clips_escena = list(clips_por_escena[i]) if i < len(clips_por_escena) else []
        random.shuffle(clips_escena)

        # Imagen IA de esa escena si existe
        if i < len(imagenes_ia) and imagenes_ia:
            try:
                dur = min(2.5, limite_tramo - tiempo_acumulado)
                if dur > 0.1:
                    c = ImageClip(imagenes_ia[i]).set_duration(dur)
                    clips_finales.append(c)
                    tiempo_acumulado += dur
            except Exception as e:
                print(f"Aviso imagen escena {i}: {e}")

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

        # Relleno con pool generico (rota sin limite para no dejar negro)
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, limite_tramo, pool_generico, set()
        )

        # Si aun queda hueco, reutiliza clips de escena
        if tiempo_acumulado < limite_tramo - 0.1 and clips_escena:
            random.shuffle(clips_escena)
            tiempo_acumulado = _rellenar_con_pool(
                clips_finales, tiempo_acumulado, limite_tramo, clips_escena, set()
            )

        # Ultimo recurso: imagen IA en vez de negro
        if tiempo_acumulado < limite_tramo - 0.1 and imagenes_ia:
            hueco = limite_tramo - tiempo_acumulado
            try:
                img_idx = i % len(imagenes_ia)
                c = ImageClip(imagenes_ia[img_idx]).set_duration(hueco)
                clips_finales.append(c)
                tiempo_acumulado += hueco
            except Exception as e:
                print(f"Aviso imagen emergencia tramo {i}: {e}")

    # Tiempo restante tras el ultimo tramo
    if tiempo_acumulado < duracion_total - 0.1:
        tiempo_acumulado = _rellenar_con_pool(
            clips_finales, tiempo_acumulado, duracion_total, pool_generico, set()
        )

    # Si aun hay hueco, imagen IA en vez de negro
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

            # Resalta numeros en amarillo para que el countdown sea visible
            es_numero = any(n in palabra for n in ["10","9","8","7","6","5","4","3","2","1"])
            color_palabra = "#FFD700" if es_numero else "white"
            color_stroke = "#FF4444"

            sombra = TextClip(
                palabra.upper(), fontsize=90, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=4,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 3, int(RESOLUCION[1] * 0.72) + 3), True
            )
            txt = TextClip(
                palabra.upper(), fontsize=90, color=color_palabra,
                font="DejaVu-Sans-Bold", stroke_color=color_stroke, stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.72), relative=True
            )
            subtitulos.append(sombra)
            subtitulos.append(txt)

    # Hook superpuesto sobre el video desde el segundo 0
    hook_txt = TextClip(
        hook_texto.upper(),
        fontsize=64, color="white", font="DejaVu-Sans-Bold",
        stroke_color="#FF4444", stroke_width=3,
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
    print("Pipeline Top 10 - terror compatible")

    contenido = generar_contenido()
    print(f"Tema: {contenido.get('tema', '')}")
    print(f"Hook: {contenido.get('hook', '')}")

    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes(escenas)
    clips_por_escena, pool_generico = descargar_clips(escenas)
    musica_path = descargar_musica()
    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)

    hook_texto = contenido.get("hook", "Number 1 will keep you up at night.")

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia,
        audio_path, segmentos, hook_texto, musica_path
    )

    titulo = contenido.get("titulo", "Top 10 Most Disturbing Mysteries Never Explained 😱 #Shorts #Horror")

    # Hashtags optimizados para nicho oscuro/misterio/top10.
    # Regla 2026: 3-5 en titulo (los primeros 3 aparecen encima del video),
    # resto en descripcion. Maximo 60 en total o YouTube los ignora todos.
    HASHTAGS_TOP10_FIJOS = [
        "#shorts", "#horror", "#top10", "#scary",
        "#mystery", "#creepy", "#disturbing", "#paranormal",
        "#scaryfacts", "#horrorshorts", "#truecrime", "#unexplained",
    ]
    tags_gemini = contenido.get("tags", ["top10", "scary", "horror", "shorts"])
    tags_completos = list(dict.fromkeys(tags_gemini + [
        "top10", "scary", "horror", "mystery", "shorts", "viral",
        "creepy", "disturbing", "paranormal", "scaryfacts", "horrorshorts",
        "truecrime", "unexplained", "darkfacts", "scaryshorts",
    ]))

    hashtags_desc = " ".join(HASHTAGS_TOP10_FIJOS)
    descripcion = (
        f"{contenido['guion']}\n\n"
        f"⚠️ Stay until number 1 — it will change how you see the world.\n\n"
        f"{hashtags_desc}"
    )
    tags = tags_completos

    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
