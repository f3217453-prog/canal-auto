"""
Pipeline 100% automático para Shorts (canal multi-nicho).
Se ejecuta 2 veces al día (1pm y 11pm), disparado por GitHub Actions.
Nichos: Horror Stories, True Crime, World Records, Top 10.

Pasos:
1. Elige nicho y tema al azar
2. Genera un guion con Gemini (API gratuita)
3. Convierte el guion en audio con edge-tts (gratis, sin límite)
4. Transcribe el audio con timestamps usando whisper (gratis, local)
5. Descarga MUCHOS clips variados desde Pexels (evita repetición y pantallas negras)
6. Arma el video final con moviepy (clips + audio + subtítulos)
7. Sube el video a YouTube usando la API de YouTube Data v3
"""

import os
import random
import textwrap
import requests
import asyncio
import edge_tts
import whisper
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_videoclips
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

VOZ = "en-US-GuyNeural"
RESOLUCION = (1080, 1920)  # vertical, para Shorts

# ------------------------------------------------------------------
# NICHOS Y TEMAS (se elige uno al azar en cada ejecución)
# ------------------------------------------------------------------
NICHOS = {
    "horror": {
        "temas": [
            "a ghost story set in an abandoned house",
            "a chilling creepypasta about something in the woods",
            "a haunted house with a dark history",
            "an urban legend that still scares people today",
            "a real reported ghost sighting with no explanation",
        ],
        "instruccion": (
            "Write it as a scary, atmospheric horror narration. Build dread "
            "slowly, use sensory details, end on a chilling unresolved note."
        ),
        "tags": ["horror", "scary story", "creepypasta", "shorts"],
    },
    "true_crime": {
        "temas": [
            "an unsolved disappearance that baffled investigators",
            "a cold case cracked open decades later",
            "a criminal who evaded capture in a shocking way",
            "a mysterious death many still question",
        ],
        "instruccion": (
            "Write it as a suspenseful true crime narration. Focus on the "
            "intrigue and timeline, not graphic violence. End with a twist "
            "or unresolved question."
        ),
        "tags": ["truecrime", "mystery", "unsolved", "shorts"],
    },
    "world_records": {
        "temas": [
            "the most extreme world record ever achieved",
            "a bizarre Guinness World Record most people don't know about",
            "a record that seems impossible but is completely real",
            "the fastest, biggest, or strangest record in its category",
        ],
        "instruccion": (
            "Write it as an exciting, fast-paced narration about a real "
            "world record. Use vivid numbers and comparisons to make it "
            "feel astonishing."
        ),
        "tags": ["worldrecord", "guinnessworldrecords", "amazing", "shorts"],
    },
    "top10": {
        "temas": [
            "top 10 most dangerous places on Earth",
            "top 10 strangest animals in the world",
            "top 10 mysteries science still can't explain",
            "top 10 most valuable things ever discovered",
        ],
        "instruccion": (
            "Write it as a punchy top 10 countdown narration. Quick hits, "
            "one sentence per fact building up to the most shocking one "
            "at the end."
        ),
        "tags": ["top10", "facts", "ranking", "shorts"],
    },
}

CONSULTAS_AMBIENTE = {
    "horror": [
        "dark forest fog night", "abandoned house interior", "old hallway dark",
        "candle flame dark room", "creepy basement", "foggy graveyard night",
        "old door creaking", "flashlight dark room",
    ],
    "true_crime": [
        "dark street night fog", "police lights night city", "old detective office",
        "rain window night moody", "empty road night headlights", "newspaper archive",
        "typewriter old paper", "evidence board string",
    ],
    "world_records": [
        "stadium crowd aerial", "extreme sports action", "fast car racing",
        "mountain climbing extreme", "ocean waves aerial", "city skyline aerial",
        "athlete running slow motion", "fireworks night sky",
    ],
    "top10": [
        "nature landscape aerial", "city skyline timelapse", "ocean underwater",
        "desert landscape aerial", "mountain range aerial", "wildlife animals",
        "space stars night sky", "waterfall nature",
    ],
}


