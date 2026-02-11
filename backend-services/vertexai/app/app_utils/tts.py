from google.auth import default
from google.auth.transport.requests import Request
import requests
import base64
import logging
import json

logger = logging.getLogger(__name__)

_TTS_SYSTEM_PROMPT = (
    "声はアニメキャラクターのようで暖かく、落ち着いた親しみやすいキャラクターをイメージしてください。"
    "また、サポートAIなので、語尾などもユーザに寄り添ったものとしてください。\n"
    "あと、活舌ははっきりとしつつキャラクターらしさを残してください。"
    "そのうえでイントネーションも人間と遜色ないようお願いします。\n"
    "また、人が話す際に読み上げないもの（・や＊など）は読み上げないようお願いします。"
)

def synthesize_text(text: str, language_code: str = "ja-jp") -> str:
    """
    Synthesizes speech from text using Google Cloud Text-to-Speech (Gemini TTS model).
    Returns the audio content as a base64 encoded string.
    """
    if not text:
        return ""

    try:
        # Get credentials and refresh token
        credentials, project = default()
        auth_request = Request()
        credentials.refresh(auth_request)
        
        url = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
        
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json; charset=utf-8",
            "x-goog-user-project": project
        }

        # User specified prompt
        system_prompt = _TTS_SYSTEM_PROMPT

        data = {
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "pitch": 0,
                "speakingRate": 1
            },
            "input": {
                "prompt": system_prompt,
                "text": text
            },
            "voice": {
                "languageCode": language_code,
                "modelName": "gemini-2.5-pro-tts",
                "name": "Leda"
            }
        }

        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            logger.error(f"TTS API request failed with status {response.status_code}: {response.text}")
            return ""

        response_json = response.json()
        
        if "audioContent" not in response_json:
            logger.error(f"TTS API response did not contain audioContent: {response_json}")
            return ""

        # The API returns base64 encoded audio content
        # We need to ensure it's returned as a clean string
        return response_json["audioContent"]

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return ""
