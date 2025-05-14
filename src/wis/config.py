from enum import Enum

from pydantic_settings import BaseSettings

"""
Pydantic Config pulls from environment variables; 
eg `STT_WHISPER_MODEL_ID` will set the value of SttConfig.stt_whisper_model_id
"""

class SttConfig(BaseSettings):
    stt_whisper_model_id: str = "small"
    stt_whisper_device: str = "cpu"
    stt_whisper_compute_type: str = "int8"
    stt_whisper_language: str | None = None

class TtsProvider(Enum):
    GoogleTranslate = "google_translate"
    OpenAI = "openai"

class TtsConfig(BaseSettings):
    tts_provider: TtsProvider = TtsProvider.GoogleTranslate
    tts_language: str | None = None
    tts_openai_baseurl: str | None = None
    tts_openai_apikey: str | None = None
    tts_openai_model: str = 'kokoro'
    tts_openai_voice: str = 'af_sky+af_bella'
