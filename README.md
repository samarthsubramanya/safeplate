# SafePlate 🍽️

Snap a restaurant menu and SafePlate tells your friend which dishes to **avoid**, which to **ask about**, and which **look safe** for their allergies. It also hands them the exact question to ask the server.

Gemma 3 does the work. It reads the menu photo itself (vision) and runs **locally through Ollama**. Nothing leaves the laptop: no API key, no cloud, no cost.

## Run it (2 commands)

```bash
ollama pull gemma3:4b
```

```bash
python3 app.py
```

Then open http://localhost:8000. You need Python 3.9+ and nothing else, because the app uses only the standard library.

To use it from a phone at the table, connect the phone to the same Wi‑Fi and open `http://<laptop-ip>:8000`. The camera button opens the phone's camera.

## Deploy to Render (free)

Render's free tier has no GPU, so the hosted version calls the **same Gemma family through Google's Gemini API** (`gemma-4-26b-a4b-it`, which has a free tier) instead of local Ollama.

1. Push this folder to a GitHub repo.
2. In Render, choose **New → Blueprint** and pick the repo. It reads `render.yaml`.
3. Paste `GEMINI_API_KEY` (from https://aistudio.google.com/apikey) and optionally `ELEVENLABS_API_KEY`.
4. Open the URL and log in as user `friend` with the generated `APP_PASSWORD` (find it under Environment in Render).

Free instances sleep after 15 idle minutes, so the first request afterwards takes ~1 min. Profile edits made in the UI reset on redeploy; change `profile.json` in the repo to make them permanent.

## How it works

```
phone camera ─► index.html (resizes to 1280px) ─► app.py ─┬─► Ollama /api/chat (gemma3:4b, local)       ← default
                                                          └─► Gemini API (gemma-4-26b-a4b-it, hosted)       ← if GEMINI_API_KEY
                                                     ─► keyword safety net ─► sorted verdicts
"Read it to me" ─► /speak ─► ElevenLabs TTS (if ELEVENLABS_API_KEY) or the browser's own voice (offline)
```

- **Structured output:** Ollama's `format` field holds Gemma to a JSON schema, so every dish comes back with `verdict` set to `safe`, `ask` or `avoid`.
- **Safety net:** a small model can miss things. If a dish's menu text contains any keyword from the profile (`satay` → peanuts, `pesto` → tree nuts), it is forced to **avoid**, whatever the model said. A verdict the app doesn't recognise falls back to **ask**, never to safe.
- **Profile:** `profile.json` holds the name, the allergens with their keywords, and free-text notes. You can edit it in the UI.

## Config

| env var | default |
|---|---|
| `GEMINI_API_KEY` | unset → local Ollama. Set → hosted Gemma |
| `ELEVENLABS_API_KEY` | unset → browser speech. Set → ElevenLabs voice |
| `ELEVENLABS_VOICE` | `JBFqnCBsd6RMkjVDRZzb` |
| `APP_PASSWORD` | unset → no login. **Set it on any public URL** (user `friend`) |
| `MODEL` | `gemma3:4b` locally, `gemma-4-26b-a4b-it` hosted (try `gemma3:12b` for better accuracy, or `gemma3:1b` with pasted text only) |
| `OLLAMA_URL` | `http://localhost:11434` |
| `PORT` | `8000` |

## Test

```bash
python3 test_app.py
```

> AI can miss things. SafePlate is a second pair of eyes, not a replacement for asking staff or carrying medication.
