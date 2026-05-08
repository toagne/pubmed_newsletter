import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

def send_email(to, subject, body):
	# Placeholder function to send an email
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = GMAIL_USER
	msg['To'] = to
	msg.set_content(body)

	with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
		server.login(GMAIL_USER, GMAIL_PASSWORD)
		server.send_message(msg)