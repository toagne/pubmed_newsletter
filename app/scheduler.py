from app import db
from app.emailer import send_email
from app import pubmed
from app.pipeline import run_pipeline
import logging

logging.basicConfig(level=logging.INFO)

def run_monthly_job():
	# logging.info("Running monthly job to send emails to users.")
	users = db.get_all_users()
	pubmed.get_journals_info() # to keep the journals info updated in the database
	papers_cache = {}
	fetched_paper_ids = set()
	
	for _, email, query, journals, n_of_papers in users:
		user_papers_ids = set(pubmed.get_ids(journals))
		# Find which papers we've already fetched
		new_ids = user_papers_ids - fetched_paper_ids
		# Fetch only new papers from PubMed
		if new_ids:
			new_papers = pubmed.get_all_papers(list(new_ids))
			for paper in new_papers:
				papers_cache[paper.pmid] = paper
			fetched_paper_ids.update(new_ids)
		# Build user's papers list from cache (both cached and newly fetched)
		user_papers = [papers_cache[pid] for pid in user_papers_ids if pid in papers_cache]
		# subject = f"Monthly Update on your query: {query}"
		body = run_pipeline(query, user_papers, n_of_papers)
		# send_email(email, subject, body)
	
	# logging.info("Monthly job completed. Emails sent to all users.")