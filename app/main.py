from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import assistant, config, ratelimit, sessions
from .kb import get_kb_text, get_system_prompt, public_config, get_rules
from .logger import log_chat, log_error
from .safety import emergency_reply, is_emergency

app = FastAPI(title="Vizag Care AI Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


class ChatOut(BaseModel):
    answer: str
    session_id: str
    emergency: bool = False


def client_ip(request: Request) -> str:
    if config.TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.on_event("startup")
def warm_up() -> None:
    get_kb_text()
    get_system_prompt()


@app.get("/health")
def health():
    return {"status": "ok", "model": config.LLAMA_MODEL, "api_key_set": bool(config.LLAMA_API_KEY)}


@app.get("/config")
def get_config():
    return public_config()


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, request: Request):
    text = (body.message or "").strip()
    if not text:
        raise HTTPException(400, "Message is empty.")
    if len(text) > config.MAX_MESSAGE_CHARS:
        raise HTTPException(400, f"Message is too long (maximum {config.MAX_MESSAGE_CHARS} characters).")

    sid = sessions.normalize_session_id(body.session_id)
    if not (ratelimit.allow(f"ip:{client_ip(request)}", config.RATE_LIMIT_PER_MINUTE)
            and ratelimit.allow(f"sid:{sid}", config.RATE_LIMIT_PER_MINUTE)):
        raise HTTPException(429, "Too many messages. Please wait a minute and try again.")

    # 1. Emergency check runs before the model
    if is_emergency(text):
        answer = emergency_reply(text)
        sessions.add_exchange(sid, text, answer)
        log_chat(sid, text, answer, answered=True, emergency=True)
        return ChatOut(answer=answer, session_id=sid, emergency=True)

    # 2. Ask the model
    try:
        answer, answered = assistant.ask(text, sessions.get_history(sid))
    except Exception as e:  # network, auth, provider outage
        log_error(sid, repr(e))
        raise HTTPException(502, "The assistant is unavailable right now.")

    if not answer:
        answer = get_rules()["fallback_phrase"]
        answered = False

    sessions.add_exchange(sid, text, answer)
    log_chat(sid, text, answer, answered)
    return ChatOut(answer=answer, session_id=sid)
