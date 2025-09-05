from gigachat import GigaChat
import os
from typing import Optional
from dotenv import load_dotenv

# === Загружаем переменные из .env ===
load_dotenv()

# === Получаем переменные окружения ===
# Предпочитаем переменную GIGACHAT_API_KEY (как указано в ТЗ),
# но сохраняем обратную совместимость с AUTHORIZATION_KEY
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY") or os.getenv("AUTHORIZATION_KEY")

DEFAULT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
DEFAULT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")
CA_BUNDLE_FILE = os.getenv("GIGACHAT_CA_BUNDLE_FILE", "russian_trusted_root_ca_pem.crt")


def create_gigachat_client(model: Optional[str] = None) -> GigaChat:
    """Создает и возвращает клиент GigaChat.

    Аргументы:
        model: имя модели GigaChat. Если не указано, используется DEFAULT_MODEL.

    Возвращает:
        Экземпляр GigaChat, готовый к использованию.
    """
    if not GIGACHAT_API_KEY:
        raise RuntimeError(
            "GigaChat API key is not set. Please set GIGACHAT_API_KEY in environment."
        )

    selected_model = model or DEFAULT_MODEL

    # ca_bundle_file опционален: используем, только если файл существует
    ca_bundle_file = CA_BUNDLE_FILE if CA_BUNDLE_FILE and os.path.isfile(CA_BUNDLE_FILE) else None

    # Возвращаем клиент. В коде, где используется, предпочтительно применять контекстный менеджер
    # with create_gigachat_client(model) as giga: ...
    return GigaChat(
        credentials=GIGACHAT_API_KEY,
        scope=DEFAULT_SCOPE,
        model=selected_model,
        ca_bundle_file=ca_bundle_file,
    )


__all__ = [
    "create_gigachat_client",
    "GIGACHAT_API_KEY",
    "DEFAULT_SCOPE",
    "DEFAULT_MODEL",
]
