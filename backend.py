import os
import asyncpg
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def init_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    pool = app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, username, full_name) 
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name
        """, message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🚀 Marketplace ni ochish", web_app=types.WebAppInfo(url=APP_URL))]
        ]
    )
    
    await message.answer("Assalomu alaykum! Reklama Marketplace botiga xush kelibsiz!", reply_markup=keyboard)

@app.get("/api/ads")
async def get_ads():
    pool = app.state.db_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM ads ORDER BY created_at DESC")
        return {"success": True, "data": [dict(row) for row in rows]}

async def init_database(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                price DECIMAL,
                owner_telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                advertiser_telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                business_telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                amount DECIMAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        logger.info("Database jadvallari tayyor")

async def main():
    pool = await init_db_pool()
    app.state.db_pool = pool
    await init_database(pool)
    asyncio.create_task(dp.start_polling(bot))
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())