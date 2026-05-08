from app import db
from app.emailer import send_email
from app import pubmed
from app.pipeline import run_pipeline
import logging

logging.basicConfig(level=logging.INFO)

def run_monthly_job():
	# logging.info("Running monthly job to send emails to users.")
	# users = db.get_all_users()
	# papers = pubmed.get_all_papers() # for now here but could be moved inside the loop if we want to customize the papers sent to each user based on their query
	pubmed.get_journals_info() # to keep the journals info updated in the database
	
	# for email, query in users:
		# subject = f"Monthly Update on your query: {query}"
		# body = run_pipeline(query, papers)
		# send_email(email, subject, body)
	
	# logging.info("Monthly job completed. Emails sent to all users.")