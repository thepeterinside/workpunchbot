import asyncio
from telegram import Bot, Update
from telegram.error import TelegramError
from datetime import datetime, time
import pytz
from collections import defaultdict

BOT_TOKEN = "8226118285:AAGS7V-LIerygiiCXx8l96BhHm77Sy67SMI"
EST = pytz.timezone('US/Eastern')

# Store data per group
group_data = defaultdict(lambda: {
    'last_reminder_times': {},
    'last_processed_update_id': 0
})

async def detect_all_chat_ids():
    """Detect all group chats the bot is in."""
    bot = Bot(BOT_TOKEN)
    try:
        await bot.delete_webhook()
        updates = await bot.get_updates()
        group_chat_ids = set()
        
        for update in updates:
            if (update.message and 
                update.message.chat.type in ['group', 'supergroup'] and
                update.message.chat.id not in group_chat_ids):
                group_chat_ids.add(update.message.chat.id)
                print(f"Detected group: {update.message.chat.title} (ID: {update.message.chat.id})")
        
        return list(group_chat_ids)
        
    except TelegramError as e:
        print(f"Error: {e}")
        return []

async def handle_messages(bot, group_chat_ids):
    """Check for new messages and handle personalized reminders for all groups."""
    
    for group_id in group_chat_ids:
        group_info = group_data[group_id]
        
        try:
            # Get new updates for this group
            updates = await bot.get_updates(
                offset=group_info['last_processed_update_id'] + 1, 
                timeout=5
            )
            
            for update in updates:
                if (update.update_id > group_info['last_processed_update_id'] and
                    update.message and 
                    update.message.chat.id == group_id and
                    update.message.from_user):
                    
                    group_info['last_processed_update_id'] = update.update_id
                    
                    user_id = update.message.from_user.id
                    user_name = update.message.from_user.first_name
                    message_time = datetime.now(EST)
                    
                    # Check if we should send a reminder and avoid spamming
                    current_time = message_time.time()
                    last_reminder = group_info['last_reminder_times'].get(user_id)
                    
                    # Morning reminder (08:45 AM to 10:15 AM)
                    if time(8, 45) <= current_time <= time(10, 15):
                        # Only send reminder once per day per user
                        if last_reminder is None or last_reminder.date() != message_time.date():
                            await bot.send_message(
                                chat_id=group_id,
                                text=f"Good morning {user_name}, have a super productive day ahead. 🌞"
                            )
                            group_info['last_reminder_times'][user_id] = message_time
                    
                    # Night reminder (after 10:00 PM)
                    elif current_time >= time(22, 0):
                        # Only send reminder once per night per user
                        if last_reminder is None or last_reminder.date() != message_time.date() or last_reminder.hour < 22:
                            await bot.send_message(
                                chat_id=group_id,
                                text=f"Good night {user_name}, sleep tight. See you tomorrow. 🌙"
                            )
                            group_info['last_reminder_times'][user_id] = message_time
                            
        except TelegramError as e:
            print(f"Error handling messages for group {group_id}: {e}")

async def send_scheduled_messages(bot, group_chat_ids):
    """Send scheduled messages at specific times to all groups."""
    while True:
        now = datetime.now(EST)
        current_time = now.time()
        
        for group_id in group_chat_ids:
            try:
                # Morning message at 10:15 AM
                if current_time.hour == 10 and current_time.minute == 15:
                    await bot.send_message(
                        chat_id=group_id,
                        text="Good Morning Everyone 🌞\nToday is your best day!"
                    )
                    await asyncio.sleep(1)  # Small delay between groups

                # Report reminders at 1PM, 4PM, 7PM, 10PM
                elif current_time.hour in [13, 16, 19, 22] and current_time.minute == 0:
                    await bot.send_message(
                        chat_id=group_id,
                        text="⏰ UPDATE YOUR REPORT"
                    )
                    await asyncio.sleep(1)

                # Evening sign-off at 10:15 PM
                elif current_time.hour == 22 and current_time.minute == 15:
                    await bot.send_message(
                        chat_id=group_id,
                        text="See you tomorrow! 👋"
                    )
                    await asyncio.sleep(1)
                    
            except TelegramError as e:
                print(f"Error sending scheduled message to group {group_id}: {e}")

        # Check every 30 seconds
        await asyncio.sleep(30)

async def main():
    group_chat_ids = await detect_all_chat_ids()
    
    if group_chat_ids:
        print(f"Detected Group IDs: {group_chat_ids}")
        
        bot = Bot(BOT_TOKEN)
        
        # Clear any pending updates and initialize last processed IDs
        await bot.delete_webhook()
        updates = await bot.get_updates()
        
        if updates:
            for group_id in group_chat_ids:
                # Find the last update ID for each group
                group_updates = [u for u in updates if u.message and u.message.chat.id == group_id]
                if group_updates:
                    group_data[group_id]['last_processed_update_id'] = max(u.update_id for u in group_updates)
        
        # Run both message handling and scheduled messages concurrently
        await asyncio.gather(
            handle_messages_loop(bot, group_chat_ids),
            send_scheduled_messages(bot, group_chat_ids)
        )
    else:
        print("Could not detect any group IDs.")

async def handle_messages_loop(bot, group_chat_ids):
    """Continuous loop for handling messages for all groups."""
    while True:
        await handle_messages(bot, group_chat_ids)
        await asyncio.sleep(5)  # Check for new messages every 5 seconds

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
