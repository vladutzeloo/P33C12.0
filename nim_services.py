import os
import time
import asyncio
import tempfile
import edge_tts
from openai import OpenAI
from dotenv import load_dotenv
from schemas import ChatMessage, NIMUsageLog
from db import log_usage
from persona import build_system_prompt

load_dotenv()

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_API_KEY = os.getenv("NVIDIA_API_KEY")
DEFAULT_MODEL = os.getenv("NIM_LLM_MODEL", "meta/llama-3.1-70b-instruct")

TTS_VOICE = os.getenv("TTS_VOICE", "ro-RO-EmilNeural")
TTS_RATE = os.getenv("TTS_RATE", "+40%")
TTS_PITCH = os.getenv("TTS_PITCH", "-5Hz")


class NIMServices:
    def __init__(self):
        self.client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)
        self.system_prompt = build_system_prompt()

    def chat(self, user_message: str, history: list[ChatMessage] | None = None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        start = time.time()
        response = self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            max_tokens=80,
            temperature=0.9,
        )
        elapsed = round(time.time() - start, 3)

        usage = response.usage
        log_usage(NIMUsageLog(
            model=DEFAULT_MODEL,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            latency_sec=elapsed,
            endpoint="chat",
        ))

        return response.choices[0].message.content

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        with open(tmp_path, "rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model="openai/whisper-large-v3",
                file=audio_file,
            )
        return result.text

    async def synthesize_to_file(self, text: str) -> str:
        """Generate TTS audio with edge-tts, return path to mp3 file."""
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        communicate = edge_tts.Communicate(
            text,
            voice=TTS_VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
        )
        await communicate.save(tmp.name)
        return tmp.name

    def synthesize_sync(self, text: str) -> str:
        return asyncio.run(self.synthesize_to_file(text))
