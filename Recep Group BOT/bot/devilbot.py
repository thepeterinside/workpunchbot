import asyncio
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Set, List
from telegram import Bot
from telegram.error import TelegramError, Forbidden, RetryAfter
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
        self.last_messages: Dict[int, datetime] = {}
        self.last_tagging_time: Dict[str, datetime] = {}  # report_type: last tagging time
        self.tagged_users: Dict[str, Set[int]] = {}  # report_type: set of already tagged users

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
report_responses: Dict[int, Dict[str, Set[int]]] = {}

# Last update ID for message handling
last_update_id = 0

async def get_all_groups(bot: Bot):
    """Get all groups that the bot is currently in."""
    try:
        global last_update_id
        updates = await bot.get_updates(offset=last_update_id + 1, timeout=10, limit=100)
        detected_groups = {}
        
        for update in updates:
            if update.update_id > last_update_id:
                last_update_id = update.update_id
                
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
        
        for group_id, group_name in current_groups.items():
            if group_id not in groups_info:
                groups_info[group_id] = GroupInfo(group_id, group_name)
                report_responses[group_id] = {report_type: set() for report_type in REPORT_SCHEDULES.keys()}
                # Initialize tagging tracking for new group
                for report_type in REPORT_SCHEDULES.keys():
                    groups_info[group_id].tagged_users[report_type] = set()
                logger.info(f"Detected new group: {group_name} (ID: {group_id})")
        
    except Exception as e:
        logger.error(f"Error updating groups list: {e}")

async def is_admin_or_owner(bot: Bot, group_id: int, user_id: int) -> bool:
    """Check if a user is admin or owner of the group."""
    try:
        chat_member = await bot.get_chat_member(group_id, user_id)
        return chat_member.status in ['administrator', 'creator', 'owner']
    except Exception as e:
        logger.warning(f"Could not check admin status for user {user_id} in group {group_id}: {e}")
        return False

async def handle_incoming_messages(bot: Bot):
    """Check for new messages and handle greetings with optimized timing."""
    try:
        global last_update_id
        updates = await bot.get_updates(offset=last_update_id + 1, timeout=5, limit=50)
        
        for update in updates:
            if update.update_id > last_update_id:
                last_update_id = update.update_id
                
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
                for report_type in REPORT_SCHEDULES.keys():
                    groups_info[chat_id].tagged_users[report_type] = set()
            
            group_info = groups_info[chat_id]
            current_est = datetime.now(EST)
            group_info.last_messages[user_id] = current_est
            current_time = current_est.time()
            
            # 9-10 AM: Good morning greeting (only once per user per day)
            if time(9, 0) <= current_time < time(10, 0):
                if user_id not in group_info.user_reports:
                    group_info.user_reports[user_id] = set()
                
                if "morning_greeting" not in group_info.user_reports[user_id]:
                    greeting = f"Good morning {user_name}, have a super productive day ahead. ☀️"
                    await bot.send_message(chat_id=chat_id, text=greeting)
                    group_info.user_reports[user_id].add("morning_greeting")
                    logger.info(f"Sent morning greeting to {user_name}")
            
            # After 10 PM: Good night message (only once per user per night)
            elif current_time >= time(22, 0) or current_time < time(6, 0):
                if user_id not in group_info.user_reports:
                    group_info.user_reports[user_id] = set()
                
                if "night_greeting" not in group_info.user_reports[user_id]:
                    night_message = f"Good night {user_name}, sleep tight. See you tomorrow. 🌙"
                    await bot.send_message(chat_id=chat_id, text=night_message)
                    group_info.user_reports[user_id].add("night_greeting")
                    logger.info(f"Sent night message to {user_name}")
            
            # Track report responses for any message during report hours
            current_hour = current_time.hour
            if current_hour in [13, 16, 19, 21]:  # Report hours
                for report_type in REPORT_SCHEDULES.keys():
                    if report_type in report_responses.get(chat_id, {}):
                        report_responses[chat_id][report_type].add(user_id)
                        
    except RetryAfter as e:
        logger.warning(f"Rate limited, waiting {e.retry_after} seconds")
        await asyncio.sleep(e.retry_after)
    except Exception as e:
        logger.error(f"Error handling messages: {e}")

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
        logger.info(f"Sent {report_type} reminder to {group_info.group_name}")
        
        # Clear previous responses and tagging data for this report type
        if group_id in report_responses and report_type in report_responses[group_id]:
            report_responses[group_id][report_type].clear()
        if report_type in group_info.tagged_users:
            group_info.tagged_users[report_type].clear()
        if report_type in group_info.last_tagging_time:
            group_info.last_tagging_time[report_type] = datetime.now(EST)
            
    except RetryAfter as e:
        logger.warning(f"Rate limited while sending reminder, waiting {e.retry_after} seconds")
        await asyncio.sleep(e.retry_after)
    except Exception as e:
        logger.error(f"Error sending report reminder: {e}")

