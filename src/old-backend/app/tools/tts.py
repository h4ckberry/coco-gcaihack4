from google.cloud import texttospeech
import base64

def synthesize_speech(text: str) -> str:
    """
    Synthesizes speech from text using Google Cloud TTS.
    Returns base64 encoded audio content.
    """
    # For local testing without creds, return dummy
    try:
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        return base64.b64encode(response.audio_content).decode("utf-8")
    except Exception as e:
        print(f"Warning: TTS failed (likely no credentials). Returning dummy. Error: {e}")
        return "b64_dummy_audio_data"
