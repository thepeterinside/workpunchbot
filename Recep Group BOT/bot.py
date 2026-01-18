import asyncio
from telegram import Bot
from telegram.error import TelegramError

BOT_TOKEN = "8226118285:AAGS7V-LIerygiiCXx8l96BhHm77Sy67SMI"
GROUP_CHAT_ID = None  # Will detect automatically

async def detect_chat_id():
    """Automatically fetch the group chat ID."""
    bot = Bot(BOT_TOKEN)
    try:
        # Delete any existing webhook to avoid conflicts
        await bot.delete_webhook()
        
        # Get the latest update (send a message in group first)
        updates = await bot.get_updates()
        if updates:
            return updates[-1].message.chat_id
        else:
            print("No updates found. Send a message in your group first.")
            return None
    except TelegramError as e:
        print(f"Error: {e}")
        return None

async def send_reminder():
    """Send reminders every 3 hours."""
    bot = Bot(BOT_TOKEN)
    while True:
        try:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text="⏰ UPDATE YOUR REPORT"
            )
            print("Reminder sent successfully!")
        except TelegramError as e:
            print(f"Failed to send reminder: {e}")
        
        # Wait 3 hours (10,800 seconds)
        await asyncio.sleep(10800)

async def main():
    global GROUP_CHAT_ID
    GROUP_CHAT_ID = await detect_chat_id()
    if GROUP_CHAT_ID:
        print(f"Detected Group ID: {GROUP_CHAT_ID}")
        await send_reminder()
    else:
        print("Could not detect Group ID. Try again.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")