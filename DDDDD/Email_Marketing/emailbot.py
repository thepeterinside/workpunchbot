import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)
import smtplib
import pytz
import datetime
import re
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Email configuration (from your existing code)
SENDER_EMAIL = "support@tethergoldtrades.com"
EMAIL_PASSWORD = "g.5dh7KsA8hX9:f"
SMTP_SERVER = 'smtppro.zoho.com'
SMTP_PORT = 465

# HTML template paths (update these paths as needed)
TEMPLATE_PATHS = {
    'welcome': r"D:\DDDDD\Email_Marketing\WELCOME_EMAIL\welcome.html",
    'deposit': r"D:\DDDDD\Email_Marketing\DEPOSIT-MAIL\index.html",
    'withdraw_code': r"D:\DDDDD\Email_Marketing\WITHDRAWAL-CODE\index.html",
    'withdraw': r"D:\DDDDD\Email_Marketing\WITHDRAW-MAIL\index.html"
}

# Conversation states
SELECTING_ACTION, ENTERING_EMAIL, CONFIRMING_EMAIL, ENTERING_USERID, CONFIRMING_USERID, ENTERING_AMOUNT, SENDING_EMAIL = range(7)

# Store user data
user_data = {}

def normalize_and_format_amount(raw: str) -> str:
    """Your existing amount formatting function"""
    if not raw or raw.strip() == "":
        raise ValueError("Empty amount")

    cleaned = raw.strip()
    cleaned = re.sub(r"[^\d\.\-]", "", cleaned)

    if cleaned.count('.') > 1:
        raise ValueError("Invalid amount format (more than one decimal point).")

    if '.' not in cleaned:
        try:
            ival = int(cleaned)
        except ValueError:
            raise ValueError("Invalid integer amount.")
        return f"{ival:,}"
    else:
        try:
            fval = float(cleaned)
        except ValueError:
            raise ValueError("Invalid decimal amount.")
        return f"{fval:,.2f}"

