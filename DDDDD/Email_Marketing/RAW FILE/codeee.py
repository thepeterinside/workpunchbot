import smtplib
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def generate_code(length=9):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

while True:
    platform_id_1 = input("Please provide the client platform ID: ").strip()
    platform_id_2 = input("Please provide the client platform ID again to make sure: ").strip()

    if platform_id_1 == platform_id_2 and platform_id_1 != "":
        USERID = platform_id_1
        break
    else:
        print("❌ The platform IDs do not match. Please try again.\n")


random_code = generate_code()

sender_email = "support@webullusa.com"
receiver_email = "Luisoptions@gmail"
password = "XMXdhM_8!8GhN9W"

msg = MIMEMultipart('alternative')
msg['Subject'] = "Your Unique Withdrawal Code"
msg['From'] = sender_email
msg['To'] = receiver_email



with open(r"D:\DDDDD\Email_Marketing\WITHDRAWAL-CODE\index.html", "r", encoding="utf-8") as file:
    html_content = file.read()

html_content = html_content.replace("{{CODE}}", random_code)
html_content = html_content.replace("{{USERID}}", USERID)


msg.attach(MIMEText(html_content, 'html'))

server = smtplib.SMTP_SSL('smtppro.zoho.com', 465)
server.login(sender_email, password)
server.sendmail(sender_email, receiver_email, msg.as_string())
server.quit()

print(f"✅ Email sent successfully to ({USERID}) with code: {random_code}")




