"""
WealthSnap - Pipeline Shorts Finanzas - Version 1.0

Top 10 de finanzas personales, habitos de ricos, errores financieros,
datos de dinero que sorprenden. CPM $18-$45 segun datos OutlierKit 2026.

Formato: countdown 10→1 o datos financieros virales, 35-50 segundos.
Audiencia: jovenes adultos que quieren mejorar su situacion economica.
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

# Voces autoritativas y confiables para finanzas
VOCES_FINANCE = [
    "en-US-AndrewNeural",
    "en-US-ChristopherNeural",
    "en-GB-RyanNeural",
    "en-AU-WilliamNeural",
    "en-US-GuyNeural",
    "en-GB-ThomasNeural",
]

MUSICA_FINANCE = [
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0c6ff1d24.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_5bbc9a1a1c.mp3",
    "https://cdn.pixabay.com/download/audio/2021/08/09/audio_99bbbd8a4c.mp3",
]

# Sub-nichos que alternan para dar variedad al canal
# todos dentro de finanzas personales (mismo CPM alto)
SUBNICHOS_FINANCE = {
    "top10_habits": {
        "temas": [
            "habits of people who became millionaires before 40",
            "money habits that keep most people broke",
            "things rich people do with their money that poor people don't",
            "habits of people who retired early with no inheritance",
            "financial mistakes that destroy wealth in your 20s and 30s",
            "things self-made billionaires never spend money on",
            "money rules wealthy people follow that nobody talks about",
            "habits that separate the top 1% from everyone else financially",
        ],
        "consultas_broll": [
            "businessman luxury office", "money cash bills closeup",
            "stock market charts screen", "luxury car driving businessman",
            "investment portfolio growth chart", "city skyline financial district",
            "person working laptop coffee shop", "savings piggy bank money",
            "real estate luxury building aerial", "credit card payment transaction",
        ],
        "color_sub": "#00C853",
        "color_hook": "#FFD700",
        "prompt_tipo": "top10_habits",
    },
    "top10_facts": {
        "temas": [
            "most shocking facts about money that will change how you think",
            "financial facts schools never taught you that rich people know",
            "most mind-blowing wealth statistics that will motivate you",
            "things about the banking system most people never figure out",
            "most surprising facts about how billionaires actually make money",
            "financial truths that feel illegal to know",
            "most shocking things about compound interest nobody talks about",
            "money facts that explain why most people stay poor forever",
        ],
        "consultas_broll": [
            "financial data charts graphs", "bank vault money",
            "stock exchange trading floor", "dollar bills falling",
            "calculator budget planning", "investment growth arrow",
            "wealthy neighborhood aerial", "financial newspaper reading",
            "money printing federal reserve", "crypto bitcoin digital",
        ],
        "color_sub": "#2196F3",
        "color_hook": "#FFD700",
        "prompt_tipo": "top10_facts",
    },
    "top10_mistakes": {
        "temas": [
            "biggest financial mistakes people make in their 20s",
            "money mistakes that silently destroy your wealth over time",
            "things financial advisors wish you would stop doing with money",
            "worst ways people waste money without realizing it",
            "financial decisions that sound smart but destroy your future",
            "biggest investing mistakes beginners make that cost them everything",
            "money traps designed to keep you broke your entire life",
        ],
        "consultas_broll": [
            "person stressed financial debt", "credit card debt bills",
            "empty wallet no money", "financial stress anxiety",
            "bankruptcy documents papers", "overspending shopping bags",
            "loan interest rate documents", "person calculating bills stress",
            "money burning waste", "financial mistake regret",
        ],
        "color_sub": "#FF5252",
        "color_hook": "#FFD700",
        "prompt_tipo": "top10_mistakes",
    },
}

CONSULTAS_RESPALDO = [
    "financial success money", "business growth chart",
    "investment wealth building", "money management planning",
]

PROMPT_TOP10 = """You are a viral YouTube Shorts finance narrator for WealthSnap channel.
Your audience wants to learn money secrets, wealth habits, and financial facts fast.
CPM goal: $18-$45. Content must be accurate, specific, and actionable.

