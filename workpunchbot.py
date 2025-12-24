import time
from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable is not set!")
    print("Please set it using:")
    print("  export BOT_TOKEN='your-bot-token-here'")
    exit(1)

ADMIN_IDS = {7549969661, 5508742157}  # multiple admins

CHECK_INTERVAL = 60  # seconds

ACTIVITIES = {
    "🚽 Toilet (厕所)": {"limit": 10 * 60, "max": 3},
    "🍱 Food (吃饭)": {"limit": 30 * 60, "max": 3},
    "🚬 Smoke (抽烟)": {"limit": 10 * 60, "max": 3},
    "📌 Others (其他)": {"limit": 20 * 60, "max": 1},
}

# ================= DATA =================

users = {}

# ================= HELPERS =================

def format_seconds(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

def keyboard():
    # List of activity buttons
    activity_buttons = list(ACTIVITIES.keys())
    
    # Split into pairs for two buttons per row
    rows = [activity_buttons[i:i+2] for i in range(0, len(activity_buttons), 2)]
    
    # Add Start/Off buttons on the first row
    buttons = [["🟢 Start 开始", "🔴 OFF 下班"]] + rows
    
    # Add Back button at the bottom row
    buttons.append(["🔙 Back to Seat"])
    
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )

def get_user(uid, name):
    if uid not in users:
        users[uid] = {
            "name": name,
            "working": False,
            "start_work": None,
            "current": None,
            "start_ts": None,
            "counts": {k: 0 for k in ACTIVITIES},
            "leisure": 0,
        }
    return users[uid]

# ================= CORE HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initialize the bot and show keyboard."""
    user = update.effective_user
    get_user(user.id, user.full_name)
    
    welcome_text = (
        "👋 Work Punch Bot Ready!\n\n"
        "Use the buttons below to track your work activities.\n"
        "The buttons will remain visible for easy access."
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,
        reply_markup=keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    data = get_user(user.id, user.full_name)

    chat_id = update.effective_chat.id

    # ------------------ Start Work ------------------
    if text == "🟢 Start 开始":
        if data["working"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ You have already started work.",
                reply_markup=keyboard()
            )
            return

        data["working"] = True
        data["start_work"] = time.time()
        data["current"] = None
        data["start_ts"] = None
        # Reset daily counts if starting a new work day
        if data["counts"][list(ACTIVITIES.keys())[0]] > 0:
            data["counts"] = {k: 0 for k in ACTIVITIES}
            data["leisure"] = 0

        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Work started. You can now track your activities.",
            reply_markup=keyboard()
        )

    # ------------------ Activity Buttons ------------------
    elif text in ACTIVITIES:
        if not data["working"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Please start work first by clicking '🟢 Start 开始'",
                reply_markup=keyboard()
            )
            return

        if data["counts"][text] >= ACTIVITIES[text]["max"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ You have reached the maximum allowed times for {text} today ({ACTIVITIES[text]['max']}).",
                reply_markup=keyboard()
            )
            return

        if data["current"] is not None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ You are already on: {data['current']}\n"
                     f"Please click '🔙 Back to Seat' before starting a new activity.",
                reply_markup=keyboard()
            )
            return

        data["current"] = text
        data["start_ts"] = time.time()
        data["counts"][text] += 1

        limit_minutes = ACTIVITIES[text]["limit"] // 60
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏳ Started: {text}\nTime limit: {limit_minutes} minutes\nClick '🔙 Back to Seat' when you return.",
            reply_markup=keyboard()
        )

    # ------------------ Back to Seat ------------------
    elif text == "🔙 Back to Seat":
        if not data["working"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ You haven't started work yet.",
                reply_markup=keyboard()
            )
            return

        if data["current"] is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text="ℹ️ You are already at your seat.",
                reply_markup=keyboard()
            )
            return

        now = time.time()
        elapsed = int(now - data["start_ts"])
        limit = ACTIVITIES[data["current"]]["limit"]
        status = "✅ On Time" if elapsed <= limit else "⛔ Delayed"

        data["leisure"] += elapsed

        report = (
            f"📊 Activity Report\n"
            f"----------------------\n"
            f"👤 {data['name']}\n"
            f"🎯 Activity: {data['current']}\n"
            f"⏱️ Duration: {format_seconds(elapsed)}\n"
            f"📌 Status: {status}\n"
            f"----------------------\n"
        )

        for k in ACTIVITIES:
            activity_name = k.split()[1]
            report += f"• {activity_name}: {data['counts'][k]}/day\n"

        report += f"📈 Total Leisure Today: {format_seconds(data['leisure'])}\n"
        report += f"----------------------"

        data["current"] = None
        data["start_ts"] = None

        await context.bot.send_message(chat_id=chat_id, text=report, reply_markup=keyboard())

    # ------------------ Off Work ------------------
    elif text == "🔴 OFF 下班":
        if not data["working"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ You haven't started work yet.",
                reply_markup=keyboard()
            )
            return

        total_work = int(time.time() - data["start_work"])

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

        report += f"----------------------\n✅ Work session ended. Goodbye!"

        data["working"] = False
        data["current"] = None
        data["start_ts"] = None

        await context.bot.send_message(chat_id=chat_id, text=report, reply_markup=keyboard())


# ================= ADMIN VIEW =================

async def admin_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    lines = ["👀 *Admin Live View*\n"]

    for data in users.values():
        name = data["name"]

        if not data["working"]:
            status = "⛔ Off Work"
        elif data["current"] is None:
            status = "🟢 On Seat"
        else:
            elapsed = int(time.time() - data["start_ts"])
            limit = ACTIVITIES[data["current"]]["limit"]
            emoji = "⚠️" if elapsed > limit else "🔴"
            status = f"{emoji} {data['current']} ({format_seconds(elapsed)})"

        lines.append(f"• {name}: {status}")

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="\n".join(lines)
    )


# ================= AUTO FORGOT CHECK =================

async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    for uid, data in users.items():
        if data["current"]:
            elapsed = now - data["start_ts"]
            limit = ACTIVITIES[data["current"]]["limit"]

            if elapsed > limit:
                # Notify all admins without resetting status
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"⚠️ Delay-status: Employee: {data['name']} "
                                f"is delayed to get back to his seat.\n"
                                f"He has been on '{data['current']}' for {format_seconds(int(elapsed))}."
                            )
                        )
                    except:
                        pass


# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin_today", admin_today))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.job_queue.run_repeating(auto_check, interval=CHECK_INTERVAL)

    print("✅ Work Punch Bot Running...")
    print("⚠️ IMPORTANT: Make sure bot privacy is OFF in @BotFather")
    print("   Command: /setprivacy -> Disable")
    app.run_polling()


if __name__ == "__main__":
    main()
