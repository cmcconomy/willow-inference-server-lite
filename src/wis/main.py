import os
from functools import cache
from io import BytesIO
from typing import NamedTuple

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel


class Config(NamedTuple):
    model_id: str = os.getenv("WHISPER_MODEL_ID", "small")
    device: str = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    language: str = os.getenv("WHISPER_LANGUAGE", "en")


@cache
def get_stt_model(config: Config) -> WhisperModel:
    return WhisperModel(
        config.model_id, device=config.device, compute_type=config.compute_type
    )


config = Config()
get_stt_model(config)  # warm up the model; will download on demand
app = FastAPI()


def create_wav_header(num_channels, sample_rate, bits_per_sample, data_size):
    """
    Converted (with apologies) from https://github.com/JayPearlman/WIS-CF-Worker
    """
    # RIFF Header
    riff = b"RIFF"
    wave = b"WAVE"

    # Format Chunk
    fmt = b"fmt "
    fmt_chunk_size = 16  # For PCM
    audio_format = 1  # PCM
    byte_rate = sample_rate * num_channels * bits_per_sample // 8  # Byte rate
    block_align = num_channels * bits_per_sample // 8  # Block align

    # Data Chunk
    data = b"data"

    # Create a bytearray to hold the WAV header
    header = bytearray(44)  # Standard WAV header size

    # RIFF header
    header[0:4] = riff  # "RIFF"
    header[4:8] = (36 + data_size).to_bytes(4, "little")  # File size minus 8
    header[8:12] = wave  # "WAVE"

    # Format chunk
    header[12:16] = fmt  # "fmt "
    header[16:20] = fmt_chunk_size.to_bytes(4, "little")  # Chunk size
    header[20:22] = audio_format.to_bytes(2, "little")  # Audio format
    header[22:24] = num_channels.to_bytes(2, "little")  # Number of channels
    header[24:28] = sample_rate.to_bytes(4, "little")  # Sample rate
    header[28:32] = byte_rate.to_bytes(4, "little")  # Byte rate
    header[32:34] = block_align.to_bytes(2, "little")  # Block align
    header[34:36] = bits_per_sample.to_bytes(2, "little")  # Bits per sample

    # Data chunk
    header[36:40] = data  # "data"
    header[40:44] = data_size.to_bytes(4, "little")  # Data size

    return header


@app.post("/api/willow")
async def willow(request: Request):
    global config
    model = get_stt_model(config)

    # Parse header values from request headers
    num_channels = int(request.headers.get("x-audio-channel", 1))
    sample_rate = int(request.headers.get("x-audio-sample-rate", 16000))
    bits_per_sample = int(request.headers.get("x-audio-bits", 16))
    data_size = int(request.headers.get("content-length", 0))

    # Create WAV header
    wav_header = create_wav_header(
        num_channels, sample_rate, bits_per_sample, data_size
    )

    # PCM data received
    audio_data = await request.body()

    # Combine WAV header and audio data
    combined_buffer = wav_header + audio_data

    # Transcribe audio
    segments, info = model.transcribe(
        BytesIO(combined_buffer), beam_size=5, language=config.language
    )

    return JSONResponse(
        {
            "language": info.language,
            "text": ". ".join([str(segment.text).strip() for segment in segments]),
        }
    )


@app.get("/api/tts")
async def tts(text: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://translate.google.com/translate_tts",
            params={"ie": "UTF-8", "tl": "en-US", "client": "tw-ob", "q": text[0:200]},
        )

        return Response(resp.content, media_type="audio/mpeg")
