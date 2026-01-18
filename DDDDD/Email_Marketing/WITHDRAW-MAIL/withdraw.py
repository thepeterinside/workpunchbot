import smtplib
import pytz
import datetime
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def normalize_and_format_amount(raw: str) -> str:
    """
    - Remove currency symbols, whitespace and grouping commas.
    - Keep digits, optional leading '-', and a single decimal point.
    - Format with thousands separators:
        * integers -> "1,234,567"
        * decimals  -> "1,234,567.89" (always two decimals)
    """
    if not raw or raw.strip() == "":
        raise ValueError("Empty amount")

    # Remove common currency symbols and whitespace
    cleaned = raw.strip()
    # remove currency symbols and spaces, keep digits, dot and minus
    cleaned = re.sub(r"[^\d\.\-]", "", cleaned)

    # Validate cleaned string
    if cleaned.count('.') > 1:
        raise ValueError("Invalid amount format (more than one decimal point).")

    # If it parses as integer (no decimal point)
    if '.' not in cleaned:
        # allow negative
        try:
            ival = int(cleaned)
        except ValueError:
            raise ValueError("Invalid integer amount.")
        return f"{ival:,}"
    else:
        # parse float and format with two decimals
        try:
            fval = float(cleaned)
        except ValueError:
            raise ValueError("Invalid decimal amount.")
        # If the fractional part is .00, you could drop decimals — but per request we keep .00 for decimals input.
        # We'll format with two decimals.
        return f"{fval:,.2f}"

# Ask for receiver email
while True:
    receiver_email = input("Please provide the receiver email address: ").strip()
    receiver_email_confirm = input("Please re-enter the receiver email to confirm: ").strip()
    
    if receiver_email == receiver_email_confirm and receiver_email != "":
        break
    else:
        print("❌ The email addresses do not match. Please try again.\n")

# Ask for platform ID
while True:
    platform_id_1 = input("Please provide the client platform ID: ").strip()
    platform_id_2 = input("Please provide the client platform ID again to make sure: ").strip()

    if platform_id_1 == platform_id_2 and platform_id_1 != "":
        USERID = platform_id_1
        break
    else:
        print("❌ The platform IDs do not match. Please try again.\n")

# Ask for deposited amount and format it
while True:
    raw_amount = input("Please provide the withdrawn amount (e.g. 1234.56 or $1,234.56): ").strip()
    try:
        AMOUNT = normalize_and_format_amount(raw_amount)
        break
    except ValueError as e:
        print(f"❌ Invalid amount: {e}. Please try again.\n")

# Get today's date in US Eastern Time
us_timezone = pytz.timezone("US/Eastern")
today = datetime.datetime.now(us_timezone).strftime("%B %d, %Y")

# Email setup
sender_email = "support@tethergoldtrades.com"
password = "g.5dh7KsA8hX9:f"

msg = MIMEMultipart('alternative')
msg['Subject'] = "Withdrawal Confirmed!"
msg['From'] = sender_email
msg['To'] = receiver_email

# Load and personalize HTML
with open(r"D:\DDDDD\Email_Marketing\WITHDRAW-MAIL\index.html", "r", encoding="utf-8") as file:
    html_content = file.read()

html_content = (html_content
                .replace("{{USERID}}", USERID)
                .replace("{{AMOUNT}}", AMOUNT)
                .replace("{{DATE}}", today))

msg.attach(MIMEText(html_content, 'html'))

# Send email
server = smtplib.SMTP_SSL('smtppro.zoho.com', 465)
server.login(sender_email, password)
server.sendmail(sender_email, receiver_email, msg.as_string())
server.quit()

# Console confirmation
print(f"✅ Email sent successfully to ({USERID}) at {receiver_email} with amount: {AMOUNT}")
