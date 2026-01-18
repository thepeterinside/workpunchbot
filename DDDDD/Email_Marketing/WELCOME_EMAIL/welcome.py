import smtplib
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


while True:
    receiver_email = input("Please provide the receiver email address: ").strip()
    receiver_email_confirm = input("Please re-enter the receiver email to confirm: ").strip()
    
    if receiver_email == receiver_email_confirm and receiver_email != "":
        break
    else:
        print("❌ The email addresses do not match. Please try again.\n")


while True:
    platform_id_1 = input("Please provide the client platform ID: ").strip()
    platform_id_2 = input("Please provide the client platform ID again to make sure: ").strip()

    if platform_id_1 == platform_id_2 and platform_id_1 != "":
        USERID = platform_id_1
        break
    else:
        print("❌ The platform IDs do not match. Please try again.\n")


sender_email = "support@tethergoldtrades.com"
password = "g.5dh7KsA8hX9:f"

msg = MIMEMultipart('alternative')
msg['Subject'] = "Welcome to the Tether Gold Trading Family!"
msg['From'] = sender_email
msg['To'] = receiver_email


with open(r"D:\DDDDD\Email_Marketing\WELCOME_EMAIL\welcome.html", "r", encoding="utf-8") as file:
    html_content = file.read()


html_content = html_content.replace("{{USERID}}", USERID)


msg.attach(MIMEText(html_content, 'html'))

server = smtplib.SMTP_SSL('smtppro.zoho.com', 465)
server.login(sender_email, password)
server.sendmail(sender_email, receiver_email, msg.as_string())
server.quit()

print(f"✅ Email sent successfully to ({USERID}) at {receiver_email}")






