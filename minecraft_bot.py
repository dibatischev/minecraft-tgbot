import logging
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
import mcrcon

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MinecraftBot:
    def __init__(self):
        self.allowed_users = Config.ALLOWED_USERS_IDS
        self.bases_file = "bases.json"
        self.users_file = "users.json"
        self.times = ['day','noon','night','midnight']
        self.wheather = ['clear','rain','thunder']
        self.modes = ['survival','creative']
        self.difficulties = ['peaceful','easy', 'normal']
        # Загружаем данные
        self.bases = self._load_bases()
        self.users = self._load_users()
        
        logger.info(f"Бот инициализирован для {len(self.allowed_users)} пользователей")
        logger.info(f"Загружено {len(self.bases)} баз и {len(self.users)} пользователей")
    
    def _load_bases(self) -> dict:
        """Загружает базы из JSON файла"""
        try:
            with open(self.bases_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки баз: {e}")
            return {}
    
    def _load_users(self) -> dict:
        """Загружает пользователей из JSON файла"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
            return {}
    
    def _save_bases(self):
        """Сохраняет базы в JSON файл"""
        try:
            with open(self.bases_file, 'w', encoding='utf-8') as f:
                json.dump(self.bases, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения баз: {e}")
    
    def is_user_allowed(self, user_id: int) -> bool:
        return user_id in self.allowed_users
    
    def get_minecraft_nickname(self, user_id: int) -> str:
        """Получает никнейм Minecraft для пользователя"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            return self.users[user_id_str]["minecraft_nickname"]
        return "Player"  # fallback
    
    async def send_rcon_command(self, command: str) -> str:
        try:
            with mcrcon.MCRcon(Config.RCON_HOST, Config.RCON_PASSWORD, port=Config.RCON_PORT) as mcr:
                response = mcr.command(command)
                return response if response else "Команда выполнена"
        except Exception as e:
            return f"Ошибка RCON: {str(e)}"
    
    async def get_player_coordinates(self, player_nickname: str) -> str:
        """Получает координаты игрока"""
        try:
            with mcrcon.MCRcon(Config.RCON_HOST, Config.RCON_PASSWORD, port=Config.RCON_PORT) as mcr:
                # Команда для получения позиции игрока
                response = mcr.command(f"data get entity {player_nickname} Pos")
                return response
        except Exception as e:
            return f"Ошибка получения координат: {str(e)}"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("❌ Доступ запрещен!")
            return
        
        user_nickname = self.get_minecraft_nickname(update.effective_user.id)
        
        welcome_text = f"👋 Привет, {user_nickname}!\n\n"
        welcome_text += "🏠 Доступные базы для телепортации:\n"
        
        for cmd, base_info in self.bases.items():
            welcome_text += f"/{cmd} - {base_info['name']}: {base_info['coords']}\n"
        
        # Добавляем команду телепортации к папе для сына
        if update.effective_user.id == self._get_son_id():
            welcome_text += "\n👨‍👦 /topapa - Телепортироваться к папе"
        
        welcome_text += "\n🔄 /reload - Перезагрузить базы (только для админов)"
        
        await update.message.reply_text(welcome_text)
    
    def _get_son_id(self) -> int:
        """Получает ID сына (второй пользователь в списке)"""
        return self.allowed_users[1] if len(self.allowed_users) > 1 else None
    
    async def teleport_to_base(self, update: Update, context: ContextTypes.DEFAULT_TYPE, base_cmd: str):
        """Телепортирует на указанную базу"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("❌ Доступ запрещен!")
            return
        
        if base_cmd not in self.bases:
            await update.message.reply_text("❌ База не найдена!")
            return
        
        base_info = self.bases[base_cmd]
        user_nickname = self.get_minecraft_nickname(update.effective_user.id)
        
        response = await self.send_rcon_command(f"tp {user_nickname} {base_info['coords']}")
        await update.message.reply_text(
            f"➡️ Телепортация {user_nickname} на {base_info['name']}...\n"
        )
    async def game_mode_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
        """Включаем креативный режим"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("Access Denied")
            return
        user_nickname = self.get_minecraft_nickname(update.effective_user.id)
        response = await self.send_rcon_command(f"gamemode creative {user_nickname}")
        await update.message.reply_text (
            f"Включен {mode} режим для игрока {user_nickname}"
        )

    async def set_time (self, update: Update, context: ContextTypes.DEFAULT_TYPE, time: str):
        """Setting Time Globally"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("Access Denied")
            return
        response = await self.send_rcon_command(f"time set {time}")
        await update.message.reply_text(
            f"Time set to {time}"
        )
    async def set_difficulty(self, update: Update, context: ContextTypes.DEFAULT_TYPE, difficulty: str):
        """Set slozhnost"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("Access Denied")
            return
        response = await self.send_rcon_command(f"difficulty {difficulty}")
        await update.message.reply_text (
            f"Game Difficulty Set To {difficulty}"
        )
    async def set_weather (self, update: Update, context: ContextTypes.DEFAULT_TYPE, weather: str):
        """Set weather globally"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("Access Denied")
            return
        response = await self.send_rcon_command(f"/weather {weather}")
        await update.message.reply_text(
            f"Weather set to {weather}"
        )
    async def teleport_to_papa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Телепортирует сына к папе"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("❌ Доступ запрещен!")
            return
        
        # Проверяем, что команду вызывает сын
        son_id = self._get_son_id()
        if update.effective_user.id != son_id:
            await update.message.reply_text("❌ Эта команда только для сына!")
            return
        
        papa_id = self.allowed_users[0]  # Первый пользователь - папа
        papa_nickname = self.get_minecraft_nickname(papa_id)
        son_nickname = self.get_minecraft_nickname(son_id)
        
        # Телепортируем сына к папе
        response = await self.send_rcon_command(f"tp {son_nickname} {papa_nickname}")
        
        # Получаем координаты папы для информации
        papa_coords = await self.get_player_coordinates(papa_nickname)
        
        await update.message.reply_text(
            f"👨‍👦 Телепортация {son_nickname} к {papa_nickname}...\n"
        )
    
    async def reload_bases(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перезагружает список баз из файла"""
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("❌ Доступ запрещен!")
            return
        
        # Можно добавить проверку на админа, если нужно
        self.bases = self._load_bases()
        await update.message.reply_text(f"✅ Базы перезагружены! Доступно {len(self.bases)} баз")
    
    def create_handlers(self, app: Application):
        """Создаем обработчики для каждой базы"""
        # Обработчик для команды start
        app.add_handler(CommandHandler("start", self.start))
        
        # Обработчики для каждой базы
        for base_cmd in self.bases.keys():
            app.add_handler(CommandHandler(base_cmd, 
                lambda update, context, cmd=base_cmd: self.teleport_to_base(update, context, cmd)))
        
        # Специальные команды
        app.add_handler(CommandHandler("topapa", self.teleport_to_papa))
        app.add_handler(CommandHandler("reload", self.reload_bases))
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")

def main():
    try: 
        bot = MinecraftBot()
        app = Application.builder().token(Config.BOT_TOKEN).build()
        
        bot.create_handlers(app)
        app.add_error_handler(bot.error_handler)
        
        logger.info("Бот запущен")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    main()