import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from config import Config
import mcrcon

# === Логирование ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S' 
)
logger = logging.getLogger(__name__)


class MinecraftBot:
    def __init__(self):
        self.allowed_users = Config.ALLOWED_USERS_IDS
        self.bases_file = "bases.json"
        self.users_file = "users.json"
        self.DIFFICULTY_DISPLAY = {
            'peaceful': 'мирный',
            'easy': 'лёгкий',
            'normal': 'нормальный',
        }
        self.WEATHER_DISPLAY = {
            'clear': 'ясно',
            'rain': 'дождь',
            'thunder': 'гроза',
        }
        self.TIME_DISPLAY = {
            'day': 'день',
            'noon': 'полдень',
            'sunset': 'вечер',    
            'night': 'ночь',
            'midnight': 'полночь',
        } 
        self.modes = ['creative','survival']
        self.times = list(self.TIME_DISPLAY.keys())
        self.weather = list(self.WEATHER_DISPLAY.keys())
        self.difficulties = list(self.DIFFICULTY_DISPLAY.keys())
        self.bases = self._load_bases()
        self.users = self._load_users()

        logger.info(f"Бот инициализирован для {len(self.allowed_users)} пользователей")
        logger.info(f"Загружено {len(self.bases)} баз и {len(self.users)} пользователей")

    def _load_bases(self) -> dict:
        try:
            with open(self.bases_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки баз: {e}")
            return {}

    def _load_users(self) -> dict:
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
            return {}

    def _save_bases(self):
        try:
            with open(self.bases_file, 'w', encoding='utf-8') as f:
                json.dump(self.bases, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения баз: {e}")

    def is_user_allowed(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    def get_minecraft_nickname(self, user_id: int) -> str:
        user_id_str = str(user_id)
        return self.users.get(user_id_str, {}).get("minecraft_nickname", "Player")

    def _get_son_id(self) -> int | None:
        return self.allowed_users[1] if len(self.allowed_users) > 1 else None

    # === RCON ===
    async def send_rcon_command(self, command: str) -> str:
        try:
            with mcrcon.MCRcon(Config.RCON_HOST, Config.RCON_PASSWORD, port=Config.RCON_PORT) as mcr:
                response = mcr.command(command)
                return response.strip() if response else "✅ Команда выполнена"
        except Exception as e:
            return f"❌ Ошибка RCON: {e}"

    async def get_player_coordinates(self, player_nickname: str) -> str:
        try:
            with mcrcon.MCRcon(Config.RCON_HOST, Config.RCON_PASSWORD, port=Config.RCON_PORT) as mcr:
                resp = mcr.command(f"data get entity {player_nickname} Pos")
                return resp
        except Exception as e:
            return f"❌ Не удалось получить координаты: {e}"

    # === Клавиатуры ===
    def start_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Старт", callback_data="main_menu")
        ]])

    def main_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🗃 Базы", callback_data="bases")],
            [InlineKeyboardButton("⚡ Сложность", callback_data="difficulty")],
            [InlineKeyboardButton("🌤 Погода", callback_data="weather")],
            [InlineKeyboardButton("⏱ Время", callback_data="time")],
            [InlineKeyboardButton("🎮 Игровой режим", callback_data="mode")],
        ])

    def back_keyboard(self, back_to: str = "main_menu") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Назад", callback_data=back_to)
        ]])

    # === Обработчики команд ===
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("❌ Доступ запрещён!")
            return

        await update.message.reply_text(
            "👋 Добро пожаловать!\nНажмите «Старт», чтобы открыть меню:",
            reply_markup=self.start_keyboard()
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        if not self.is_user_allowed(user_id):
            await query.message.reply_text("❌ Доступ запрещён!")
            return

        data = query.data
        user_nick = self.get_minecraft_nickname(user_id)
        son_id = self._get_son_id()

        # --- Главное меню ---
        if data == "main_menu":
            await query.edit_message_text("📁 Выберите действие:", reply_markup=self.main_menu_keyboard())

        # --- Базы ---
        elif data == "bases":
            if not self.bases:
                txt = "❌ Нет доступных баз."
                kb = self.back_keyboard("main_menu")
            else:
                txt = "🗃 Доступные базы:\n"
                buttons = []
                for cmd, info in self.bases.items():
                    txt += f"- {info['name']}: {info['coords']}\n"
                    buttons.append([InlineKeyboardButton(info['name'], callback_data=f"tp_base:{cmd}")])
                if son_id == user_id:
                    buttons.append([InlineKeyboardButton("👨‍👦 К папе", callback_data="tp_papa")])
                buttons.append([InlineKeyboardButton("↩️ Назад", callback_data="main_menu")])
                kb = InlineKeyboardMarkup(buttons)
            await query.edit_message_text(txt, reply_markup=kb)

        elif data.startswith("tp_base:"):
            base_cmd = data.split(":", 1)[1]
            if base_cmd not in self.bases:
                await query.edit_message_text("❌ База не найдена", reply_markup=self.back_keyboard("bases"))
                return
            base = self.bases[base_cmd]
            resp = await self.send_rcon_command(f"tp {user_nick} {base['coords']}")
            await query.edit_message_text(
                f"➡️ {user_nick} телепортирован на {base['name']} ({base['coords']})",
                reply_markup=self.back_keyboard("bases")
            )

        elif data == "tp_papa":
            if son_id != user_id:
                await query.edit_message_text("❌ Только для сына!", reply_markup=self.back_keyboard("bases"))
                return
            papa_nick = self.get_minecraft_nickname(self.allowed_users[0])
            resp = await self.send_rcon_command(f"tp {user_nick} {papa_nick}")
            await query.edit_message_text(
                f"👨‍👦 {user_nick} телепортирован к {papa_nick}",
                reply_markup=self.back_keyboard("bases")
            )

        # --- Сложность ---
        elif data == "difficulty":
            buttons = [
                [InlineKeyboardButton(self.DIFFICULTY_DISPLAY[d], callback_data=f"set_diff:{d}") for d in self.difficulties],
                [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("⚡ Выберите сложность:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("set_diff:"):
            diff = data.split(":", 1)[1]
            if diff not in self.difficulties:
                await query.edit_message_text("❌ Неверная сложность", reply_markup=self.back_keyboard("difficulty"))
                return
            await self.send_rcon_command(f"difficulty {diff}")
            await query.edit_message_text(
                f"✅ Сложность установлена: *{self.DIFFICULTY_DISPLAY[diff]}*",
                parse_mode="Markdown",
                reply_markup=self.back_keyboard("main_menu")
            )

        # --- Погода ---
        elif data == "weather":
            buttons = [
                [InlineKeyboardButton(self.WEATHER_DISPLAY[w], callback_data=f"set_weather:{w}") for w in self.weather],
                [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("🌤 Выберите погоду:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("set_weather:"):
            w = data.split(":", 1)[1]
            if w not in self.weather:
                await query.edit_message_text("❌ Неверная погода", reply_markup=self.back_keyboard("weather"))
                return
            await self.send_rcon_command(f"weather {w}")
            await query.edit_message_text(
                f"✅ Погода установлена: *{self.WEATHER_DISPLAY[w]}*",
                parse_mode="Markdown",
                reply_markup=self.back_keyboard("main_menu")
            )

        # --- Время ---
        elif data == "time":
            buttons = [
                [InlineKeyboardButton(self.TIME_DISPLAY[t], callback_data=f"set_time:{t}") for t in self.times],
                [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("⏱ Выберите время суток:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("set_time:"):
            t = data.split(":", 1)[1]
            if t not in self.times:
                await query.edit_message_text("❌ Неверное время", reply_markup=self.back_keyboard("time"))
                return
            await self.send_rcon_command(f"time set {t}")
            await query.edit_message_text(
                f"✅ Время установлено: *{self.TIME_DISPLAY[t]}*",
                parse_mode="Markdown",
                reply_markup=self.back_keyboard("main_menu")
            )

        # --- Игровой режим ---
        elif data == "mode":
            buttons = []
            for m in self.modes:
                btn_text = "Креатив 🧱" if m == "creative" else "Выживание 🌲"
                buttons.append([InlineKeyboardButton(btn_text, callback_data=f"set_mode:{m}")])
            buttons.append([InlineKeyboardButton("↩️ Назад", callback_data="main_menu")])
            await query.edit_message_text("🎮 Выберите режим:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("set_mode:"):
            m = data.split(":", 1)[1]
            if m not in self.modes:
                await query.edit_message_text("❌ Неверный режим", reply_markup=self.back_keyboard("mode"))
                return
            resp = await self.send_rcon_command(f"gamemode {m} {user_nick}")
            mode_name = "креатив" if m == "creative" else "выживание"
            await query.edit_message_text(f"✅ Установлен режим: *{mode_name}* для {user_nick}", parse_mode="Markdown", reply_markup=self.back_keyboard("main_menu"))

    async def reload_bases(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_user_allowed(update.effective_user.id):
            await update.message.reply_text("❌ Доступ запрещён!")
            return
        self.bases = self._load_bases()
        await update.message.reply_text(f"✅ Базы перезагружены! Всего: {len(self.bases)}")

    def create_handlers(self, app: Application):
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("reload", self.reload_bases))
        app.add_handler(CallbackQueryHandler(self.button_handler))

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Обновление {update} вызвало ошибку: {context.error}")


def main():
    try:
        bot = MinecraftBot()
        app = Application.builder().token(Config.BOT_TOKEN).build()

        bot.create_handlers(app)
        app.add_error_handler(bot.error_handler)

        logger.info("✅ Бот запущен и ожидает команд...")
        app.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)


if __name__ == "__main__":
    main()