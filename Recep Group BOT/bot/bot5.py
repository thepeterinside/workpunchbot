import asyncio
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Set, List
from telegram import Bot, Update
from telegram.error import TelegramError, Forbidden
import pytz

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8226118285:AAGS7V-LIerygiiCXx8l96BhHm77Sy67SMI"

# Timezone
EST = pytz.timezone('US/Eastern')

# Group information class
class GroupInfo:
    def __init__(self, group_id: int, group_name: str):
        self.group_id = group_id
        self.group_name = group_name
        self.sent_reports_today: Set[str] = set()
        self.user_reports: Dict[int, Set[str]] = {}
        self.last_reset_date = datetime.now(EST).date()
        self.is_active = True
        self.last_messages: Dict[int, datetime] = {}  # user_id: last message time

# Store group information
groups_info: Dict[int, GroupInfo] = {}

# Report schedules (EST time)
REPORT_SCHEDULES = {
    "1pm_report": time(13, 0),    # 1:00 PM EST
    "4pm_report": time(16, 0),    # 4:00 PM EST
    "7pm_report": time(19, 0),    # 7:00 PM EST
    "final_report": time(21, 30)  # 9:30 PM EST
}

# Report messages
REPORT_MESSAGES = {
    "1pm_report": "📋 POST YOUR REPORT",
    "4pm_report": "📋 POST YOUR REPORT", 
    "7pm_report": "📋 POST YOUR REPORT",
    "final_report": "📊 UPDATE YOUR FINAL REPORT"
}

# Track report responses
report_responses: Dict[int, Dict[str, Set[int]]] = {}  # group_id: {report_type: set(user_ids)}

async def get_all_groups(bot: Bot):
    """Get all groups that the bot is currently in."""
    try:
        updates = await bot.get_updates(limit=100, timeout=30)
        detected_groups = {}
        
        for update in updates:
            if update.message and update.message.chat.type in ['group', 'supergroup']:
                chat = update.message.chat
                if chat.id not in detected_groups:
                    detected_groups[chat.id] = chat.title or f"Group_{chat.id}"
        
        return detected_groups
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return {}

async def update_groups_list(bot: Bot):
    """Update the list of groups the bot is in."""
    try:
        current_groups = await get_all_groups(bot)
        
        # Add new groups
        for group_id, group_name in current_groups.items():
            if group_id not in groups_info:
                groups_info[group_id] = GroupInfo(group_id, group_name)
                report_responses[group_id] = {report_type: set() for report_type in REPORT_SCHEDULES.keys()}
                logger.info(f"Detected new group: {group_name} (ID: {group_id})")
        
        logger.info(f"Currently monitoring {len(groups_info)} groups")
        
    except Exception as e:
        logger.error(f"Error updating groups list: {e}")

async def handle_incoming_messages(bot: Bot):
    """Check for new messages and handle greetings."""
    try:
        updates = await bot.get_updates(offset=-1, timeout=10, limit=10)
        
        for update in updates:
            if not update.message or not update.message.chat.type in ['group', 'supergroup']:
                continue
            
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id
            user_name = update.message.from_user.first_name
            
            # Skip if message is from bot itself
            if user_id == (await bot.get_me()).id:
                continue
            
            # Initialize group if not exists
            if chat_id not in groups_info:
                groups_info[chat_id] = GroupInfo(chat_id, update.message.chat.title or f"Group_{chat_id}")
                report_responses[chat_id] = {report_type: set() for report_type in REPORT_SCHEDULES.keys()}
            
            group_info = groups_info[chat_id]
            group_info.last_messages[user_id] = datetime.now(EST)
            
            # Get current EST time
            est_time = datetime.now(EST)
            current_time = est_time.time()
            
            # 9-10 AM: Good morning greeting (only once per user per day)
            if time(9, 0) <= current_time < time(10, 0):
                if user_id not in group_info.user_reports:
                    group_info.user_reports[user_id] = set()
                
                if "morning_greeting" not in group_info.user_reports[user_id]:
                    greeting = f"Good morning {user_name}, have a super productive day ahead. ☀️"
                    await bot.send_message(chat_id=chat_id, text=greeting)
                    group_info.user_reports[user_id].add("morning_greeting")
                    logger.info(f"Sent morning greeting to {user_name} in group {group_info.group_name}")
            
            # After 10 PM: Good night message (only once per user per night)
            elif current_time >= time(22, 0) or current_time < time(6, 0):
                if user_id not in group_info.user_reports:
                    group_info.user_reports[user_id] = set()
                
                if "night_greeting" not in group_info.user_reports[user_id]:
                    night_message = f"Good night {user_name}, sleep tight. See you tomorrow. 🌙"
                    await bot.send_message(chat_id=chat_id, text=night_message)
                    group_info.user_reports[user_id].add("night_greeting")
                    logger.info(f"Sent night message to {user_name} in group {group_info.group_name}")
            
            # Track report responses
            for report_type in REPORT_SCHEDULES.keys():
                if report_type in report_responses.get(chat_id, {}):
                    report_responses[chat_id][report_type].add(user_id)
                    
    except Exception as e:
        logger.error(f"Error handling incoming messages: {e}")