Create a top 10 countdown about: {tema}

RULES:
- Start with the hook IMMEDIATELY — no intro, straight into the value
- Number from 10 down to 1
- Number 1 must be the most surprising, impactful, or counterintuitive entry
- Each entry: 1-2 punchy sentences with SPECIFIC details (percentages, amounts, names)
- Build value progressively — each entry more surprising than the last
- At entry 5 tease #1: "but the most important one is coming at number 1..."
- Use real data and specific numbers — vague tips kill credibility
- 3 vivid scene descriptions for AI image generation (professional, financial aesthetic)

HOOK: Under 10 words. Creates immediate curiosity or reveals a surprising fact.
Examples: "90% of millionaires share this one habit." / "This mistake costs you $500K."

TITLE RULES:
- Start with "Top 10"
- Power word: shocking / brutal / secret / nobody / millionaire / broke
- End with 💰 or 📈 or 🤑
- Add #Shorts #Finance at end of title

STRICT: 100-130 words ENGLISH ONLY. Every sentence must deliver real value.

Return ONLY valid JSON, no markdown, no backticks:
{{
"hook": "...(under 10 words, specific and surprising)...",
"guion": "...(100-130 words STRICT, countdown 10 to 1 with specific data)...",
"escenas": ["professional financial visual 1", "financial visual 2", "financial visual 3"],
"titulo": "...(Top 10 title + emoji + #Shorts #Finance)...",
"tags": ["finance", "money", "personalfinance", "wealth", "investing", "top10", "shorts", "rich", "millionaire", "financetips"]
}}"""


def generar_contenido() -> tuple:
    subnicho_key = random.choice(list(SUBNICHOS_FINANCE.keys()))
    subnicho = SUBNICHOS_FINANCE[subnicho_key]
    tema = random.choice(subnicho["temas"])

    prompt = PROMPT_TOP10.format(tema=tema)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 1500}
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
                print(f"Sub-nicho: {subnicho_key} | Tema: {tema}")
                print(f"Guion: {len(contenido.get('guion','').split())} palabras")
                return contenido, subnicho
            except Exception as e:
                print(f"Error {modelo} intento {intento+1}: {e}")
                time.sleep(5)
    raise RuntimeError("Todos los modelos fallaron")


def generar_imagen_ia(prompt: str, indice: int, carpeta: str = "imagenes_finance") -> str:
    os.makedirs(carpeta, exist_ok=True)
    destino = f"{carpeta}/imagen_{indice}.png"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": (
            f"professional financial photography, clean modern aesthetic, "
            f"high quality, 4k, corporate: {prompt}"
        ),
        "parameters": {"width": 768, "height": 1344, "negative_prompt": NEGATIVE_PROMPT}
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
    return [
        ruta for i, escena in enumerate(escenas[:3])
        if (ruta := generar_imagen_ia(f"{escena}, professional finance aesthetic", i))
    ]


def descargar_musica() -> str:
    url = random.choice(MUSICA_FINANCE)
    destino = "musica_finance.mp3"
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


def generar_audio(texto: str, salida: str = "audio_finance.mp3"):
    voz = random.choice(VOCES_FINANCE)
    print(f"Voz: {voz}")
    asyncio.run(_tts(texto, salida, voz))
    return salida


def transcribir(audio_path: str):
    return whisper.load_model("base").transcribe(audio_path, language="en")["segments"]


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


def descargar_clips(escenas, subnicho, carpeta="clips_finance"):
    os.makedirs(carpeta, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    indice = 0
    clips_por_escena = []
    for escena in escenas:
        rutas, indice = _buscar_clips(escena, headers, carpeta, indice, 12)
        clips_por_escena.append(rutas)
    pool_generico = []
    for consulta in subnicho["consultas_broll"]:
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
    dur_clip = min(c.duration, dur_max, random.uniform(1.5, 3.0))
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
                 segmentos, hook_texto, musica_path, subnicho,
                 salida="video_finance.mp4"):
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
            audios.append(musica.subclip(0, duracion_total).volumex(0.12))
        except Exception as e:
            print(f"Aviso musica: {e}")

    video_base = video_base.set_audio(CompositeAudioClip(audios))

    color_sub = subnicho["color_sub"]
    color_hook = subnicho["color_hook"]

    # Palabras clave de finanzas resaltadas en verde/dorado
    PALABRAS_CLAVE_FINANCE = {
        "million", "billion", "percent", "%", "rich", "wealthy", "broke",
        "invest", "save", "debt", "profit", "loss", "income", "salary",
        "compound", "interest", "retirement", "passive", "freedom", "money",
        "wealthy", "millionaire", "billionaire", "secret", "mistake",
    }

    subtitulos = []
    for seg in segmentos:
        palabras = seg["text"].strip().split()
        if not palabras:
            continue
        dur_palabra = (seg["end"] - seg["start"]) / max(len(palabras), 1)
        for j, palabra in enumerate(palabras):
            t_inicio = seg["start"] + j * dur_palabra
            t_fin = t_inicio + dur_palabra
            es_numero = any(n in palabra for n in ["10","9","8","7","6","5","4","3","2","1"])
            es_clave = palabra.lower().strip(".,!?$%") in PALABRAS_CLAVE_FINANCE
            color = "#FFD700" if es_numero else (color_sub if es_clave else "white")
            tam = 95 if es_clave or es_numero else 90

            subtitulos.append(TextClip(
                palabra.upper(), fontsize=tam, color="black",
                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=4,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                (RESOLUCION[0]//2 - 3, int(RESOLUCION[1] * 0.72) + 3), True
            ))
            subtitulos.append(TextClip(
                palabra.upper(), fontsize=tam, color=color,
                font="DejaVu-Sans-Bold", stroke_color="#1B5E20", stroke_width=3,
            ).set_start(t_inicio).set_end(t_fin).set_position(
                ("center", 0.72), relative=True
            ))

    subtitulos.append(TextClip(
        hook_texto.upper(), fontsize=62, color="white",
        font="DejaVu-Sans-Bold", stroke_color=color_hook, stroke_width=3,
        size=(RESOLUCION[0]-100, None), method="caption"
    ).set_start(0).set_end(min(2.5, duracion_total)).set_position(
        ("center", 0.38), relative=True
    ))

    final = CompositeVideoClip([video_base, *subtitulos]).set_duration(duracion_total)
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
                "categoryId": "27",  # Education - mejor CPM que Entertainment
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    print("Subido:", request.execute().get("id"))


def main():
    print("WealthSnap - Pipeline Shorts Finanzas")
    contenido, subnicho = generar_contenido()
    escenas = contenido.get("escenas", [])
    imagenes_ia = generar_imagenes(escenas)
    clips_por_escena, pool_generico = descargar_clips(escenas, subnicho)
    musica_path = descargar_musica()
    audio_path = generar_audio(contenido["guion"])
    segmentos = transcribir(audio_path)
    hook_texto = contenido.get("hook", "90% of people never learn this about money.")

    video_path = armar_video(
        clips_por_escena, pool_generico, imagenes_ia,
        audio_path, segmentos, hook_texto, musica_path, subnicho
    )

    titulo = contenido.get("titulo", "Top 10 Money Secrets Nobody Tells You 💰 #Shorts #Finance")
    HASHTAGS = ["#shorts", "#finance", "#money", "#personalfinance", "#wealth",
                "#investing", "#rich", "#millionaire", "#financetips", "#top10"]
    tags = list(dict.fromkeys(
        contenido.get("tags", []) + [
            "finance", "money", "personalfinance", "wealth", "investing",
            "top10", "shorts", "rich", "millionaire", "financetips",
            "budgeting", "savemoney", "financialfreedom", "wealthbuilding",
        ]
    ))
    descripcion = (
        f"{contenido['guion']}\n\n"
        f"💰 Subscribe for daily money tips that actually work.\n\n"
        f"{' '.join(HASHTAGS)}"
    )
    subir_youtube(video_path, titulo, descripcion, tags)


if __name__ == "__main__":
    main()
