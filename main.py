"""
Pipeline 100% automático para Shorts (canal multi-nicho).
Se ejecuta 2 veces al día (1pm y 11pm), disparado por GitHub Actions.
Nichos: Horror Stories, True Crime, World Records, Top 10.
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

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

VOZ = "en-US-GuyNeural"
RESOLUCION = (1080, 1920)

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
            "top 10 mysteries science still