async def send_report_reminder(bot: Bot, group_id: int, report_type: str):
    """Send report reminder to a group."""
    try:
        if group_id not in groups_info:
            return
        
        group_info = groups_info[group_id]
        
        if report_type in group_info.sent_reports_today:
            return
        
        message = REPORT_MESSAGES[report_type]
        await bot.send_message(chat_id=group_id, text=message)
        
        group_info.sent_reports_today.add(report_type)
        logger.info(f"Sent {report_type} reminder to group {group_info.group_name}")
        
        # Clear previous responses for this report type
        if group_id in report_responses and report_type in report_responses[group_id]:
            report_responses[group_id][report_type].clear()
            
    except Exception as e:
        logger.error(f"Error sending report reminder: {e}")

async def check_non_responders(bot: Bot):
    """Check for users who haven't responded to report requests."""
    try:
        est_time = datetime.now(EST)
        current_time = est_time.time()
        
        # Only check during report hours (1PM-8PM for daily reports, 9:30PM-10PM for final)
        if not ((time(13, 0) <= current_time < time(20, 0)) or 
                (time(21, 30) <= current_time < time(22, 0))):
            return
        
        for group_id, group_info in groups_info.items():
            if not group_info.is_active:
                continue
            
            active_report_type = None
            for report_type, schedule_time in REPORT_SCHEDULES.items():
                schedule_end_time = time(schedule_time.hour + 1, schedule_time.minute)
                if schedule_time <= current_time < schedule_end_time:
                    active_report_type = report_type
                    break
            
            if not active_report_type or group_id not in report_responses:
                continue
            
            responders = report_responses[group_id][active_report_type]
            
            # Get recent active users (those who sent messages in the last 2 hours)
            recent_users = set()
            for user_id, last_msg_time in group_info.last_messages.items():
                if (est_time - last_msg_time).total_seconds() < 7200:  # 2 hours
                    recent_users.add(user_id)
            
            # Find non-responders among recent users
            non_responders = recent_users - responders
            
            if non_responders:
                try:
                    # Try to get usernames for tagging
                    non_responder_names = []
                    for user_id in non_responders:
                        try:
                            chat_member = await bot.get_chat_member(group_id, user_id)
                            name = chat_member.user.first_name
                            if chat_member.user.username:
                                name = f"@{chat_member.user.username}"
                            non_responder_names.append(name)
                        except:
                            non_responder_names.append(f"user_{user_id}")
                    
                    if non_responder_names:
                        reminder_msg = "Reminder: " + ", ".join(non_responder_names) + " - kindly post your report. 📋"
                        await bot.send_message(chat_id=group_id, text=reminder_msg)
                        logger.info(f"Sent non-responder reminder in group {group_info.group_name}")
                        
                except Exception as e:
                    logger.warning(f"Couldn't send individual reminders: {e}")
                    # Send general reminder
                    await bot.send_message(chat_id=group_id, text="Reminder: Please don't forget to post your report! 📋")
                    
    except Exception as e:
        logger.error(f"Error checking non-responders: {e}")

def reset_daily_data():
    """Reset daily data at midnight EST."""
    est_time = datetime.now(EST)
    current_date = est_time.date()
    
    for group_info in groups_info.values():
        if group_info.last_reset_date != current_date:
            group_info.sent_reports_today.clear()
            group_info.user_reports.clear()
            group_info.last_messages.clear()
            group_info.last_reset_date = current_date
            logger.info(f"Reset daily data for {group_info.group_name}")
    
    # Reset report responses
    for group_id in report_responses:
        for report_type in report_responses[group_id]:
            report_responses[group_id][report_type].clear()

async def send_scheduled_reports(bot: Bot):
    """Send scheduled report reminders."""
    # Reset daily data if it's a new day
    reset_daily_data()
    
    # Get current EST time
    est_time = datetime.now(EST)
    current_time = est_time.time()
    current_hour_minute = (current_time.hour, current_time.minute)
    
    # Check each report schedule
    for report_type, schedule_time in REPORT_SCHEDULES.items():
        schedule_hour_minute = (schedule_time.hour, schedule_time.minute)
        
        # Check if it's time to send this report reminder
        if current_hour_minute == schedule_hour_minute:
            for group_id in list(groups_info.keys()):
                await send_report_reminder(bot, group_id, report_type)

async def periodic_group_update(bot: Bot):
    """Periodically update the list of groups."""
    while True:
        try:
            await asyncio.sleep(3600)  # Update every hour
            await update_groups_list(bot)
        except Exception as e:
            logger.error(f"Error in periodic group update: {e}")
            await asyncio.sleep(300)

async def main():
    """Start the bot."""
    # Create the bot instance
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Test bot connection
        me = await bot.get_me()
        logger.info(f"Bot started as @{me.username}")
        
        # Initial group detection
        await update_groups_list(bot)
        
        # Start periodic tasks
        update_task = asyncio.create_task(periodic_group_update(bot))
        
        logger.info("Bot started. Press Ctrl+C to stop.")
        
        # Main loop
        while True:
            try:
                # Handle incoming messages
                await handle_incoming_messages(bot)
                
                # Send scheduled reports
                await send_scheduled_reports(bot)
                
                # Check for non-responders
                await check_non_responders(bot)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)
                
    except asyncio.CancelledError:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Cleanup
        if 'update_task' in locals():
            update_task.cancel()
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
