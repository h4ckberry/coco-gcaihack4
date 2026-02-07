from google.cloud import texttospeech
import base64
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Cloud TTS Client
try:
    client = texttospeech.TextToSpeechClient()
except Exception as e:
    logger.warning(f"Cloud TTS Client initialization failed: {e}. TTS will be disabled.")
    client = None

def synthesize_text(text: str, language_code: str = "ja-JP") -> str:
    """
    Synthesizes speech from text using Google Cloud Text-to-Speech.
    Returns the audio content as a base64 encoded string.
    """
    if not client:
        return ""
    
    if not text:
        return ""

    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name="ja-JP-Neural2-B", # Example high-quality voice
             ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Return base64 encoded audio
        return base64.b64encode(response.audio_content).decode("utf-8")

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return ""