def generate_code(length=9):
    """Your existing code generation function"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def send_email_sync(email_type: str, user_info: dict):
    """Synchronous function to send email - can be called from thread"""
    try:
        receiver_email = user_info['email']
        userid = user_info['userid']
        
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        
        # Load and personalize HTML template
        template_path = TEMPLATE_PATHS[email_type]
        with open(template_path, "r", encoding="utf-8") as file:
            html_content = file.read()

        generated_code = None

        if email_type == 'welcome':
            msg['Subject'] = "Welcome to the Tether Gold Trading Family!"
            html_content = html_content.replace("{{USERID}}", userid)
            
        elif email_type == 'deposit':
            msg['Subject'] = "Deposit Confirmed!"
            amount = user_info['amount']
            us_timezone = pytz.timezone("US/Eastern")
            today = datetime.datetime.now(us_timezone).strftime("%B %d, %Y")
            html_content = (html_content
                          .replace("{{USERID}}", userid)
                          .replace("{{AMOUNT}}", amount)
                          .replace("{{DATE}}", today))
            
        elif email_type == 'withdraw_code':
            msg['Subject'] = "Your Unique Withdrawal Code"
            random_code = generate_code()
            html_content = html_content.replace("{{CODE}}", random_code)
            html_content = html_content.replace("{{USERID}}", userid)
            generated_code = random_code
            
        elif email_type == 'withdraw':
            msg['Subject'] = "Withdrawal Confirmed!"
            amount = user_info['amount']
            us_timezone = pytz.timezone("US/Eastern")
            today = datetime.datetime.now(us_timezone).strftime("%B %d, %Y")
            html_content = (html_content
                          .replace("{{USERID}}", userid)
                          .replace("{{AMOUNT}}", amount)
                          .replace("{{DATE}}", today))

        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        
        return True, generated_code
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False, None

async def send_email_handler(email_type: str, user_id: int):
    """Async wrapper for email sending"""
    try:
        # Run the synchronous email sending in a thread pool
        success, generated_code = await asyncio.get_event_loop().run_in_executor(
            None, send_email_sync, email_type, user_data[user_id]
        )
        return success, generated_code
    except Exception as e:
        logger.error(f"Error in send_email_handler: {e}")
        return False, None

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu with email options"""
    keyboard = [
        ["📧 Welcome Mail", "💰 Deposit Mail"],
        ["🔐 Withdrawal Code", "💸 Withdrawal Mail"],
        ["❌ Cancel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "<b>🤖 Email Bot - Tether Gold Support</b>\n\n"
        "Please select the type of email you want to send:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECTING_ACTION

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show main menu with welcome message"""
    user_id = update.effective_user.id
    user_data[user_id] = {'current_action': None}
    
    # Welcome message with developer credit
    welcome_message = (
        "<b>👋 Welcome to Tether Gold Email Bot!</b>\n\n"
        "This bot helps you send professional emails to clients quickly and efficiently.\n\n"
        "<i>💡 This bot has been coded and developed by Peter Inside</i>\n\n"
        "Select an email type below to get started:"
    )
    
    keyboard = [
        ["📧 Welcome Mail", "💰 Deposit Mail"],
        ["🔐 Withdrawal Code", "💸 Withdrawal Mail"],
        ["❌ Cancel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECTING_ACTION

async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action selection"""
    user_id = update.effective_user.id
    text = update.message.text
    
    action_map = {
        "📧 Welcome Mail": 'welcome',
        "💰 Deposit Mail": 'deposit', 
        "🔐 Withdrawal Code": 'withdraw_code',
        "💸 Withdrawal Mail": 'withdraw'
    }
    
    if text == "❌ Cancel":
        await update.message.reply_text(
            "Operation cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
        
    if text in action_map:
        user_data[user_id]['current_action'] = action_map[text]
        user_data[user_id]['step'] = 'email'
        
        await update.message.reply_text(
            "Please enter the recipient's email address:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ENTERING_EMAIL
    else:
        await update.message.reply_text("Please select a valid option from the menu.")
        return SELECTING_ACTION

async def enter_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store email and ask for confirmation"""
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        await update.message.reply_text("❌ Invalid email format. Please enter a valid email address:")
        return ENTERING_EMAIL
    
    user_data[user_id]['temp_email'] = email
    
    keyboard = [["✅ Confirm Email", "❌ Re-enter Email"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Email: {email}\n\nIs this correct?",
        reply_markup=reply_markup
    )
    return CONFIRMING_EMAIL

async def confirm_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email confirmation"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "✅ Confirm Email":
        user_data[user_id]['email'] = user_data[user_id]['temp_email']
        del user_data[user_id]['temp_email']
        
        await update.message.reply_text(
            "Please enter the client platform ID:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ENTERING_USERID
    else:
        await update.message.reply_text("Please enter the email address again:")
        return ENTERING_EMAIL

async def enter_userid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store user ID and ask for confirmation"""
    user_id = update.effective_user.id
    userid = update.message.text.strip()
    
    if not userid:
        await update.message.reply_text("❌ Platform ID cannot be empty. Please enter the client platform ID:")
        return ENTERING_USERID
    
    user_data[user_id]['temp_userid'] = userid
    
    keyboard = [["✅ Confirm Platform ID", "❌ Re-enter Platform ID"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Platform ID: {userid}\n\nIs this correct?",
        reply_markup=reply_markup
    )
    return CONFIRMING_USERID

async def confirm_userid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user ID confirmation"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "✅ Confirm Platform ID":
        user_data[user_id]['userid'] = user_data[user_id]['temp_userid']
        del user_data[user_id]['temp_userid']
        
        current_action = user_data[user_id]['current_action']
        
        # Check if we need amount input
        if current_action in ['deposit', 'withdraw']:
            await update.message.reply_text(
                "Please enter the amount (e.g., 1234.56 or $1,234.56):",
                reply_markup=ReplyKeyboardRemove()
            )
            return ENTERING_AMOUNT
        else:
            # For welcome and withdrawal code, we can send immediately
            await update.message.reply_text("🔄 Sending email...")
            return await send_email(update, context)
    else:
        await update.message.reply_text("Please enter the platform ID again:")
        return ENTERING_USERID

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store and validate amount"""
    user_id = update.effective_user.id
    raw_amount = update.message.text.strip()
    
    try:
        formatted_amount = normalize_and_format_amount(raw_amount)
        user_data[user_id]['amount'] = formatted_amount
        
        await update.message.reply_text("🔄 Sending email...")
        return await send_email(update, context)
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Invalid amount: {e}. Please enter the amount again:")
        return ENTERING_AMOUNT

async def send_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the actual email and return to main menu"""
    user_id = update.effective_user.id
    current_action = user_data[user_id]['current_action']
    
    try:
        # Use the async email handler
        success, generated_code = await send_email_handler(current_action, user_id)
        
        if success:
            user_info = user_data[user_id]
            message = f"✅ <b>Email sent successfully!</b>\n\n"
            message += f"📧 <b>Recipient:</b> {user_info['email']}\n"
            message += f"🆔 <b>Platform ID:</b> {user_info['userid']}\n"
            
            if generated_code:
                message += f"🔐 <b>Generated Code:</b> {generated_code}\n"
            if 'amount' in user_info:
                message += f"💰 <b>Amount:</b> {user_info['amount']}\n"
                
            # Send success message first
            await update.message.reply_text(message, parse_mode='HTML')
            
        else:
            await update.message.reply_text("❌ <b>Failed to send email.</b> Please try again.", parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Error in send_email: {e}")
        await update.message.reply_text("❌ <b>An error occurred while sending the email.</b>", parse_mode='HTML')
    
    # Clean up user data for this operation
    if user_id in user_data:
        # Only remove the operation-specific data, keep the user_id entry
        user_data[user_id] = {'current_action': None}
    
    # Always return to main menu after operation (success or failure)
    return await show_main_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation and return to main menu"""
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id] = {'current_action': None}
    
    await update.message.reply_text(
        "Operation cancelled. Returning to main menu...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Return to main menu instead of ending conversation
    return await show_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
<b>🤖 Tether Gold Email Bot Help</b>

<i>This bot has been coded and developed by Peter Inside</i>

<b>Available Commands:</b>
/start - Start the bot and select email type
/help - Show this help message
/cancel - Cancel current operation

<b>Email Types:</b>
• 📧 Welcome Mail - Send welcome email to new clients
• 💰 Deposit Mail - Send deposit confirmation  
• 🔐 Withdrawal Code - Generate and send withdrawal code
• 💸 Withdrawal Mail - Send withdrawal confirmation

<b>How to use:</b>
1. Use /start to begin
2. Select email type from menu
3. Follow the prompts to enter details
4. Confirm information before sending
5. After sending, you'll return to main menu for next operation
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

def main():
    """Start the bot"""
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token from BotFather
    TOKEN = "8420317112:AAHKkN7acTvKkcPKV4snDcRKNEX0GvcdfRI"
    
    application = Application.builder().token(TOKEN).build()
    
    # Conversation handler for the main flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_action)
            ],
            ENTERING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_email)
            ],
            CONFIRMING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_email)
            ],
            ENTERING_USERID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_userid)
            ],
            CONFIRMING_USERID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_userid)
            ],
            ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)
            ],
            SENDING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, send_email)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('help', help_command)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel))
    
    # Start the Bot
    print("🤖 Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()