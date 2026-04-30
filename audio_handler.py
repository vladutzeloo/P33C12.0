import asyncio
import io
import os
import wave
from collections import deque, defaultdict
import discord
import discord.opus
from discord.ext import voice_recv
from nim_services import NIMServices
from schemas import ChatMessage


# Patch discord.opus.Decoder.decode so a corrupted packet doesn't kill
# the voice_recv router thread — known instability in the alpha lib.
_SILENCE_FRAME = b"\x00" * 3840  # 20ms @ 48kHz stereo 16-bit
_orig_opus_decode = discord.opus.Decoder.decode


def _safe_opus_decode(self, data, fec=False):
    try:
        return _orig_opus_decode(self, data, fec=fec)
    except discord.opus.OpusError:
        return _SILENCE_FRAME


discord.opus.Decoder.decode = _safe_opus_decode


SILENCE_THRESHOLD = 500   # ms of silence before processing
MIN_AUDIO_LEN = 0.6       # seconds minimum for valid audio
HISTORY_TURNS = 6         # rolling per-user message buffer (user+assistant pairs)


class AudioSink(voice_recv.AudioSink):
    """Custom sink to capture raw PCM audio from Discord voice."""

    def __init__(self):
        self.buffer: dict[int, list[bytes]] = {}

    def write(self, user: discord.User, data: voice_recv.VoiceData):
        uid = user.id if user else 0
        if uid not in self.buffer:
            self.buffer[uid] = []
        self.buffer[uid].append(data.pcm)

    def wants_opus(self) -> bool:
        return False

    def cleanup(self):
        self.buffer.clear()


class AudioHandler:
    def __init__(self):
        self.history: dict[int, deque[ChatMessage]] = defaultdict(
            lambda: deque(maxlen=HISTORY_TURNS * 2)
        )

    def pcm_to_wav(self, pcm_data: bytes, channels: int = 2, rate: int = 48000) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    async def speak(self, vc: discord.VoiceClient, nim: NIMServices, text: str):
        """Synthesize text and play it through the voice client."""
        path = await nim.synthesize_to_file(text)
        if vc.is_playing():
            vc.stop()
        source = discord.FFmpegPCMAudio(path)
        done = asyncio.Event()
        loop = asyncio.get_running_loop()

        def after(err):
            loop.call_soon_threadsafe(done.set)
            try:
                os.remove(path)
            except OSError:
                pass

        vc.play(source, after=after)
        await done.wait()

    async def listen_and_respond(self, vc: discord.VoiceClient, nim: NIMServices):
        sink = AudioSink()
        vc.listen(sink)

        print("[AudioHandler] Listening...")
        await asyncio.sleep(SILENCE_THRESHOLD / 1000)

        while vc.is_connected():
            await asyncio.sleep(2)

            for user_id, chunks in list(sink.buffer.items()):
                if not chunks:
                    continue

                pcm = b"".join(chunks)
                sink.buffer[user_id] = []

                duration = len(pcm) / (48000 * 2 * 2)
                print(f"[AudioHandler] buffered {duration:.2f}s from {user_id}")
                if duration < MIN_AUDIO_LEN:
                    continue

                wav_bytes = self.pcm_to_wav(pcm)

                try:
                    loop = asyncio.get_running_loop()
                    transcript = await loop.run_in_executor(
                        None, nim.transcribe, wav_bytes
                    )
                    print(f"[ASR] {user_id}: {transcript}")

                    if not transcript.strip():
                        continue

                    user_history = list(self.history[user_id])
                    response_text = await loop.run_in_executor(
                        None, lambda: nim.chat(transcript, history=user_history)
                    )
                    print(f"[LLM] {response_text}")

                    self.history[user_id].append(
                        ChatMessage(role="user", content=transcript)
                    )
                    self.history[user_id].append(
                        ChatMessage(role="assistant", content=response_text)
                    )

                    await self.speak(vc, nim, response_text)

                except Exception as e:
                    print(f"[AudioHandler] Error: {e}")
