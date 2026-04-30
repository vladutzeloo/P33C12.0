import asyncio
import io
import wave
import discord
from discord.ext import voice_recv
from nim_services import NIMServices


SILENCE_THRESHOLD = 500   # ms of silence before processing
MIN_AUDIO_LEN = 1.0       # seconds minimum for valid audio


class AudioSink(voice_recv.AudioSink):
    """Custom sink to capture raw PCM audio from Discord voice."""

    def __init__(self):
        self.buffer: dict[int, list[bytes]] = {}  # user_id -> chunks

    def write(self, user: discord.User, data: voice_recv.VoiceData):
        uid = user.id if user else 0
        if uid not in self.buffer:
            self.buffer[uid] = []
        self.buffer[uid].append(data.pcm)

    def cleanup(self):
        self.buffer.clear()


class AudioHandler:
    def pcm_to_wav(self, pcm_data: bytes, channels: int = 2, rate: int = 48000) -> bytes:
        """Convert raw PCM to WAV bytes for NIM ASR."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    async def listen_and_respond(self, vc: discord.VoiceClient, nim: NIMServices):
        """
        Main voice loop:
        1. Capture audio via AudioSink
        2. Transcribe with NIM ASR
        3. Generate response with NIM LLM (rat personality)
        4. Synthesize and play back via TTS
        """
        sink = AudioSink()
        vc.listen(sink)  # requires discord-ext-voice-recv

        print("[AudioHandler] Listening...")
        await asyncio.sleep(SILENCE_THRESHOLD / 1000)

        while vc.is_connected():
            await asyncio.sleep(2)  # poll interval

            for user_id, chunks in list(sink.buffer.items()):
                if not chunks:
                    continue

                pcm = b"".join(chunks)
                sink.buffer[user_id] = []

                # Skip if too short
                duration = len(pcm) / (48000 * 2 * 2)  # bytes / (rate * channels * width)
                if duration < MIN_AUDIO_LEN:
                    continue

                wav_bytes = self.pcm_to_wav(pcm)

                try:
                    transcript = nim.transcribe(wav_bytes)
                    print(f"[ASR] {user_id}: {transcript}")

                    if not transcript.strip():
                        continue

                    response_text = nim.chat(transcript)
                    print(f"[LLM] RatBot: {response_text}")

                    # TODO: Replace with NIM TTS when available
                    # tts_audio = nim.synthesize(response_text)
                    # vc.play(discord.FFmpegPCMAudio(io.BytesIO(tts_audio), pipe=True))

                    # Fallback: print to console (enable TTS when microservice ready)
                    print(f"[TTS PENDING] Would say: {response_text}")

                except Exception as e:
                    print(f"[AudioHandler] Error: {e}")
