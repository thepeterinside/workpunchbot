import asyncio
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime, time
import pytz

BOT_TOKEN = "8226118285:AAGS7V-LIerygiiCXx8l96BhHm77Sy67SMI"
GROUP_CHAT_ID = None  # Will detect automatically
EST = pytz.timezone('US/Eastern')

async def detect_chat_id():
    """Automatically fetch the group chat ID."""
    bot = Bot(BOT_TOKEN)
    try:
        await bot.delete_webhook()
        updates = await bot.get_updates()
        if updates:
            return updates[-1].message.chat_id
        else:
            print("Send a message in your group first.")
            return None
    except TelegramError as e:
        print(f"Error: {e}")
        return None

async def send_scheduled_messages():
    bot = Bot(BOT_TOKEN)
    while True:
        now = datetime.now(EST)
        current_time = now.time()
        
        # Morning message at 10:15 AM
        if current_time.hour == 10 and current_time.minute == 15:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text="Good Morning Everyone 🌞\nToday is your best day!"
            )
            await asyncio.sleep(60)  # Prevent duplicate sends

        # Report reminders at 1PM, 4PM, 7PM, 10PM
        elif current_time.hour in [13, 16, 19, 22] and current_time.minute == 0:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text="⏰ UPDATE YOUR REPORT"
            )
            await asyncio.sleep(60)

        # Evening sign-off at 10:15 PM
        elif current_time.hour == 22 and current_time.minute == 15:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text="See you tomorrow! 👋"
            )
            await asyncio.sleep(60)

        # Check every 30 seconds
        await asyncio.sleep(30)

async def main():
    global GROUP_CHAT_ID
    GROUP_CHAT_ID = await detect_chat_id()
    if GROUP_CHAT_ID:
        print(f"Detected Group ID: {GROUP_CHAT_ID}")
        await send_scheduled_messages()
    else:
        print("Could not detect Group ID.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")