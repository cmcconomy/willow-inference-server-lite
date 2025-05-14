from functools import cache
from io import BytesIO
from typing import NamedTuple

from faster_whisper import WhisperModel
from pydantic import BaseModel

from wis.config import SttConfig


@cache
def get_stt_model(whisper_model_id: str, device: str, compute_type: str) -> WhisperModel:
    return WhisperModel(
        whisper_model_id, device=device, compute_type=compute_type
    )


class AudioInfo(BaseModel):
    num_channels: int = 1
    sample_rate: int = 16000
    bits_per_sample: int = 16
    data_size: int = 0


class SttResult(NamedTuple):
    text: str
    language: str


def get_text(audio_data: bytes, audio_info: AudioInfo, config: SttConfig ) -> SttResult:
    """
    Get text from audio data using the Whisper model.
    """
    formatted_audio_data = create_wav_header(audio_info) + audio_data
    model = get_stt_model(
        config.stt_whisper_model_id, 
        config.stt_whisper_device, 
        config.stt_whisper_compute_type)
    segments, info = model.transcribe(
        BytesIO(formatted_audio_data), beam_size=5, language=config.stt_whisper_language
    )
    text = ". ".join([str(segment.text).strip() for segment in segments])
    language = info.language
    return SttResult( text, language)


def create_wav_header(audio_info: AudioInfo) -> bytes:
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
    byte_rate = audio_info.sample_rate * audio_info.num_channels * audio_info.bits_per_sample // 8  # Byte rate
    block_align = audio_info.num_channels * audio_info.bits_per_sample // 8  # Block align

    # Data Chunk
    data = b"data"

    # Create a bytearray to hold the WAV header
    header = bytearray(44)  # Standard WAV header size

    # RIFF header
    header[0:4] = riff  # "RIFF"
    header[4:8] = (36 + audio_info.data_size).to_bytes(4, "little")  # File size minus 8
    header[8:12] = wave  # "WAVE"

    # Format chunk
    header[12:16] = fmt  # "fmt "
    header[16:20] = fmt_chunk_size.to_bytes(4, "little")  # Chunk size
    header[20:22] = audio_format.to_bytes(2, "little")  # Audio format
    header[22:24] = audio_info.num_channels.to_bytes(2, "little")  # Number of channels
    header[24:28] = audio_info.sample_rate.to_bytes(4, "little")  # Sample rate
    header[28:32] = byte_rate.to_bytes(4, "little")  # Byte rate
    header[32:34] = block_align.to_bytes(2, "little")  # Block align
    header[34:36] = audio_info.bits_per_sample.to_bytes(2, "little")  # Bits per sample

    # Data chunk
    header[36:40] = data  # "data"
    header[40:44] = audio_info.data_size.to_bytes(4, "little")  # Data size

    return header
