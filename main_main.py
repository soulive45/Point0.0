import logging
from flask import Flask, request
import hashlib
import hmac
import json
import base64
import requests
import openai
import aiosqlite
import asyncio
import discord
import matplotlib.pyplot as plt
import pandas as pd
from discord.ext import commands, tasks
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from aiogram.types import FSInputFile
from datetime import time
import hashlib
import aiohttp
from datetime import datetime
from openai import OpenAI
from collections import defaultdict
from datetime import timezone
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext  # Импорт контекста состояний
from aiogram.fsm.state import State, StatesGroup  # Импорт машины состояний
from aiogram.filters import StateFilter  # Фильтр по состояниям
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from discord.ext import commands


# 🔹 Загружаем токены из .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GUILD_ID = 1346969339743703050  # ID сервера в Discord
DB_PATH = "bot_activity.db"  # Единая база данных
DISCORD_LINK = os.getenv("DISCORD_LINK")
TELEGRAM_LINK = os.getenv("TELEGRAM_LINK")


# 🔹 Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.info("🟢 Логирование работает!")
SYSTEM_PROMPT = "You are a helpful assistant."  # Структура промптов сохранена


# 🔹 Инициализация ботов
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # ⚠️ Без этого бот не будет получать сообщения!
intents.guilds = True
intents.members = True
discord_bot = commands.Bot(command_prefix="!", intents=intents)
dp = Dispatcher()
bot = Bot(token=TELEGRAM_TOKEN)
router = Router()
dp.include_router(router)








# 🔹 Определяем ID каналов в Discord (пример)
target_channels = {
    "точка-входа": 1346977292668239953,
    "точка-намерения": 1346977301874868234,
    "точка-контакта": 1346977310376464394,
    "точка-выхода": 1347010428571484283,
    "точка-действия": 1347010437773922515,
    "точка-столкновения": 1347010462885351535,
    "точка-слабости": 1347010472209154218,
}

######################################################################
# 🔹 Постоянная клавиатура, которая появляется при вводе текста
persistent_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start")],  # Кнопка старт
    ],
    resize_keyboard=True,  # Подстраивает размер под экран
    one_time_keyboard=False,  # Клавиатура не скрывается после нажатия
    input_field_placeholder="Введите сообщение или нажмите /start"  # Текст в поле ввода
)
# 📌 Обработчик команды /start
@router.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📊 Личная статистика", callback_data="cmd_my_stats"
                ),
                types.InlineKeyboardButton(
                    text="📉 Графики", callback_data="cmd_daily_graph"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="📋 Недельная статистика", callback_data="cmd_weekly"
                ),
                types.InlineKeyboardButton(
                    text="📜 Месячная статистика", callback_data="cmd_monthly"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="🟦 Discord", callback_data="cmd_discord"
                ),
                types.InlineKeyboardButton(
                    text="🏆 Топ пользователи", callback_data="cmd_top_users"
                ),
                types.InlineKeyboardButton(
                    text="🔗Привязать DS по нику", callback_data="cmd_link_discord"
                ),
            ],
        ]
    )

    await bot.send_message(
        chat_id=message.chat.id,
        text="👋 Привет, выбери что тебя интересует",
        reply_markup=keyboard
    )

    # **Отправляем основную клавиатуру БЕЗ привязки**
    await bot.send_message(
        chat_id=message.chat.id,
        text="⬇️",
        reply_markup=persistent_keyboard
    )

