import asyncio
import logging
import random
import requests  # For fetching motivational quotes (optional)
from datetime import datetime, time, timedelta
from typing import Dict, Set
from telegram import Bot
from telegram.error import RetryAfter
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

# ---------------- MOTIVATIONAL QUOTES ----------------
MOTIVATIONAL_QUOTES = [
    "Keep pushing, you’re closer than you think 💪",
    "Consistency always beats motivation 🔥",
    "Another report, another step toward success 🚀",
    "Stay focused, the results are on their way 📈",
    "Teamwork makes the dream work 🤝",
    "You’re doing amazing — don’t slow down now ⚡",
    "Small wins add up to big victories 🏆",
    "Progress, not perfection. Keep going 🌱",
    "Love the energy today! Keep it rolling 💪",
    "Every update counts. Let’s make it happen 💼",
    "Hard work always pays off 💰",
    "You’re leveling up one report at a time 🎯",
    "Keep the hustle strong. You got this 🔥",
    "Discipline over everything. Stay sharp ⚔️",
    "Let’s finish the day strong 🌟"
]

def get_random_quote():
    """Fetch random quote from an API, fallback to local list."""
    try:
        resp = requests.get("https://type.fit/api/quotes", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return random.choice(data).get("text", random.choice(MOTIVATIONAL_QUOTES))
    except Exception:
        pass
    return random.choice(MOTIVATIONAL_QUOTES)
# -----------------------------------------------------

# ---------------- GROUP INFO -------------------------
class GroupInfo:
    def __init__(self, group_id: int, group_name: str):
        self.group_id = group_id
        self.group_name = group_name
        self.sent_reports_today: Set[str] = set()
        self.user_reports: Dict[int, Set[str]] = {}
        self.daily_report_count: Dict[int, int] = {}     # NEW
        self.consistency_score: Dict[int, int] = {}      # NEW
        self.last_reset_date = datetime.now(EST).date()
        self.is_active = True
        self.last_messages: Dict[int, datetime] = {}
        self.last_tagging_time: Dict[str, datetime] = {}
        self.tagged_users: Dict[str, Set[int]] = {}

groups_info: Dict[int, GroupInfo] = {}

# Report schedules (EST)
REPORT_SCHEDULES = {
    "1pm_report": time(13, 0),
    "4pm_report": time(16, 0),
    "7pm_report": time(19, 0),
    "final_report": time(21, 30)
}

REPORT_MESSAGES = {
    "1pm_report": "📋 POST YOUR REPORT",
    "4pm_report": "📋 POST YOUR REPORT",
    "7pm_report": "📋 POST YOUR REPORT",
    "final_report": "📊 UPDATE YOUR FINAL REPORT"
}

report_responses: Dict[int, Dict[str, Set[int]]] = {}
last_update_id = 0
# -----------------------------------------------------

async def get_all_groups(bot: Bot):
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
    try:
        current_groups = await get_all_groups(bot)
        for group_id, group_name in current_groups.items():
            if group_id not in groups_info:
                groups_info[group_id] = GroupInfo(group_id, group_name)
                report_responses[group_id] = {r: set() for r in REPORT_SCHEDULES.keys()}
                for r in REPORT_SCHEDULES.keys():
                    groups_info[group_id].tagged_users[r] = set()
                logger.info(f"Detected new group: {group_name} (ID: {group_id})")
    except Exception as e:
        logger.error(f"Error updating groups list: {e}")

async def is_admin_or_owner(bot: Bot, group_id: int, user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(group_id, user_id)
        return chat_member.status in ['administrator', 'creator', 'owner']
    except Exception:
        return False

async def handle_incoming_messages(bot: Bot):
    """Handle messages, greetings, and count reports."""
    global last_update_id
    try:
        updates = await bot.get_updates(offset=last_update_id + 1, timeout=5, limit=50)
        for update in updates:
            if update.update_id > last_update_id:
                last_update_id = update.update_id
            if not update.message or not update.message.chat.type in ['group', 'supergroup']:
                continue

            chat_id = update.message.chat.id
            user_id = update.message.from_user.id
            user_name = update.message.from_user.first_name

            if user_id == (await bot.get_me()).id:
                continue

            if chat_id not in groups_info:
                groups_info[chat_id] = GroupInfo(chat_id, update.message.chat.title or f"Group_{chat_id}")
                report_responses[chat_id] = {r: set() for r in REPORT_SCHEDULES.keys()}
                for r in REPORT_SCHEDULES.keys():
                    groups_info[chat_id].tagged_users[r] = set()

            group_info = groups_info[chat_id]
            current_est = datetime.now(EST)
            group_info.last_messages[user_id] = current_est
            current_time = current_est.time()

            # Morning greeting
            if time(9, 0) <= current_time < time(10, 0):
                if user_id not in group_info.user_reports:
                    group_info.user_reports[user_id] = set()
                if "morning_greeting" not in group_info.user_reports[user_id]:
                    await bot.send_message(chat_id, f"Good morning {user_name}, have a super productive day ahead. ☀️")
                    group_info.user_reports[user_id].add("morning_greeting")

            # Night greeting
            elif current_time >= time(22, 0) or current_time < time(6, 0):
                if user_id not in group_info.user_reports:
                    group_info.user_reports[user_id] = set()
                if "night_greeting" not in group_info.user_reports[user_id]:
                    await bot.send_message(chat_id, f"Good night {user_name}, sleep tight. See you tomorrow. 🌙")
                    group_info.user_reports[user_id].add("night_greeting")

            # Report responses
            current_hour = current_time.hour
            if current_hour in [13, 16, 19, 21]:
                for r_type in REPORT_SCHEDULES.keys():
                    if r_type in report_responses.get(chat_id, {}):
                        report_responses[chat_id][r_type].add(user_id)
                        # --- Count user participation ---
                        group_info.daily_report_count[user_id] = group_info.daily_report_count.get(user_id, 0) + 1
                        # --- Motivation trigger ---
                        if len(report_responses[chat_id][r_type]) >= 5 and "motivation_sent" not in group_info.sent_reports_today:
                            quote = get_random_quote()
                            await bot.send_message(chat_id, f"💬 {quote}")
                            group_info.sent_reports_today.add("motivation_sent")
                            logger.info(f"Sent motivation in {group_info.group_name}")

    except RetryAfter as e:
        logger.warning(f"Rate limited, waiting {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
    except Exception as e:
        logger.error(f"Error handling messages: {e}")

async def send_report_reminder(bot: Bot, group_id: int, report_type: str):
    try:
        if group_id not in groups_info:
            return
        group_info = groups_info[group_id]
        if report_type in group_info.sent_reports_today:
            return
        await bot.send_message(group_id, REPORT_MESSAGES[report_type])
        group_info.sent_reports_today.add(report_type)
        if group_id in report_responses and report_type in report_responses[group_id]:
            report_responses[group_id][report_type].clear()
        group_info.tagged_users[report_type].clear()
        group_info.last_tagging_time[report_type] = datetime.now(EST)
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")

async def check_non_responders(bot: Bot):
    try:
        est_time = datetime.now(EST)
        current_time = est_time.time()
        active_report = None
        for r_type, sched in REPORT_SCHEDULES.items():
            if 0 <= ((current_time.hour * 60 + current_time.minute) - (sched.hour * 60 + sched.minute)) <= 60:
                active_report = r_type
                break
        if not active_report:
            return
        for gid, ginfo in groups_info.items():
            if not ginfo.is_active or gid not in report_responses:
                continue
            last_tag = ginfo.last_tagging_time.get(active_report)
            if last_tag and (est_time - last_tag).total_seconds() < 150:
                continue
            responders = report_responses[gid].get(active_report, set())
            active_users = {u for u, t in ginfo.last_messages.items() if (est_time - t).total_seconds() < 10800}
            non_responders = active_users - responders - ginfo.tagged_users.get(active_report, set())
            final_nonresponders = {u for u in non_responders if not await is_admin_or_owner(bot, gid, u)}
            if final_nonresponders:
                names = []
                for uid in final_nonresponders:
                    try:
                        member = await bot.get_chat_member(gid, uid)
                        names.append(f"@{member.user.username}" if member.user.username else member.user.first_name)
                        ginfo.tagged_users[active_report].add(uid)
                    except Exception:
                        continue
                if names:
                    msg = "📋 Reminder: " + ", ".join(names) + " - kindly post your report!"
                    await bot.send_message(gid, msg)
                    ginfo.last_tagging_time[active_report] = est_time
    except Exception as e:
        logger.error(f"Error checking non-responders: {e}")

def reset_daily_data():
    est_time = datetime.now(EST)
    today = est_time.date()
    for ginfo in groups_info.values():
        if ginfo.last_reset_date != today:
            ginfo.sent_reports_today.clear()
            ginfo.user_reports.clear()
            ginfo.daily_report_count.clear()
            ginfo.last_tagging_time.clear()
            for r in ginfo.tagged_users:
                ginfo.tagged_users[r].clear()
            ginfo.last_reset_date = today

async def send_daily_summary(bot: Bot):
    """Send summary + leaderboard at 10 PM EST"""
    est_now = datetime.now(EST)
    if est_now.hour != 22 or est_now.minute != 0:
        return
    for gid, ginfo in groups_info.items():
        if not ginfo.is_active or not ginfo.daily_report_count:
            continue
        total = len(ginfo.daily_report_count)
        active = sum(1 for c in ginfo.daily_report_count.values() if c > 0)
        for uid in ginfo.daily_report_count:
            ginfo.consistency_score[uid] = ginfo.consistency_score.get(uid, 0)
            if ginfo.daily_report_count[uid] > 0:
                ginfo.consistency_score[uid] += 1
        leaderboard = sorted(ginfo.consistency_score.items(), key=lambda x: x[1], reverse=True)[:3]
        lines = []
        for i, (uid, score) in enumerate(leaderboard, 1):
            try:
                member = await bot.get_chat_member(gid, uid)
                name = f"@{member.user.username}" if member.user.username else member.user.first_name
                lines.append(f"{i}. {name} — {score} pts")
            except Exception:
                continue
        msg = f"📊 *Daily Report Summary*\n👥 Active members: {active}/{total}\n\n🏆 *Top Performers:*\n" + "\n".join(lines)
        await bot.send_message(gid, msg, parse_mode="Markdown")
        ginfo.daily_report_count.clear()
        logger.info(f"Sent summary to {ginfo.group_name}")

async def send_scheduled_reports(bot: Bot):
    est = datetime.now(EST)
    if est.second > 10:
        return
    reset_daily_data()
    for r_type, sched in REPORT_SCHEDULES.items():
        if (est.hour, est.minute) == (sched.hour, sched.minute):
            for gid in list(groups_info.keys()):
                await send_report_reminder(bot, gid, r_type)

async def main():
    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        logger.info(f"Bot started as @{me.username}")
        await update_groups_list(bot)
        logger.info("Bot running...")
        while True:
            await handle_incoming_messages(bot)
            now = datetime.now()
            if now.second < 15:
                await send_scheduled_reports(bot)
                await check_non_responders(bot)
                await send_daily_summary(bot)
            if now.minute % 30 == 0:
                await update_groups_list(bot)
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        await asyncio.sleep(30)
    finally:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
