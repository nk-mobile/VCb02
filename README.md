## Telegram бот с GigaChat (Python, telebot)
<img width="548" height="524" alt="Выделение_927" src="https://github.com/user-attachments/assets/0036aa69-b28d-4c8d-a42d-76e18914f3cb" />

### Возможности
- Приветствие при старте (`/start`).
- Выбор модели GigaChat из списка.
- Отправка каждого сообщения пользователя в GigaChat и возврат ответа.
- Поддержка контекста диалога (история сообщений в памяти процесса).
- Обработка ошибок: при недоступности API — сообщение «Сервис временно недоступен, попробуйте позже».
- Логирование запросов и ответов в консоль.

### Требования
- Python 3.10+
- Аккаунт Telegram-бота (токен от BotFather)
- Ключ API GigaChat

### Установка
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Конфигурация (.env)
Создайте файл `.env` в корне проекта :
```env
TELEGRAM_BOT_TOKEN=ваш_токен_телеграм
GIGACHAT_API_KEY=ваш_ключ_gigachat

# Необязательно
# GIGACHAT_SCOPE=GIGACHAT_API_PERS
# GIGACHAT_MODEL=GigaChat
# GIGACHAT_CA_BUNDLE_FILE=/abs/path/to/russian_trusted_root_ca_pem.crt
# LOG_LEVEL=INFO  # DEBUG для детальной отладки
```

Переменные автоматически загружаются через `python-dotenv`.

### Запуск
```bash
source .venv/bin/activate
python bot.py
```

После запуска отправьте боту `/start`, выберите модель и напишите сообщение.

### Структура
- `bot.py` — основной файл бота (telebot), выбор модели, контекст, логирование, обработка ошибок.
- `get_token.py` — фабрика клиента GigaChat: `create_gigachat_client(model)`; подхватывает ключ из `.env`.

### Замечания по контексту
- История диалога хранится в памяти процесса и очищается при перезапуске. Для продакшена можно заменить на Redis/БД.

### Отладка
- Включите детальные логи:
```bash
export LOG_LEVEL=DEBUG
python bot.py
```

Или укажите `LOG_LEVEL=DEBUG` в `.env`.

Если увидите ошибки в сигнатуре методов SDK (`ValidationError: messages field required` и т.п.), включите DEBUG-логи и пришлите несколько строк — бот уже пробует разные сигнатуры `chat(...)`/`generate(...)`, при необходимости подстроим парсинг под вашу версию `gigachat`.

### Возможные доработки
- Кнопки/команды телеграм (inline/reply) для выбора настроек.
- Персистентное хранение контекста (Redis/DB) и ограничение длины истории.
- Админ-команды, метрики, хелсчеки.