@router.callback_query(F.data == "cmd_link_discord")
async def ask_for_discord_nickname(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("📝 Введите ваш ник в Discord:")
    await state.set_state("waiting_for_discord_nickname")  # Устанавливаем состояние ожидания ввода
    await callback_query.answer()

@router.message(StateFilter("waiting_for_discord_nickname"))
async def link_discord_username(message: types.Message, state: FSMContext):
    discord_username = message.text.strip()  # Получаем введённый никнейм
    telegram_id = message.from_user.id  # Получаем Telegram ID пользователя

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO user_links (discord_username, telegram_id) 
               VALUES (?, ?)
               ON CONFLICT(discord_username) 
               DO UPDATE SET telegram_id = ?""",  # Обновляем telegram_id в случае конфликта
            (discord_username, telegram_id, telegram_id)
        )
        await db.commit()

    await message.answer(f"✅ Ваш Telegram привязан к Discord нику `{discord_username}`.")
    await state.clear()  # Сбрасываем состояние









# 📌 Обработчик нажатий на кнопки → выполнение команд
@router.callback_query(F.data.startswith("cmd_"))
async def process_callback(callback_query: types.CallbackQuery):
    commands_map = {
        "cmd_my_stats": "/my_stats",
        "cmd_daily_graph": "/daily_graph",
        "cmd_weekly": "/weekly",
        "cmd_monthly": "/monthly",
        "cmd_discord": "/discord",
        "cmd_top_users": "/top_users",
        "cmd_link_discord": "/link_dicsord",
    }

    command = commands_map.get(callback_query.data)
    if command:
        # Создаём "фейковое" сообщение от пользователя
        fake_message = types.Message(
            message_id=callback_query.message.message_id,
            from_user=callback_query.from_user,
            chat=callback_query.message.chat,
            date=datetime.now(),
            text=command,
        )

        # Оборачиваем в объект types.Update и добавляем update_id
        update = types.Update(update_id=callback_query.id, message=fake_message)

        # Принудительно обрабатываем сообщение как команду
        await dp.feed_update(bot, update=update)

    await callback_query.answer()



#############################################################################
#############################################################################
#############################################################################
# ✅ **Стартовая команда в Telegram-ADMIN**
@dp.message(Command("start_admin"))
async def start_cmd(message: Message):
    await message.answer(
        "📌 **Доступные команды:**\n"
        "🔹 /admin_weekly [Discord ID] - просмотр за неделю статистики конкретного человека\n"
        "🔹 /admin_monthly [Discord ID] - просмотр за месяц статистики конкретного человека\n"
        "🔹 /moderation_list – — вывод списка забаненных и замьюченных пользователей.\n"
    )


# ✅ **Команды в Discord-ADMIN**
import discord

class AdminPanel(discord.ui.View):
    """Панель администратора с кнопками команд"""

    def __init__(self):
        super().__init__(timeout=None)  # ✅ Делаем View постоянным

    @discord.ui.button(label="🚨 Выдать предупреждение", style=discord.ButtonStyle.danger, custom_id="warn")
    async def warn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⚠️ Используйте команду: `!warn @User [причина]`", ephemeral=True)

    @discord.ui.button(label="🔇 Замьютить пользователя", style=discord.ButtonStyle.primary, custom_id="mute")
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔇 Используйте команду: `!mute @User [время/минуты] [причина]`", ephemeral=True)

    @discord.ui.button(label="⛔ Забанить пользователя", style=discord.ButtonStyle.danger, custom_id="ban")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⛔ Используйте команду: `!ban @User [причина]`", ephemeral=True)

    @discord.ui.button(label="✅ Разбанить пользователя", style=discord.ButtonStyle.success, custom_id="unban")
    async def unban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Используйте команду: `!unban @User`", ephemeral=True)

    @discord.ui.button(label="👢 Кикнуть пользователя", style=discord.ButtonStyle.danger, custom_id="kick")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👢 Используйте команду: `!kick @User [причина]`", ephemeral=True)

    @discord.ui.button(label="📜 Список нарушителей", style=discord.ButtonStyle.secondary, custom_id="moderation_list")
    async def moderation_list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📜 Используйте команду: `!moderation_list`", ephemeral=True)




@discord_bot.command()
@commands.has_permissions(administrator=True)
async def admin_panel(ctx):
    """Отправляет панель администратора с кнопками команд"""
    
    embed = discord.Embed(
        title="⚙️ Панель администратора",
        description="Выбери нужную команду:",
        color=discord.Color.red()
    )

    view = AdminPanel()  # Создаём экземпляр панели с кнопками
    await ctx.send(embed=embed, view=view)


# ✅ **Команды в Discord**
@discord_bot.command("start")
async def start(ctx):
    """Вывод списка доступных команд в Discord"""
    commands_list = (
        "**📌 Доступные команды:**\n"
        "🔹 !telegram - даёт ссылку для перехода на наш тг-канал.\n"
    )
    await ctx.send(commands_list)






# ✅ **Проверка привязки**
# 🔹 Функция получения статистики пользователя
async def get_user_stats(user_id, days):
    """Возвращает количество сообщений пользователя за указанный период (дней)"""
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT point, COUNT(*) FROM activity WHERE user_id = ? AND timestamp >= ? GROUP BY point",
            (user_id, date_from),
        )
        return await cursor.fetchall()


# 🔹 Получение Discord ID по Telegram ID
async def get_discord_id(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT discord_id FROM user_links WHERE telegram_id = ?", (telegram_id,)
        )
        result = await cursor.fetchone()
    return result[0] if result else None


# Сохранение активности
async def save_activity(user_id, username, channel_id, point, message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO activity (user_id, username, channel_id, point, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                username,
                channel_id,
                point,
                message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        await db.commit()
    logging.info(f"✅ Сообщение сохранено в БД: {username} | {point} | {message}")






# 🔹 Получение данных из БД
async def get_activity():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT point, COUNT(*) FROM activity GROUP BY point")
        data = await cursor.fetchall()
    logging.info(f"📊 Данные активности: {data}")
    return data


async def get_top_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username, COUNT(*) FROM activity GROUP BY username ORDER BY COUNT(*) DESC LIMIT 5"
        )
        return await cursor.fetchall()


async def get_activity_by_day():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT strftime('%w', timestamp) AS day, COUNT(*) FROM activity GROUP BY day"
        )
        return await cursor.fetchall()


################################################################################################################
################################################################################################################
################################################################################################################
################################################################################################################
################################################################################################################
# ✅ **Команды в Telegram**
# 🔹 Генерация графиков
async def generate_graph_activity():
    data = await get_activity()
    if not data:
        return None

    df = pd.DataFrame(data, columns=["point", "count"])
    plt.figure(figsize=(8, 6))
    plt.bar(df["point"], df["count"], color="skyblue")
    plt.xlabel("Точка активности")
    plt.ylabel("Количество сообщений")
    plt.title("Активность по точкам")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("activity_graph.png")
    plt.close()
    return "activity_graph.png"


async def generate_graph_daily():
    data = await get_activity_by_day()
    if not data:
        return None

    days = [
        "Воскресенье",
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
    ]
    df = pd.DataFrame(data, columns=["day", "count"])
    df["day"] = df["day"].astype(int)
    df = df.sort_values(by="day")

    plt.figure(figsize=(8, 6))
    plt.plot(df["day"], df["count"], marker="o", linestyle="-", color="green")
    plt.xticks(ticks=df["day"], labels=[days[d] for d in df["day"]])
    plt.xlabel("День недели")
    plt.ylabel("Количество сообщений")
    plt.title("Активность по дням недели")
    plt.tight_layout()
    plt.savefig("daily_graph.png")
    plt.close()
    return "daily_graph.png"


@router.message(Command("activity_graph"))
async def tg_activity_graph_cmd(message: Message):
    file = await generate_graph_activity()
    if file:
        photo = FSInputFile(file)  # Оборачиваем путь в FSInputFile
        await message.answer_photo(photo, caption="📊 График активности по точкам")
    else:
        await message.answer("❌ Нет данных для графика!")


@router.message(Command("daily_graph"))
async def tg_daily_graph_cmd(message: Message):
    file = await generate_graph_daily()
    if file:
        photo = FSInputFile(file)  # Используем FSInputFile
        await message.answer_photo(photo, caption="📅 График активности по дням недели")
    else:
        await message.answer("❌ Нет данных для графика!")


@router.message(Command("top_users"))
async def tg_top_users_cmd(message: Message):
    data = await get_top_users()

    if not data:
        await message.answer("❌ Нет данных о пользователях!")
        return

    # Формируем текстовое сообщение
    stats_message = "🏆 Топ-5 активных пользователей:\n"
    for index, (username, count) in enumerate(data, start=1):
        stats_message += f"{index}. **{username}** — {count} сообщений\n"

    await message.answer(stats_message)


# ✅ Получение статистики пользователя
async def get_user_stats_by_nickname(nickname):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT point, COUNT(*) 
            FROM activity 
            WHERE username = ?
            GROUP BY point
            """,
            (nickname,),
        )
        return await cursor.fetchall()


