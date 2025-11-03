import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

class Config:
    """Конфигурация приложения"""
    
    # Настройки бота
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ALLOWED_USERS_IDS = [int(x.strip()) for x in os.getenv("ALLOWED_USERS_IDS", "").split(",") if x.strip()]
    
    # Настройки RCON
    RCON_HOST = os.getenv("RCON_HOST", "localhost")
    RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
    RCON_PASSWORD = os.getenv("RCON_PASSWORD")
    
    # Валидация обязательных полей
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.ALLOWED_USERS_IDS:
            raise ValueError("ALLOWED_USERS_IDS не установлены в .env файле")
        if not cls.RCON_PASSWORD:
            raise ValueError("RCON_PASSWORD не установлен в .env файле")

# Проверяем конфигурацию при импорте
Config.validate()