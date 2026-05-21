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

def create_pdf(papers):
	buffer = io.BytesIO()
	doc = SimpleDocTemplate(buffer)
	styles = getSampleStyleSheet()
	elements = []
	for i, p in enumerate(papers, 1):
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
			<b>Summary:</b>
			{p.summary}<br/>
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
	return buffer.read()

def send_email(to, subject, body, papers=None):
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = GMAIL_USER
	msg['To'] = to
	if papers:
		journals_text = "\n".join(f"- {j}" for j in body["Journals"])
		msg.set_content(f"""
In the attachment you can find the literature update for the last month.

Here you have a recap of the research interest details you selected:

Description: {body["Description"]}
Journals:
{journals_text}
Number of papers: {body["N of papers"]}
Pub Types: {", ".join(body["Pub types"])} (this is a fixed parameter)
""")

		pdf_bytes = create_pdf(papers)
		year, month = body["Date"].split("/")
		msg.add_attachment(
			pdf_bytes,
			maintype="application",
			subtype="pdf",
			filename=f"Literature Update_{year}_{month}.pdf"
		)
	else:
		msg.set_content(body)

	with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
		server.login(GMAIL_USER, GMAIL_PASSWORD)
		server.send_message(msg)