# ✅ Получение топ-5 пользователей
async def get_top_5_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT username, COUNT(*) 
            FROM activity 
            GROUP BY username 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
            """
        )
        return await cursor.fetchall()


# ✅ Генерация графика активности пользователя
async def generate_user_activity_graph(nickname):
    data = await get_user_stats_by_nickname(nickname)
    if not data:
        return None

    df = pd.DataFrame(data, columns=["point", "count"])
    plt.figure(figsize=(8, 6))
    plt.bar(df["point"], df["count"], color="blue")
    plt.xlabel("Точка активности")
    plt.ylabel("Количество сообщений")
    plt.title(f"Активность {nickname} по точкам")
    plt.xticks(rotation=45)
    plt.tight_layout()
    filename = f"{nickname}_activity.png"
    plt.savefig(filename)
    plt.close()
    return filename

class Form(StatesGroup):
    waiting_for_nickname = State()

@router.message(Command("my_stats"))
async def request_nickname(callback_query: types.CallbackQuery, state: FSMContext):
    """Запрашивает ник у пользователя перед обработкой команды"""
    await callback_query.answer("📝 Введите ваш Discord ник для получения статистики:")
    await state.set_state(Form.waiting_for_nickname)  # Устанавливаем состояние
    await callback_query.answer()


@router.message(StateFilter(Form.waiting_for_nickname))
async def process_nickname(message: types.Message, state: FSMContext):
    """Обрабатывает введённый пользователем ник и вызывает команду /my_stats"""
    discord_nickname = message.text.strip()
    await state.clear()  # Очищаем состояние
    await my_stats_cmd(message, discord_nickname)




async def my_stats_cmd(message: types.Message, discord_nickname: str):
    """Получает и отправляет статистику пользователя по его нику"""
    user_data = await get_user_stats_by_nickname(discord_nickname)
    top_users = await get_top_5_users()

    if not user_data:
        await message.answer(f"❌ Данных о пользователе {discord_nickname} нет в базе!")
        return

    total_messages = sum(count for _, count in user_data)
    user_rank = next(
        (index + 1 for index, (user, _) in enumerate(top_users) if user == discord_nickname),
        None,
    )
    user_rank_text = (
        f"📊 {user_rank}-е место на сервере" if user_rank else "📊 Вне топ-5 пользователей"
    )

    top_3_points = sorted(user_data, key=lambda x: x[1], reverse=True)[:3]
    points_text = "\n".join(
        [
            f"{i+1}️⃣ {point} – {count} сообщений"
            for i, (point, count) in enumerate(top_3_points)
        ]
    )

    top_users_text = "\n".join(
        [
            f"{i+1}. 🔥 {user} — {count} сообщений"
            for i, (user, count) in enumerate(top_users)
        ]
    )

    stats_message = (
        f"📊 Личная статистика для {discord_nickname}\n"
        f"- 📌 Сообщений: {total_messages} ({user_rank_text})\n"
        f"- 🔥 Топ-3 точки активности:\n{points_text}\n\n"
        f"🏆 Сравнение с топ-5 активными пользователями:\n{top_users_text}"
    )

    await message.answer(stats_message)



# ✅ **Команда /weekly - недельная статистика**
@router.message(Command("weekly"))
async def weekly_cmd(message: Message):
    discord_id = await get_discord_id(message.from_user.id)
    if not discord_id:
        await message.answer(
            "⚠️ Ты не привязал свой Discord ID! Используй команду `/link_discord [твой Discord ID]`"
        )
        return

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT point, COUNT(*) FROM activity WHERE user_id = ? AND timestamp >= ? GROUP BY point",
            (discord_id, week_ago),
        )
        data = await cursor.fetchall()

    if data:
        stats_message = "📊 **Недельная активность:**\n"
        for point, count in data:
            stats_message += f"🔹 {point}: {count} сообщений\n"
        await message.answer(stats_message)
    else:
        await message.answer("ℹ️ У тебя нет активности за последнюю неделю.")


# ✅ **Команда /monthly - месячная статистика**
@router.message(Command("monthly"))
async def monthly_cmd(message: Message):
    discord_id = await get_discord_id(message.from_user.id)
    if not discord_id:
        await message.answer(
            "⚠️ Ты не привязал свой Discord ID! Используй команду `/link_discord [твой Discord ID]`"
        )
        return

    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT point, COUNT(*) FROM activity WHERE user_id = ? AND timestamp >= ? GROUP BY point",
            (discord_id, month_ago),
        )
        data = await cursor.fetchall()

    if data:
        stats_message = "📊 **Месячная активность:**\n"
        for point, count in data:
            stats_message += f"🔹 {point}: {count} сообщений\n"
        await message.answer(stats_message)
    else:
        await message.answer("ℹ️ У тебя нет активности за последний месяц.")


@router.message(Command("discord"))
async def discord_link_cmd(message: types.Message):
    """Отправляет ссылку на Discord сервер из .env"""
    if DISCORD_LINK:
        await message.answer(f"🔗 Ссылка на наш Discord сервер: {DISCORD_LINK}")
    else:
        await message.answer("❌ Ссылка на Discord сервер не настроена. Обратитесь к администратору.")


################################################################################################################
################################################################################################################
################################################################################################################
################################################################################################################
################################################################################################################

#   КОМАНДЫ DISCORD
@discord_bot.command()
async def telegram(ctx):
    """Отправляет ссылку на Discord сервер из .env"""
    if TELEGRAM_LINK:
        await ctx.send(f"🔗 Ссылка на наш Telegram сервер: {TELEGRAM_LINK}")
    else:
        await ctx.send("❌ Ссылка на Discord сервер не настроена. Обратитесь к администратору.")


@discord_bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="Не указана"):
    """Выдаёт предупреждение пользователю, а при 3-х предупреждениях отправляет в точка-слабости и блокирует в других точках."""
    user_id = member.id

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # ✅ Добавляем предупреждение в базу
            await db.execute(
                "INSERT INTO warnings (user_id, reason, timestamp) VALUES (?, ?, ?)",
                (user_id, reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            await db.commit()

            # ✅ Проверяем количество предупреждений
            cursor = await db.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
            warn_count = (await cursor.fetchone())[0]

        # ✅ Отправляем сообщение в канал
        await ctx.send(f"⚠️ {member.mention} получил предупреждение! Причина: {reason} (⚠ {warn_count}/3)")

        # ✅ Отправляем уведомление в ЛС
        try:
            await member.send(f"⚠️ Ты получил предупреждение на сервере! Причина: {reason} (⚠ {warn_count}/3)")
        except discord.Forbidden:
            await ctx.send(f"⚠️ {member.mention}, не могу отправить тебе ЛС!")

        # 🚨 Если 3 предупреждения — отправляем в точка-слабости, блокируем и сбрасываем счётчик
        if warn_count >= 3:
            await move_to_weakness(ctx, member, reason="3 предупреждения")

            async with aiosqlite.connect(DB_PATH) as db:
                # ✅ Удаляем все предупреждения для сброса счётчика
                await db.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
                await db.commit()

                # ✅ Блокируем пользователя (не даём писать в других точках)
                await db.execute(
                    "INSERT INTO blocked_users (user_id, blocked) VALUES (?, 1) "
                    "ON CONFLICT(user_id) DO UPDATE SET blocked = 1",
                    (user_id,),
                )
                await db.commit()

            # ✅ Проверяем, действительно ли предупреждения сброшены
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
                new_warn_count = (await cursor.fetchone())[0]

            if new_warn_count == 0:
                await ctx.send(f"✅ Счётчик предупреждений {member.mention} успешно сброшен!")
            else:
                await ctx.send(f"⚠️ Ошибка: предупреждения не сбросились! Новое количество: {new_warn_count}")

            # ✅ Сообщение о блокировке
            await ctx.send(f"🚫 {member.mention} заблокирован во всех точках, пока не напишет причину в 'точка-слабости'!")
            try:
                await member.send("🚫 Ты заблокирован во всех точках, пока не напишешь причину в 'точка-слабости'.")
            except discord.Forbidden:
                pass

    except Exception as e:
        logging.error(f"Ошибка в !warn: {e}")
        await ctx.send(f"❌ Ошибка при выдаче предупреждения: {e}")




    




@discord_bot.command()
@commands.has_permissions(manage_messages=True)
async def mute(ctx, member: discord.Member, time: int, *, reason="Не указана"):
    """Мут пользователя (минуты)"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)

    await member.add_roles(mute_role)
    unmute_time = (datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO muted_users (user_id, muted_until) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET muted_until = ?",
            (member.id, unmute_time, unmute_time),
        )
        await db.commit()

    await ctx.send(f"🔇 {member.mention} замьючен на {time} минут! Причина: {reason}")

    await asyncio.sleep(time * 60)
    await member.remove_roles(mute_role)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM muted_users WHERE user_id = ?", (member.id,))
        await db.commit()

    await ctx.send(f"✅ {member.mention} размьючен!")


