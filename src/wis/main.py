
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wis.config import SttConfig, TtsConfig
from wis.stt import AudioInfo, get_stt_model, get_text
from wis.tts import to_speech

stt_config = SttConfig()
tts_config = TtsConfig()

get_stt_model(
        stt_config.stt_whisper_model_id, 
        stt_config.stt_whisper_device, 
        stt_config.stt_whisper_compute_type)
  # warm up the model; will download on demand
app = FastAPI()


@app.post("/api/willow")
async def willow(request: Request):

    audio_info = AudioInfo(
        num_channels=int(request.headers.get("x-audio-channel", 1)),
        sample_rate=int(request.headers.get("x-audio-sample-rate", 16000)),
        bits_per_sample=int(request.headers.get("x-audio-bits", 16)),
        data_size=int(request.headers.get("content-length", 0)),
    )
    
    result = get_text(await request.body(), audio_info, stt_config)
    return JSONResponse(
        {
            "language": result.language,
            "text": result.text
        }
    )


@app.get("/api/tts")
async def tts(text: str):
    return await to_speech(text, tts_config)
