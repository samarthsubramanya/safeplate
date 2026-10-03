"""SafePlate: snap a menu, get allergy verdicts from a local Gemma 3. Stdlib only."""
import base64, json, os, re, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
PROFILE = HERE / "profile.json"
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")  # set -> hosted Gemma (Render); unset -> local Ollama
MODEL = os.environ.get("MODEL", "gemma-3-27b-it" if GEMINI_KEY else "gemma3:4b")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
VOICE = os.environ.get("ELEVENLABS_VOICE", "JBFqnCBsd6RMkjVDRZzb")
PASSWORD = os.environ.get("APP_PASSWORD")  # set it on any public deploy
RANK = {"safe": 0, "ask": 1, "avoid": 2}

SCHEMA = {
    "type": "object",
    "properties": {"dishes": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "menu_text": {"type": "string"},
            "verdict": {"type": "string", "enum": ["safe", "ask", "avoid"]},
            "reason": {"type": "string"},
            "ask_server": {"type": "string"},
        },
        "required": ["name", "menu_text", "verdict", "reason", "ask_server"],
    }}},
    "required": ["dishes"],
}


def load_profile():
    return json.loads(PROFILE.read_text())


def build_prompt(profile, menu_text):
    allergens = ", ".join(profile["allergens"])
    src = f"Menu text:\n{menu_text}" if menu_text else "The menu is in the attached photo."
    return (
        f"You help {profile['name']}, who is allergic to: {allergens}. Notes: {profile.get('notes', '')}\n"
        f"{src}\n\nFor EVERY dish on the menu return: name, menu_text (the dish's description exactly as written), "
        "verdict ('avoid' if it clearly contains an allergen, 'ask' if it might via sauces, oils, cross-contact "
        "or the cuisine commonly uses it, 'safe' only if you are confident), a short reason, and ask_server "
        "(one polite question to confirm with staff, or empty string if safe). When unsure, choose 'ask'."
    )


def safety_net(dishes, profile):
    """Never trust the model alone: any dish whose text names an allergen keyword is forced to 'avoid'."""
    for d in dishes:
        text = f"{d.get('name', '')} {d.get('menu_text', '')}".lower()
        hits = [a for a, words in profile["allergens"].items() if any(w.lower() in text for w in words)]
        if hits and d.get("verdict") != "avoid":
            d["verdict"] = "avoid"
            d["reason"] = f"Menu text mentions {', '.join(hits)}. " + d.get("reason", "")
            d["flagged_by"] = "keyword safety net"
        if d.get("verdict") not in RANK:
            d["verdict"] = "ask"  # unknown verdict = don't claim safe
    return sorted(dishes, key=lambda d: -RANK[d["verdict"]])


def post(url, payload, headers):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def parse_dishes(text):
    """Hosted Gemma has no JSON mode, so pull the first {...} block out of whatever it wrote."""
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))["dishes"]


def ask_gemma(prompt, image_b64=None):
    if GEMINI_KEY:
        parts = [{"text": prompt + "\n\nReply with ONLY JSON matching this schema:\n" + json.dumps(SCHEMA)}]
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
        out = json.loads(post(url, {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0}},
                              {"x-goog-api-key": GEMINI_KEY}))
        return parse_dishes(out["candidates"][0]["content"]["parts"][0]["text"])
    msg = {"role": "user", "content": prompt}
    if image_b64:
        msg["images"] = [image_b64]
    out = post(f"{OLLAMA}/api/chat", {"model": MODEL, "messages": [msg], "format": SCHEMA, "stream": False,
                                      "options": {"temperature": 0}}, {})
    return json.loads(json.loads(out)["message"]["content"])["dishes"]


def speak(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128"
    return post(url, {"text": text[:2500], "model_id": "eleven_flash_v2_5"}, {"xi-api-key": ELEVEN_KEY})


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, data, ctype="application/json"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

    def _authed(self):
        if not PASSWORD:
            return True
        want = "Basic " + base64.b64encode(f"friend:{PASSWORD}".encode()).decode()
        if self.headers.get("Authorization") == want:
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="SafePlate"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        if not self._authed():
            return
        if self.path == "/profile":
            return self._send(200, load_profile())
        self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        if not self._authed():
            return
        try:
            data = self._json()
            if self.path == "/speak":
                if not ELEVEN_KEY:
                    return self._send(501, {"error": "no ElevenLabs key; browser voice is used instead"})
                return self._send(200, speak(data.get("text", "")), "audio/mpeg")
            if self.path == "/profile":
                if not isinstance(data.get("name"), str) or not isinstance(data.get("allergens"), dict):
                    return self._send(400, {"error": "profile needs name and allergens"})
                PROFILE.write_text(json.dumps(data, indent=2))  # ponytail: ephemeral on Render free tier, resets on redeploy; use a disk/DB if edits must stick
                return self._send(200, data)
            if self.path == "/check":
                if not data.get("image") and not data.get("text", "").strip():
                    return self._send(400, {"error": "send a menu photo or paste menu text"})
                profile = load_profile()
                dishes = ask_gemma(build_prompt(profile, data.get("text", "")), data.get("image"))
                return self._send(200, {"dishes": safety_net(dishes, profile), "model": MODEL})
            self._send(404, {"error": "not found"})
        except Exception as e:  # surface Ollama-not-running etc. to the UI
            self._send(500, {"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"SafePlate on http://localhost:{port} using {MODEL} via {'Gemini API' if GEMINI_KEY else 'Ollama'}"
          f", voice: {'ElevenLabs' if ELEVEN_KEY else 'browser'}, password: {'on' if PASSWORD else 'off'}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