@discord_bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Не указана"):
    """Бан пользователя"""
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member.mention} забанен! Причина: {reason}")

@discord_bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, username: str):
    """Разбан пользователя по нику"""
    banned_users = await ctx.guild.bans()
    
    # Ищем пользователя по нику
    for ban_entry in banned_users:
        if ban_entry.user.name.lower() == username.lower():  # Сравниваем без учёта регистра
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f"✅ {ban_entry.user.mention} разбанен!")
            return
    
    await ctx.send(f"❌ Пользователь `{username}` не найден в списке забаненных!")


@discord_bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Не указана"):
    """Кикает пользователя с сервера"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} кикнут! Причина: {reason}")


@discord_bot.command()
@commands.has_permissions(manage_messages=True)
async def move_to_weakness(ctx, member: discord.Member, *, reason="Не указана"):
    """Перемещает пользователя в точка-слабости"""
    weakness_channel = discord_bot.get_channel(target_channels["точка-слабости"])
    if weakness_channel:
        await weakness_channel.send(f"🚨 {member.mention} перемещён в точка-слабости. Причина: {reason}")
        await ctx.send(f"✅ {member.mention} перемещён в точка-слабости!")
    else:
        await ctx.send("❌ Канал 'точка-слабости' не найден!")

@discord_bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Удаляет последние N сообщений"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Удалено {amount} сообщений!", delete_after=5)

@discord_bot.command()
@commands.has_permissions(manage_messages=True)
async def moderation_list(ctx):
    """Показывает список пользователей с мутами, варнами, банами"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем список предупреждений
        cursor = await db.execute("SELECT user_id, reason FROM warnings")
        warns = await cursor.fetchall()

        # Получаем список замьюченных
        cursor = await db.execute("SELECT user_id FROM muted_users")
        muted = await cursor.fetchall()

        # Получаем список забаненных
        cursor = await db.execute("SELECT user_id FROM banned_users")
        banned = await cursor.fetchall()

    # Функция получения ника по user_id
    def get_username(user_id):
        user = ctx.guild.get_member(user_id)
        return user.name if user else "Неизвестный пользователь"

    # Формируем списки
    warn_list = "\n".join([f"⚠ {get_username(user_id)} - {reason}" for user_id, reason in warns]) or "Нет предупреждений"
    mute_list = "\n".join([f"🔇 {get_username(user_id)}" for user_id, in muted]) or "Нет замьюченных"
    ban_list = "\n".join([f"⛔ {get_username(user_id)}" for user_id, in banned]) or "Нет забаненных"

    # Создаём Embed
    embed = discord.Embed(title="📌 Список наказанных", color=discord.Color.red())
    embed.add_field(name="⚠ Предупреждения", value=warn_list, inline=False)
    embed.add_field(name="🔇 Замьюченные", value=mute_list, inline=False)
    embed.add_field(name="⛔ Забаненные", value=ban_list, inline=False)

    await ctx.send(embed=embed)