async def check_non_responders(bot: Bot):
    """Check for users who haven't responded to report requests with 150-second intervals."""
    try:
        est_time = datetime.now(EST)
        current_time = est_time.time()
        
        # Only check during appropriate times (1 hour after each report schedule)
        current_hour_minute = current_time.hour * 60 + current_time.minute
        should_check = False
        active_report_type = None
        
        for report_type, schedule_time in REPORT_SCHEDULES.items():
            schedule_minutes = schedule_time.hour * 60 + schedule_time.minute
            # Check within 1 hour after scheduled time
            if 0 <= (current_hour_minute - schedule_minutes) <= 60:
                should_check = True
                active_report_type = report_type
                break
        
        if not should_check or not active_report_type:
            return
        
        for group_id, group_info in groups_info.items():
            if not group_info.is_active or group_id not in report_responses:
                continue
            
            # Check if 150 seconds have passed since last tagging for this report type
            last_tag_time = group_info.last_tagging_time.get(active_report_type)
            if last_tag_time and (est_time - last_tag_time).total_seconds() < 150:
                continue
            
            responders = report_responses[group_id].get(active_report_type, set())
            recently_active_users = {
                user_id for user_id, last_msg_time in group_info.last_messages.items()
                if (est_time - last_msg_time).total_seconds() < 10800  # 3 hours
            }
            
            # Exclude responders and already tagged users
            non_responders = recently_active_users - responders
            previously_tagged = group_info.tagged_users.get(active_report_type, set())
            new_non_responders = non_responders - previously_tagged
            
            # Further filter out admins and owners
            final_non_responders = set()
            for user_id in new_non_responders:
                if not await is_admin_or_owner(bot, group_id, user_id):
                    final_non_responders.add(user_id)
            
            if final_non_responders:
                try:
                    # Get usernames for tagging
                    non_responder_names = []
                    for user_id in final_non_responders:
                        try:
                            chat_member = await bot.get_chat_member(group_id, user_id)
                            name = chat_member.user.first_name
                            if chat_member.user.username:
                                name = f"@{chat_member.user.username}"
                            non_responder_names.append(name)
                            
                            # Mark as tagged
                            if active_report_type not in group_info.tagged_users:
                                group_info.tagged_users[active_report_type] = set()
                            group_info.tagged_users[active_report_type].add(user_id)
                            
                        except Exception as e:
                            logger.warning(f"Could not get user info for {user_id}: {e}")
                    
                    if non_responder_names:
                        reminder_msg = "📋 Reminder: " + ", ".join(non_responder_names) + " - kindly post your report!"
                        await bot.send_message(chat_id=group_id, text=reminder_msg)
                        group_info.last_tagging_time[active_report_type] = est_time
                        logger.info(f"Tagged {len(non_responder_names)} users in {group_info.group_name}")
                        
                except RetryAfter as e:
                    logger.warning(f"Rate limited while tagging, waiting {e.retry_after} seconds")
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    logger.error(f"Error sending tagging message: {e}")
                    
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
            group_info.last_tagging_time.clear()
            for report_type in group_info.tagged_users:
                group_info.tagged_users[report_type].clear()
            group_info.last_reset_date = current_date

async def send_scheduled_reports(bot: Bot):
    """Send scheduled report reminders with minute-level precision."""
    est_time = datetime.now(EST)
    current_time = est_time.time()
    current_minute = (current_time.hour, current_time.minute)
    
    # Only check at specific minutes to reduce unnecessary processing
    if current_time.second > 10:
        return
    
    reset_daily_data()
    
    for report_type, schedule_time in REPORT_SCHEDULES.items():
        schedule_minute = (schedule_time.hour, schedule_time.minute)
        
        if current_minute == schedule_minute:
            for group_id in list(groups_info.keys()):
                await send_report_reminder(bot, group_id, report_type)

async def main():
    """Start the bot with optimized timing."""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        me = await bot.get_me()
        logger.info(f"Bot started as @{me.username}")
        
        await update_groups_list(bot)
        
        logger.info("Bot started. Press Ctrl+C to stop.")
        
        # Main loop with optimized timing
        while True:
            try:
                # Handle messages frequently but responsibly
                await handle_incoming_messages(bot)
                
                # Check schedules every minute
                current_second = datetime.now().second
                if current_second < 15:
                    await send_scheduled_reports(bot)
                    await check_non_responders(bot)
                
                # Update groups list less frequently
                if datetime.now().minute % 30 == 0:
                    await update_groups_list(bot)
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
