import asyncio
from telegram import Bot, Update
from telegram.error import TelegramError
from datetime import datetime, time
import pytz

BOT_TOKEN = "8226118285:AAGS7V-LIerygiiCXx8l96BhHm77Sy67SMI"
GROUP_CHAT_ID = None  # Will detect automatically
EST = pytz.timezone('US/Eastern')

# Store last message times to avoid spamming users
last_reminder_times = {}
last_processed_update_id = 0

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

async def handle_messages(bot):
    """Check for new messages and handle personalized reminders."""
    global last_processed_update_id
    
    try:
        # Get new updates
        updates = await bot.get_updates(offset=last_processed_update_id + 1, timeout=10)
        
        for update in updates:
            if update.update_id > last_processed_update_id:
                last_processed_update_id = update.update_id
                
                if update.message and update.message.chat.id == GROUP_CHAT_ID and update.message.from_user:
                    user_id = update.message.from_user.id
                    user_name = update.message.from_user.first_name
                    message_time = datetime.now(EST)
                    
                    # Check if we should send a reminder and avoid spamming
                    current_time = message_time.time()
                    last_reminder = last_reminder_times.get(user_id)
                    
                    # Morning reminder (08:45 AM to 10:15 AM)
                    if time(8, 45) <= current_time <= time(10, 15):
                        # Only send reminder once per day per user
                        if last_reminder is None or last_reminder.date() != message_time.date():
                            await bot.send_message(
                                chat_id=GROUP_CHAT_ID,
                                text=f"Good morning {user_name}, have a super productive day ahead. 🌞"
                            )
                            last_reminder_times[user_id] = message_time
                    
                    # Night reminder (after 10:00 PM)
                    elif current_time >= time(22, 0):
                        # Only send reminder once per night per user
                        if last_reminder is None or last_reminder.date() != message_time.date() or last_reminder.hour < 22:
                            await bot.send_message(
                                chat_id=GROUP_CHAT_ID,
                                text=f"Good night {user_name}, sleep tight. See you tomorrow. 🌙"
                            )
                            last_reminder_times[user_id] = message_time
                            
    except TelegramError as e:
        print(f"Error handling messages: {e}")

async def send_scheduled_messages(bot):
    """Send scheduled messages at specific times."""
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
        
        bot = Bot(BOT_TOKEN)
        
        # Clear any pending updates
        await bot.delete_webhook()
        updates = await bot.get_updates()
        if updates:
            global last_processed_update_id
            last_processed_update_id = updates[-1].update_id
        
        # Run both message handling and scheduled messages concurrently
        await asyncio.gather(
            handle_messages_loop(bot),
            send_scheduled_messages(bot)
        )
    else:
        print("Could not detect Group ID.")

async def handle_messages_loop(bot):
    """Continuous loop for handling messages."""
    while True:
        await handle_messages(bot)
        await asyncio.sleep(5)  # Check for new messages every 5 seconds

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