##############################################################################################################################
##############################################################################################################################
##############################################################################################################################
##############################################################################################################################
##############################################################################################################################
# Персонализированные промты для OpenAI
PROMPTS = {
    "точка-входа": "Ты попал в точку входа. Какой у тебя план на этот этап?",
    "точка-действия": "Ты находишься в точке действия. Как ты планируешь двигаться дальше?",
    "точка-столкновения": "Ты столкнулся с вызовом. Как ты с ним справляешься?",
    "точка-слабости": "Ты чувствуешь слабость. Что поможет тебе восстановиться?",
    "точка-контакта": "Ты в точке контакта. Поделись своими мыслями и чувствами развёрнуто!",
    "точка-намерения": "Зачем ты строишь весь этот путь?",
    "точка-выхода": "Время подвести итоги. Как прошёл этот этап?",
}
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Отслеживание активности пользователей (лимиты сообщений в каждой точке)
USER_MESSAGES = defaultdict(
    lambda: defaultdict(lambda: {"count": 0, "last_reset": datetime.now(timezone.utc)})
)

# Отслеживание отправленных приветственных сообщений
LAST_GREETING = defaultdict(lambda: {"date": None, "message": ""})


def generate_daily_greeting(user_point):
    greetings = [
        f"Добро пожаловать в {user_point}! Надеюсь, у тебя сегодня будет продуктивный день!",
        f"Сегодня отличный день для работы в {user_point}! У тебя всё получится!",
        f"Привет! Как настроение в {user_point}? Делись своими планами!",
        f"День начинается с новых идей в {user_point}! Вперёд к успеху!",
    ]
    return random.choice(greetings)


