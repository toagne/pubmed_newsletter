import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

def send_email(to, subject, content, send_email=True):
	# Placeholder function to send an email
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = GMAIL_USER
	msg['To'] = to
	if type(content).__name__ == "str":
		msg.set_content(content)
	if type(content).__name__ == "list":
		msg.set_content("this is the email body") # to change

		buffer = io.BytesIO()
		doc = SimpleDocTemplate(buffer)
		styles = getSampleStyleSheet()
		elements = []
		for i, p in enumerate(content, 1):
			text = f"""
			<b>Paper {i}</b><br/>
			<b>PMID:</b> {p.pmid}<br/>
			<b>Doi:</b> {p.doi}<br/>
			<b>Journal:</b> {p.journal}<br/>
			<b>Journal type:</b> {p.journal_type}<br/>
			<b>Publication date:</b> {p.publication_date}<br/>
			<b>Title:</b> {p.title}<br/>
			<b>Authors:</b> {p.authors}<br/>
			"""
			if p.summary:
				text += f"""
				<b>Summary:</b><br/>
				{p.title}
				<b>Relevance score:</b> {p.relevance_score}<br/>
				<b>Relevance explanation:</b> {p.relevance_explanation}<br/>
				"""
			else:
				text += f"""
				<b>Abstract:</b><br/>
				{p.abstract}
				"""
			paragraph = Paragraph(text, styles["BodyText"])
			elements.append(paragraph)
			elements.append(Spacer(1, 20))

		doc.build(elements)
		buffer.seek(0)
		pdf_bytes = buffer.read()
		if send_email:
			msg.add_attachment(
				pdf_bytes,
				maintype="application",
				subtype="pdf",
				filename="info.pdf"
			)
		else:
			with open(f"{to}.pdf", "wb") as f:
				f.write(pdf_bytes)

	if send_email:
		with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
			server.login(GMAIL_USER, GMAIL_PASSWORD)
			server.send_message(msg)