def generar_guion(tema: str, instruccion: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = textwrap.dedent(f"""
        Write a 55-second narration script in English about: {tema}.
        {instruccion}
        Short sentences. Strong hook in the first sentence.
        Only the narration text, no titles or numbering, as if narrated by
        a single voice.
    """)
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


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


CONSULTAS_RESPALDO = [
    "cinematic dark background", "abstract dark texture", "smoke slow motion dark",
    "clouds timelapse dark", "light rays dark room", "particles floating dark",
]


def _descargar_desde_consultas(consultas, headers, carpeta, indice_inicial, minimo_por_consulta=6):
    rutas = []
    indice_global = indice_inicial
    for consulta in consultas:
        url = (
            f"https://api.pexels.com/videos/search?query={consulta}"
            f"&per_page={minimo_por_consulta}"
        )
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
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
            except requests.exceptions.RequestException as e:
                print(f"Aviso: falló descarga de un clip: {e}")
                continue
    return rutas, indice_global


def descargar_clips(nicho: str, carpeta: str = "clips"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    consultas = CONSULTAS_AMBIENTE[nicho]

    rutas, siguiente_indice = _descargar_desde_consultas(consultas, headers, carpeta, 0)

    # Si el nicho no trajo suficientes clips (mínimo 15 para variedad real),
    # completamos con búsquedas genéricas que Pexels sí tiene en abundancia
    if len(rutas) < 15:
        print(f"Solo {len(rutas)} clips del nicho, completando con búsquedas de respaldo...")
        extra, siguiente_indice = _descargar_desde_consultas(
            CONSULTAS_RESPALDO, headers, carpeta, siguiente_indice
        )
        rutas.extend(extra)

    print(f"Total de clips descargados: {len(rutas)}")
    return rutas


def armar_video(clips_rutas, audio_path, segmentos, salida="video_final.mp4"):
    if not clips_rutas:
        raise RuntimeError("No se descargó ningún clip de Pexels, no se puede armar el video")

    audio = AudioFileClip(audio_path)
    duracion_total = audio.duration

    orden = clips_rutas.copy()
    random.shuffle(orden)

    clips = []
    tiempo_acumulado = 0
    puntero = 0
    ultimo_usado = None

    while tiempo_acumulado < duracion_total:
        if puntero >= len(orden):
            random.shuffle(orden)
            if orden[0] == ultimo_usado and len(orden) > 1:
                orden[0], orden[1] = orden[1], orden[0]
            puntero = 0

        ruta = orden[puntero]
        puntero += 1

        try:
            c = VideoFileClip(ruta).without_audio()
        except Exception:
            continue

        if c.duration < 0.5:
            c.close()
            continue

        # Escala el clip para que cubra TODO el frame vertical (nunca deja
        # bandas negras), luego recorta al centro al tamaño exacto
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
        clips.append(c)
        tiempo_acumulado += duracion_clip
        ultimo_usado = ruta

    if not clips:
        raise RuntimeError("No se pudo armar ningún clip válido para el video")

    video_base = concatenate_videoclips(clips, method="compose")
    video_base = video_base.set_audio(audio)
    video_base = video_base.set_duration(duracion_total)

    subtitulos = []
    for seg in segmentos:
        txt = TextClip(
            seg["text"].strip(), fontsize=60, color="white",
            font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=2,
            size=(RESOLUCION[0]-100, None), method="caption"
        ).set_start(seg["start"]).set_end(seg["end"]).set_position(("center", "bottom"))
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


def generar_titulo(nicho: str, tema: str) -> str:
    if nicho == "horror":
        return "This True Horror Story Will Haunt You 👻"
    if nicho == "true_crime":
        return "The Case Nobody Could Solve 🔎"
    if nicho == "world_records":
        return "You Won't Believe This World Record 🌍"
    return "Top 10 You Need To See 🔥"


def main():
    nicho = random.choice(list(NICHOS.keys()))
    tema = random.choice(NICHOS[nicho]["temas"])
    instruccion = NICHOS[nicho]["instruccion"]
    tags = NICHOS[nicho]["tags"]

    print("Nicho elegido:", nicho)
    print("Tema elegido:", tema)

    guion = generar_guion(tema, instruccion)
    print("Guion generado:\n", guion)

    audio_path = generar_audio(guion)
    segmentos = transcribir(audio_path)
    clips = descargar_clips(nicho)
    print(f"Clips descargados: {len(clips)}")
    video_path = armar_video(clips, audio_path, segmentos)

    titulo = generar_titulo(nicho, tema)
    descripcion = f"{guion}\n\n#{nicho.replace('_', '')} #shorts"
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
