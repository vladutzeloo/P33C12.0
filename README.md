# P33C1 2.0 — Discord NIM Voice Bot

A cunning Discord voice AI chatbot powered by **NVIDIA NIM** APIs.
RatBot joins your voice channel, listens, transcribes speech, generates responses with a rat-factory personality, and (soon) speaks back via NIM TTS.

---

## Stack
- Python 3.12, discord.py, discord-ext-voice-recv
- NVIDIA NIM (LLM: Llama 3.1 70B, ASR: Whisper, TTS: FastPitch coming soon)
- SQLite for token usage tracking
- Pydantic v2 for schemas

---

## Setup

### 1. Clone and install
```bash
git clone https://github.com/vladutzeloo/P33C12.0.git
cd P33C12.0
pip install -r requirements.txt
```

### 2. Create .env
```bash
cp .env.example .env
# Fill in DISCORD_TOKEN and NVIDIA_API_KEY
```

### 3. Discord Bot Setup
- Go to [discord.com/developers](https://discord.com/developers/applications)
- Create new app → Bot → Enable **Message Content Intent** + **Voice** permissions
- Invite URL scopes: `bot`, permissions: `Connect`, `Speak`, `Read Messages`

### 4. Run
```bash
python bot.py
```

Or with Docker:
```bash
docker build -t p33c12 .
docker run --env-file .env p33c12
```

---

## Commands
| Command | Action |
|---|---|
| `!voice` | RatBot joins your voice channel |
| `!leave` | RatBot disconnects |

---

## Roadmap
- [x] Discord voice capture + ASR
- [x] NIM LLM with rat personality
- [x] Token usage logging (SQLite)
- [ ] NIM TTS (FastPitch-HifiGAN microservice)
- [ ] Speaker diarization (multi-user)
- [ ] Web dashboard for token stats
- [ ] Pipecat integration for advanced pipeline

---

## NIM Models Used
| Purpose | Model |
|---|---|
| Chat/LLM | `meta/llama-3.1-70b-instruct` |
| ASR | `openai/whisper-large-v3` (via NIM) |
| TTS | `nvidia/fastpitch-hifigan` (self-hosted, coming) |
