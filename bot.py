import time
import json
import os
from datetime import datetime, timedelta, time as dtime
import pytz

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram.ext import ChatMemberHandler

# IDs allowed to add the bot
OWNER_ID = {6047103658} # your owner ID(s)
ALLOWED_ADMINS = {6047103658}  # your Telegram ID(s)

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return  # Ignore updates without chat_member
    
    chat_member = update.chat_member
    chat = chat_member.chat
    member = chat_member.new_chat_member

    # If bot itself was added to a group
    if member.user.id == context.bot.id:
        if chat.id not in ALLOWED_GROUPS:
            # Notify the owner/admin
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"New group request: {chat.title} ({chat.id}) by {member.user.full_name}\n"
                    f"Admins: {list(ADMIN_IDS)}"
                )
            )
            # Leave the group automatically
            await context.bot.leave_chat(chat.id)



# ================= CONFIG =================

BOT_TOKEN = "8407516624:AAFchTuuLT8UsGVRUqj7VhaG3sGEYjEg39g"

ADMIN_IDS = {6047103658}  # Replace with actual admin Telegram user IDs

CHECK_INTERVAL = 60  # seconds

ALLOWED_GROUPS = []

async def approve_group(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve_group <chat_id>")
        return

    chat_id = int(context.args[0])
    ALLOWED_GROUPS.append(chat_id)
    save_allowed_groups()  # optional, save to JSON
    await update.message.reply_text(f"Group {chat_id} approved! Bot can now stay there.")


CHECK_INTERVAL = 60  # seconds

DATA_FILE = "users_data.json"

EST = pytz.timezone("US/Eastern")

ACTIVITIES = {
    "🚽 Toilet (厕所)": {"limit": 10 * 60, "max": 3},
    "🍱 Food (吃饭)": {"limit": 30 * 60, "max": 3},
    "🚬 Smoke (抽烟)": {"limit": 10 * 60, "max": 3},
    "📌 Others (其他)": {"limit": 20 * 60, "max": 1},
}

# ================= DATA =================

users = {}

# ================= CLALLED GROUP FUNCTION =================

# save_allowed_groups() example
def save_allowed_groups():
    with open("allowed_groups.json", "w") as f:
        json.dump(ALLOWED_GROUPS, f)

def load_allowed_groups():
    global ALLOWED_GROUPS
    if os.path.exists("allowed_groups.json"):
        with open("allowed_groups.json", "r") as f:
            ALLOWED_GROUPS = json.load(f)
    else:
        ALLOWED_GROUPS = []


# ================= PERSISTENCE =================

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

def load_users():
    global users
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Validate structure
                users = {k: v for k, v in loaded.items() if isinstance(v, dict)}
        except (json.JSONDecodeError, FileNotFoundError):
            users = {}
    else:
        users = {}



# ================= HELPERS =================

def format_seconds(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

def keyboard():
    activity_buttons = list(ACTIVITIES.keys())
    rows = [activity_buttons[i:i+2] for i in range(0, len(activity_buttons), 2)]
    buttons = [["🟢 Start 开始", "🔴 OFF 下班"]] + rows
    buttons.append(["🔙 Back to Seat"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_user(chat_id, uid, name):
    if chat_id not in users:
        users[chat_id] = {}

    if uid not in users[chat_id]:
        users[chat_id][uid] = {
            "name": name,
            "working": False,
            "start_work": None,
            "current": None,
            "start_ts": None,
            "counts": {k: 0 for k in ACTIVITIES},
            "leisure": 0,
        }
        save_users()
    return users[chat_id][uid]


# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    data = get_user(chat_id, user.id, user.full_name)


    await update.message.reply_text(
        "👋 Work Punch Bot Ready!",
        reply_markup=keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    data = chat_id = update.effective_chat.id
    data = get_user(chat_id, user.id, user.full_name)


    # -------- START WORK --------
    if text == "🟢 Start 开始":
        if data["working"]:
            await update.message.reply_text("⚠️ You already started work.", reply_markup=keyboard())
            return

        data["working"] = True
        data["start_work"] = time.time()
        data["current"] = None
        data["start_ts"] = None
        save_users()

        await update.message.reply_text("✅ Work started.", reply_markup=keyboard())

    # -------- ACTIVITY --------
    elif text in ACTIVITIES:
        if not data["working"]:
            await update.message.reply_text("⚠️ Please start work first.", reply_markup=keyboard())
            return

        if data["counts"][text] >= ACTIVITIES[text]["max"]:
            await update.message.reply_text("⚠️ Activity limit reached.", reply_markup=keyboard())
            return

        if data["current"]:
            await update.message.reply_text(
                f"⚠️ You are already on {data['current']}.",
                reply_markup=keyboard()
            )
            return

        data["current"] = text
        data["start_ts"] = time.time()
        data["counts"][text] += 1
        save_users()

        await update.message.reply_text(
            f"⏳ Started {text}.",
            reply_markup=keyboard()
        )

    # -------- BACK TO SEAT --------
    elif text == "🔙 Back to Seat":
        if not data["working"]:
            await update.message.reply_text("⚠️ Work not started.", reply_markup=keyboard())
            return

        if not data["current"]:
            await update.message.reply_text("ℹ️ Already on seat.", reply_markup=keyboard())
            return

        elapsed = int(time.time() - data["start_ts"])
        limit = ACTIVITIES[data["current"]]["limit"]
        status = "✅ On Time" if elapsed <= limit else "⛔ Delayed"

        data["leisure"] += elapsed
        current_activity = data["current"]
        data["current"] = None
        data["start_ts"] = None
        save_users()

        # --- Restored report format ---
        report = (
            f"📊 Activity Report\n"
            f"----------------------\n"
            f"👤 Employee: {data['name']}\n"
            f"🎯 Activity: {current_activity}\n"
            f"⏱️ Duration: {format_seconds(elapsed)}\n"
            f"📌 Status: {status}\n"
            f"----------------------\n"
        )
        for k in ACTIVITIES:
            activity_name = k.split()[1]  # Chinese part removed for display consistency
            report += f"• {activity_name}: {data['counts'][k]}/day\n"

        report += f"📈 Total Leisure Today: {format_seconds(data['leisure'])}\n"
        report += "----------------------"

        await update.message.reply_text(report, reply_markup=keyboard())

    # -------- OFF WORK --------
    elif text == "🔴 OFF 下班":
        if not data["working"]:
            await update.message.reply_text("⚠️ Work not started.", reply_markup=keyboard())
            return

        total_work = int(time.time() - data["start_work"])
        data["working"] = False
        data["current"] = None
        data["start_ts"] = None
        save_users()

        # --- Restored report format ---
        report = (
            f"📊 End of Work Report\n"
            f"----------------------\n"
            f"👤 Employee: {data['name']}\n"
            f"⏰ Total Working: {format_seconds(total_work)}\n"
            f"🎯 Total Leisure: {format_seconds(data['leisure'])}\n"
            f"----------------------\n"
        )
        for k in ACTIVITIES:
            activity_name = k.split()[1]
            report += f"• {activity_name}: {data['counts'][k]} times\n"
        report += "----------------------\n"
        report += "✅ Work session ended. Goodbye!"

        await update.message.reply_text(report, reply_markup=keyboard())

# ================= ADMIN =================

async def admin_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    lines = ["👀 Admin Live View\n"]
    chat_id = update.effective_chat.id

    if chat_id not in users:
        lines.append("No data for this group yet.")
    else:
        for data in users[chat_id].values():
            if not data["working"]:
                status = "⛔ Off"
            elif not data["current"]:
                status = "🟢 On Seat"
            else:
                elapsed = int(time.time() - data["start_ts"])
                status = f"⚠️ {data['current']} ({format_seconds(elapsed)})"

            lines.append(f"{data['name']}: {status}")

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="\n".join(lines)
    )


# ================= AUTO CHECK =================

async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    for data in users.values():
        if not isinstance(data, dict):
            continue  # Skip invalid entries
        if data.get("current"):  # Safe access
            elapsed = now - data["start_ts"]
            limit = ACTIVITIES[data["current"]]["limit"]
            if elapsed > limit:
                for admin in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin,
                            text=f"⚠️ {data['name']} delayed on {data['current']} ({format_seconds(int(elapsed))})"
                        )
                    except:
                        pass



# ================= DAILY RESET =================

async def daily_reset(context: ContextTypes.DEFAULT_TYPE):
    for data in users.values():
        data["working"] = False
        data["current"] = None
        data["start_ts"] = None
        data["start_work"] = None
        data["counts"] = {k: 0 for k in ACTIVITIES}
        data["leisure"] = 0

    save_users()

    for admin in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin,
                text="🕛 Daily reset completed (12:00 AM EST)."
            )
        except:
            pass

# ================= MAIN =================

def main():
    load_users()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin_today", admin_today))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    app.job_queue.run_repeating(auto_check, interval=CHECK_INTERVAL)

    now = datetime.now(EST)
    midnight = datetime.combine(now.date(), dtime(0, 0), tzinfo=EST)
    if now >= midnight:
        midnight += timedelta(days=1)

    app.job_queue.run_repeating(
        daily_reset,
        interval=86400,
        first=(midnight - now).total_seconds()
    )

    print("✅ Work Punch Bot Running")
    app.run_polling()

if __name__ == "__main__":
    main()