async def generate_openai_response(prompt, max_tokens=250):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


@discord_bot.command()
async def ask(ctx, *, user_message: str):
    """Команда для запроса к ИИ в точке-контакте"""
    user_point = next(
        (point for point, ch_id in target_channels.items() if ch_id == ctx.channel.id),
        None,
    )

    if user_point == "точка-контакта":
        ai_prompt = f"{PROMPTS[user_point]} Пользователь написал: {user_message}. Дай рекомендацию и пожелание."
        ai_response = await generate_openai_response(ai_prompt)
        await ctx.send(f"✨ Ответ ИИ: {ai_response}")
    else:
        await ctx.send(f"🚫 Использование ИИ разрешено только в точке-контакта!")


@discord_bot.event
async def on_message(message):
    if message.author.bot:
        return  # Игнорируем ботов

    # ✅ Проверяем, если это команда (!)
    if message.content.startswith("!"):
        await discord_bot.process_commands(message)
        return  # Выходим, чтобы не выполнять код дважды

    logging.info(f"📩 Новое сообщение в Discord: {message.author.name} в канале ID {message.channel.id}: {message.content}")

    user_id = message.author.id
    username = message.author.name
    channel_id = message.channel.id
    now = datetime.now(timezone.utc)

    # Определяем точку пользователя по ID канала
    user_point = next((point for point, ch_id in target_channels.items() if ch_id == channel_id), None)

    

    if user_point:
        logging.info(f"✅ Сообщение относится к точке: {user_point}!")
        await save_activity(user_id, username, channel_id, user_point, message.content)
    else:
        logging.warning(f"⚠️ Канал {channel_id} не найден в target_channels!")

    # ✅ Не вызываем process_commands() снова, так как он уже обработан выше

    # Проверяем, является ли пользователь администратором
    if message.author.guild_permissions.administrator:
        await discord_bot.process_commands(message)
        return  # Админы не имеют ограничений

    # Определяем точку
    user_point = next(
        (point for point, ch_id in target_channels.items() if ch_id == channel_id), None
    )
    

    if user_point:
        # Проверка и отправка приветственного сообщения (раз в день на точку)
        last_greeting_date = LAST_GREETING[user_point]["date"]
        if last_greeting_date is None or (now.date() > last_greeting_date):
            greeting_message = generate_daily_greeting(user_point)
            LAST_GREETING[user_point] = {
                "date": now.date(),
                "message": greeting_message,
            }
            await message.channel.send(f"🌟 **{greeting_message}**")

        # Проверка и сброс счётчика раз в сутки для каждой точки
        if (now - USER_MESSAGES[user_id][user_point]["last_reset"]).days >= 1:
            print(f"[DEBUG] Сброс лимита сообщений для {username} в {user_point}")
            USER_MESSAGES[user_id][user_point] = {"count": 0, "last_reset": now}

        USER_MESSAGES[user_id][user_point]["count"] += 1
        print(
            f"[DEBUG] {username} отправил {USER_MESSAGES[user_id][user_point]['count']} сообщений в {user_point}"
        )

        # Проверяем лимиты сообщений (кроме точки контакта)
        if (
            user_point != "точка-контакта"
            and USER_MESSAGES[user_id][user_point]["count"] > 2
        ):
            try:
                await message.delete()
                print(
                    f"[DEBUG] Сообщение пользователя {username} удалено в {user_point}"
                )
            except discord.Forbidden:
                print(f"[WARNING] Нет прав на удаление сообщения в {user_point}")
                return

            try:
                await message.author.send(
                    f"🚫 Ты превысил лимит сообщений (2 в день) в {user_point}! Следующие сообщения будут удаляться."
                )
                print(f"[DEBUG] ЛС отправлено пользователю {username}")
            except discord.Forbidden:
                print(
                    f"[WARNING] Не удалось отправить ЛС пользователю {username}, отправляю предупреждение в канал"
                )
                await message.channel.send(
                    f"{message.author.mention} 🚫 Ты превысил лимит сообщений (2 в день) в {user_point}!"
                )
            return

        # Генерация ответа OpenAI во всех точках, кроме точки-контакта
        if user_point != "точка-контакта":
            ai_prompt = f"{PROMPTS[user_point]} Пользователь написал: {message.content}. Дай рекомендацию и пожелание."
            ai_response = await generate_openai_response(ai_prompt)
            await message.channel.send(f"✨ {ai_response}")

        # ✅ Проверяем, заблокирован ли пользователь
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT blocked FROM blocked_users WHERE user_id = ?", (user_id,))
        blocked = await cursor.fetchone()

    # 🚫 Если пользователь заблокирован и пишет НЕ в "точка-слабости" → удаляем сообщение
    if blocked and blocked[0] == 1 and user_point != "точка-слабости":
        await message.delete()
        await message.author.send("🚫 Ты заблокирован во всех точках, пока не напишешь причину в 'точка-слабости'.")
        return

    # ✅ Если пользователь написал в "точка-слабости", разблокируем его
    if blocked and blocked[0] == 1 and user_point == "точка-слабости":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
            await db.commit()
        await message.author.send("✅ Ты разблокирован и можешь снова писать во всех точках!")

    # 📩 Логируем сообщение
    logging.info(f"📩 Новое сообщение в Discord: {username} в канале ID {channel_id}: {message.content}")

    await discord_bot.process_commands(message)


