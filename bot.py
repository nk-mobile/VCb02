import os
import logging
import inspect
from typing import Dict, List, Any

from dotenv import load_dotenv
import telebot
from telebot import types

from get_token import create_gigachat_client, DEFAULT_MODEL


# === Load environment ===
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment variables")


# === Logging ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bot")


# === Telegram bot ===
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)


# === Simple in-memory session storage for context and selected model ===
UserHistory = List[Dict[str, str]]
user_sessions: Dict[int, Dict[str, Any]] = {}


def get_or_create_session(chat_id: int) -> Dict[str, Any]:
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"model": DEFAULT_MODEL, "history": []}  # type: ignore
    return user_sessions[chat_id]


def list_models() -> List[str]:
    # Try to fetch available models from the API. If fails, return a safe default list.
    try:
        with create_gigachat_client() as giga:
            # Some SDKs expose models list as attribute or method; try both.
            models_attr = getattr(giga, "models", None)
            if isinstance(models_attr, list) and models_attr:
                return [str(m) for m in models_attr]
            # Fallback: attempt method call if available
            get_models = getattr(giga, "get_models", None)
            if callable(get_models):
                models = get_models()
                # Normalize to list[str]
                if isinstance(models, list) and models:
                    return [str(m) for m in models]
    except Exception as exc:
        logger.warning("Failed to list models from GigaChat: %s", exc)
    # Fallback default choices
    return [DEFAULT_MODEL, "GigaChat-Pro", "GigaChat-Plus"]


def chat_with_gigachat(model: str, history: UserHistory) -> str:
    # history is a list of dicts like {"role": "user"|"assistant"|"system", "content": "..."}
    try:
        with create_gigachat_client(model=model) as giga:
            # Many chat SDKs accept OpenAI-like payload: messages=[{"role":..., "content": ...}]
            # Try common call flow; adjust if your SDK differs.
            logger.info("➡️ Request to GigaChat | model=%s | messages=%s", model, history)
            chat_fn = getattr(giga, "chat", None) or getattr(giga, "completions", None)
            if callable(chat_fn):
                logger.debug("Using chat-like API: %s", getattr(chat_fn, "__name__", "chat"))
                response = None
                last_error: Exception | None = None

                try:
                    sig = inspect.signature(chat_fn)
                    param_names = list(sig.parameters.keys())
                except Exception:
                    param_names = []

                # 1) Direct messages kwarg
                if "messages" in param_names:
                    try:
                        logger.debug("Call chat with messages kwarg")
                        response = chat_fn(messages=history, model=model) if "model" in param_names else chat_fn(messages=history)
                    except Exception as e:
                        last_error = e

                # 2) Request-like single object (pydantic Chat)
                if response is None and ("request" in param_names or "body" in param_names or len(param_names) == 1):
                    try:
                        logger.debug("Attempt request/body Chat model path")
                        ChatModel = None
                        # Try common import paths dynamically
                        try:
                            from gigachat.models.chat import Chat as ChatModel  # type: ignore
                        except Exception:
                            try:
                                from gigachat.schemas.chat import Chat as ChatModel  # type: ignore
                            except Exception:
                                ChatModel = None

                        if ChatModel is not None:
                            request_obj = ChatModel(messages=history, model=model)
                        else:
                            request_obj = {"messages": history, "model": model}

                        if "request" in param_names:
                            response = chat_fn(request=request_obj)
                        elif "body" in param_names:
                            response = chat_fn(body=request_obj)
                        else:
                            # Single positional parameter
                            response = chat_fn(request_obj)
                    except Exception as e:
                        last_error = e

                # 3) Other common kwargs
                if response is None:
                    for kwargs in (
                        {"messages_list": history, "model": model},
                        {"dialog_messages": history, "model": model},
                        {"model": model},
                    ):
                        try:
                            logger.debug("Attempt chat call with kwargs=%s", kwargs)
                            response = chat_fn(**kwargs)
                            break
                        except Exception as e:
                            last_error = e
                            continue

                # 4) Positional fallbacks
                if response is None:
                    for args in ((history, model), (history,)):
                        try:
                            logger.debug("Attempt chat call with positional args=%s", args)
                            response = chat_fn(*args)
                            break
                        except Exception as e:
                            last_error = e
                            continue

                if response is None and last_error is not None:
                    raise last_error
            else:
                # Fallback: try generate-like API
                generate_fn = getattr(giga, "generate", None)
                if not callable(generate_fn):
                    raise RuntimeError("GigaChat client does not expose chat/generate methods")
                # Compose a single prompt using history as plain text
                prompt = "\n".join([
                    f"{m['role']}: {m['content']}" for m in history
                ])
                logger.debug("Using generate-like API: %s", getattr(generate_fn, "__name__", "generate"))
                response = generate_fn(prompt=prompt, model=model)

            # Try to normalize common response structures
            logger.debug("Raw response type=%s value=%s", type(response), response)
            if isinstance(response, dict):
                # OpenAI-like structure
                try:
                    text = response["choices"][0]["message"]["content"]
                except Exception:
                    try:
                        text = response["choices"][0]["text"]
                    except Exception:
                        text = str(response)
            else:
                # Object-like response with .choices
                try:
                    choices = getattr(response, "choices", None)
                    if choices:
                        first = choices[0]
                        text = getattr(getattr(first, "message", first), "content", None) or getattr(first, "text", None)
                        if not text:
                            text = str(response)
                    else:
                        text = str(response)
                except Exception:
                    text = str(response)

            logger.info("⬅️ Response from GigaChat | text=%s", text)
            return text
    except Exception as exc:
        logger.exception("Error calling GigaChat: %s", exc)
        raise


@bot.message_handler(commands=["start"])
def handle_start(message: types.Message) -> None:
    session = get_or_create_session(message.chat.id)
    session["history"] = []

    models = list_models()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for model in models:
        keyboard.add(types.KeyboardButton(model))

    welcome = (
        "Привет! Я бот на базе GigaChat.\n\n"
        "Выберите модель ниже, затем отправьте вопрос."
    )
    bot.send_message(message.chat.id, welcome, reply_markup=keyboard)


@bot.message_handler(func=lambda m: m.text in set(list_models()))
def handle_model_selection(message: types.Message) -> None:
    session = get_or_create_session(message.chat.id)
    session["model"] = message.text
    bot.send_message(message.chat.id, f"Модель установлена: {message.text}. Можете задать вопрос.")


@bot.message_handler(content_types=["text"])
def handle_text(message: types.Message) -> None:
    session = get_or_create_session(message.chat.id)
    model: str = session.get("model", DEFAULT_MODEL)
    history: UserHistory = session.get("history", [])

    # Append user message to history
    history.append({"role": "user", "content": message.text})

    try:
        reply_text = chat_with_gigachat(model=model, history=history)
        # Append assistant reply to history
        history.append({"role": "assistant", "content": reply_text})
        bot.send_message(message.chat.id, reply_text)
    except Exception:
        bot.send_message(message.chat.id, "Сервис временно недоступен, попробуйте позже")


def main() -> None:
    logger.info("Starting Telegram bot...")
    # none_stop to keep polling, skip_pending allows immediate processing of new updates only
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=50)


if __name__ == "__main__":
    main()


