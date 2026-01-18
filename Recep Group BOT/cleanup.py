import asyncio
from telegram import Bot

BOT_TOKEN = "8226118285:AAGS7V-LIerygiiCXx8l96BhHm77Sy67SMI"

async def cleanup():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deleted successfully")

asyncio.run(cleanup())