# 🔹 Функция отправки ежедневных напоминаний
@tasks.loop(hours=16)
async def send_daily_reminders():
    now = datetime.now(timezone.utc)
    logger.info(f"🔄 Проверка отправки напоминаний: {now}")

    for guild in discord_bot.guilds:
        for member in guild.members:
            if not member.bot:
                # Проверяем, был ли человек активен в любой точке (кроме входа)
                was_active = any(
                    USER_MESSAGES[member.id][point]["count"] > 0
                    for point in target_channels
                    if point != "точка-входа"
                )

                if was_active:
                    try:
                        await member.send("📌 Не забудь написать отчёт в точке-выхода!")
                        logger.info(f"📩 Напоминание отправлено: {member.name}")
                    except discord.Forbidden:
                        logger.warning(
                            f"⚠️ Не могу отправить ЛС {member.name}! Возможно, у него отключены сообщения от сервера."
                        )


# 🔹 Ручной запуск напоминаний (для теста)
@discord_bot.command()
async def test_reminder(ctx):
    """Ручной тест отправки напоминаний"""
    await send_daily_reminders()
    await ctx.send("📌 Тестовое напоминание отправлено!")




##############################################################################################################################
async def init_db():
    # Подключение к базе данных SQLite
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("DROP TABLE IF EXISTS user_links;")
        await db.commit()

        
        # Создание таблицы activity, если она не существует
        await db.execute(
            """CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                channel_id INTEGER,
                point TEXT,
                message TEXT,
                timestamp TEXT
            )"""
        )

        # Создание таблицы user_links
        await db.execute(
            """CREATE TABLE IF NOT EXISTS user_links (
            discord_username TEXT PRIMARY KEY,
            telegram_id INTEGER UNIQUE
        )"""
        )
        # Создание таблицы user_checkpoints
        await db.execute(
            """CREATE TABLE IF NOT EXISTS user_checkpoints (
                user_id INTEGER,
                point TEXT,
                UNIQUE(user_id, point)
            )"""
        )

        # Создание таблицы user_status
        await db.execute(
            """CREATE TABLE IF NOT EXISTS user_status (
                user_id INTEGER PRIMARY KEY,
                last_point TEXT,
                last_activity TIMESTAMP
            )"""
        )

        # Создание таблицы warnings
        await db.execute(
            """CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                timestamp TEXT
            )"""
        )

        # Создание таблицы blocked_users
        await db.execute(
            """CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY,
                blocked INTEGER DEFAULT 0
            )"""
        )

        # Создание таблицы muted_users
        await db.execute(
            """CREATE TABLE IF NOT EXISTS muted_users (
                user_id INTEGER PRIMARY KEY,
                muted_until TEXT
            )"""
        )

        # Создание таблицы banned_users
        await db.execute(
            """CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY
            )"""
        )

        # Сохраняем изменения в базе данных
        await db.commit()
        print("✅ База данных инициализирована успешно!")


# 🔥 **Запуск ботов**
async def main():
    await init_db()

    discord_bot.add_view(AdminPanel())  # ✅ Теперь ошибки не будет!

    
    asyncio.create_task(discord_bot.start(DISCORD_TOKEN))
    print("✅ Telegram-бот запущен!")
    await asyncio.sleep(1)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())  # Запуск обоих ботов
