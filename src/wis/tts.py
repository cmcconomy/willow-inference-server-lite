import httpx
from fastapi import Response
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk

from wis.config import TtsConfig, TtsProvider


async def to_speech(text: str, config: TtsConfig) -> Response:
    """
    Convert text to speech using Google Translate TTS API.
    
    Args:
        text (str): The text to convert to speech.
        language (str): The language code for the speech. Default is "en-US".
    
    Returns:
        bytes: The audio content in MP3 format.
    """
    result = None
    match config.tts_provider:
        case TtsProvider.GoogleTranslate:
            url = "https://translate.google.com/translate_tts"
            params = {
                "ie": "UTF-8",
                "tl": config.tts_language or 'en',
                "client": "tw-ob",
                "q": text[0:200],
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params)
                result = Response(await resp.content, media_type="audio/mpeg")

        case TtsProvider.OpenAI:
            if not config.tts_openai_baseurl:
                raise ValueError("OpenAI TTS requires base URL (and sometimes API key)")
            
            client = AsyncOpenAI(
                base_url=config.tts_openai_baseurl, api_key=config.tts_openai_apikey or "not-needed"
            )

            stream: AsyncStream[ChatCompletionChunk] = await client.audio.speech.create(
                model=config.tts_openai_model,
                voice=config.tts_openai_voice, #single or multiple voicepack combo
                input=text
            )
            result = StreamingResponse(stream.response.aiter_bytes(), media_type="audio/mpeg")

        case _:
            raise ValueError("Unsupported TTS provider")

    
    return result
