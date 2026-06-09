import logging
from app import db
from app import pubmed
from app.pipeline import run_pipeline
from app.utils import get_last_month, logger

logging.basicConfig(level=logging.INFO)

PUB_TYPES = ["Journal Article", "Meta-Analysis", "Preprint", "Review", "Systematic Review"]
SUBJECT = "Your breaking news from the scientific world"


def run_monthly_job():
	logger.info("Running monthly job to send emails to users.")
	users = db.get_all_users()
	pubmed.get_journals_info() # to keep the journals info updated in the database
	if not users:
		logger.info("There are no users in db, just updating journals")
		return
	last_month = get_last_month()
	papers_cache = {}
	fetched_paper_ids = set()
	for user in users:
		if not user["receive_email"]:
			continue
		if not user.get("query") or not user.get("journals"):
			logger.warning(f"Skipping user id {user['id']}: missing query or journals")
			continue
		if not user.get("num_papers"):
			logger.warning(f"Skipping user id {user['id']}: missing num_papers")
			continue
		try:
			run_pipeline(user, last_month, papers_cache, fetched_paper_ids, PUB_TYPES, SUBJECT)
		except Exception:
			logger.error(f"Failed to process user id {user['id']}", exc_info=True)
	logger.info("Monthly job completed. Emails sent to all users.")
