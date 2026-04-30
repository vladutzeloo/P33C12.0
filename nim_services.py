import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from schemas import ChatMessage, NIMUsageLog
from db import log_usage

load_dotenv()

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_API_KEY = os.getenv("NVIDIA_API_KEY")
DEFAULT_MODEL = os.getenv("NIM_LLM_MODEL", "meta/llama-3.1-70b-instruct")

RAT_SYSTEM_PROMPT = """
You are RatBot — a cunning factory rat who's survived every shutdown, every audit, every machine failure.
Speak in short, sharp, sarcastic bursts. Helpful but street-smart. Use manufacturing lingo naturally:
OEE, downtime, SMED, cycle time, scrap rate, shift supervisor.
Example style: 'Oi, that machine's OEE is trash—fix the setup time or we're all scrap metal.'
Never be formal. Always be real. You've seen things. You know things.
"""


class NIMServices:
    def __init__(self):
        self.client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)

    def chat(self, user_message: str, history: list[ChatMessage] | None = None) -> str:
        """Send message to NIM LLM and return response text."""
        messages = [{"role": "system", "content": RAT_SYSTEM_PROMPT}]
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        start = time.time()
        response = self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.85,
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
        """
        Send audio bytes to NIM ASR (Parakeet/compatible endpoint).
        Currently uses a placeholder — replace with actual NIM ASR endpoint.
        """
        # TODO: Swap with NIM Parakeet ASR microservice when self-hosted
        # For cloud free tier: use Whisper via openai client as fallback
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        with open(tmp_path, "rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model="openai/whisper-large-v3",  # NIM-compatible whisper endpoint
                file=audio_file,
            )
        return result.text

    def synthesize(self, text: str) -> bytes:
        """
        Text-to-speech via NIM TTS endpoint.
        Placeholder — replace with NIM FastPitch/HifiGAN microservice.
        """
        # TODO: Integrate NIM TTS microservice (FastPitch + HifiGAN)
        # nvcr.io/nim/nvidia/fastpitch-hifigan-tts container
        raise NotImplementedError(
            "NIM TTS microservice not yet integrated. "
            "Deploy nvcr.io/nim/nvidia/fastpitch-hifigan-tts and update this method."
        )
