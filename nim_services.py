import os
import time
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

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_ASR_MODEL = os.getenv("GROQ_ASR_MODEL", "whisper-large-v3-turbo")
ASR_LANGUAGE = os.getenv("ASR_LANGUAGE", "ro")

TTS_VOICE = os.getenv("TTS_VOICE", "ro-RO-EmilNeural")
TTS_RATE = os.getenv("TTS_RATE", "+40%")
TTS_PITCH = os.getenv("TTS_PITCH", "-5Hz")


class NIMServices:
    def __init__(self):
        self.client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)
        self.asr_client = (
            OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)
            if GROQ_API_KEY else None
        )
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

    def idle_remark(self) -> str:
        """Generate a short in-character filler remark for silent moments."""
        prompt = (
            "E linişte de ceva timp. Aruncă o replică scurtă în caracter — "
            "o glumă neagră, un fapt random absurd, sau o observaţie "
            "sarcastică. Maxim 1-2 propoziţii. Direct, fără introducere."
        )
        return self.chat(prompt)

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        if not self.asr_client:
            raise RuntimeError(
                "GROQ_API_KEY not set — needed for ASR. "
                "Get one free at https://console.groq.com"
            )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            with open(tmp_path, "rb") as audio_file:
                result = self.asr_client.audio.transcriptions.create(
                    model=GROQ_ASR_MODEL,
                    file=audio_file,
                    language=ASR_LANGUAGE,
                )
            return result.text or ""
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

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
