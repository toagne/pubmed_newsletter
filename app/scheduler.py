from app import db
from app.emailer import send_email
from app import pubmed
from app.pipeline import run_pipeline
from app.utils import chunk_list, get_last_month
from app import llm
import logging
import json

logging.basicConfig(level=logging.INFO)

def adapt_queries_with_llm(users):
	llm_queries = {}
	queries = [[u["id"], u["query"]] for u in users if u["receive_email"] == True]
	for batch in chunk_list(queries, 10, adapt_queries_with_llm.__name__):
		queries_payload = json.dumps({str(q[0]): q[1] for q in batch})
		response = llm.analyze_with_llm(llm.USER_QUERY_ANALYSIS_PROMPT, queries_payload)
		try:
			batch_result = json.loads(response)
			llm_queries.update(batch_result)
		except json.JSONDecodeError:
			for q in batch:
				keywords = llm.analyze_with_llm(llm.USER_QUERY_ANALYSIS_PROMPT, json.dumps({str(q[0]): q[1]}))
				llm_queries.update(json.loads(keywords))
	return llm_queries

def run_monthly_job():
	logging.info("Running monthly job to send emails to users.")
	pub_types = ["Journal Article", "Meta-Analysis", "Preprint", "Review", "Systematic Review"]
	users = db.get_all_users()
	pubmed.get_journals_info() # to keep the journals info updated in the database
	if not users:
		logging.info("There are no users in db, just updating journals")
		return
	llm_queries = adapt_queries_with_llm(users)
	papers_cache = {}
	fetched_paper_ids = set()
	last_month = get_last_month()
	subject = "Your breaking news from the scientific world"
	
	for user in users:
		if user["receive_email"]:
			logging.info(f"Processing user {user['email']}")
			if llm_queries.get(str(user["id"])).get('is_valid_research_query'):
				pubmed_keywords = llm_queries.get(str(user["id"])).get('pubmed_keywords')
				journals_names = db.get_journal_names_using_pmid(user["journals"])
				user_papers_ids = set(pubmed.get_ids(journals_names, pubmed_keywords, pub_types, last_month))
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
				
				similarity_search_query = llm_queries.get(str(user["id"])).get('vector_query')
				best_papers = run_pipeline(similarity_search_query, user["query"], user_papers, user["num_papers"])
				body = {
					"Description": user["query"],
					"Journals": journals_names,
					"N of papers": user["num_papers"],
					"Date": last_month,
					"Pub types": pub_types
				}
			else:
				body = "Profile contains no or not enough scientific research information. Please improve your research description."
			logging.info(f"Sending email to {user['email']}")
			send_email(user["email"], subject, body, best_papers)
			logging.info(f"Email succesfully sent to {user['email']}")

	logging.info("Monthly job completed. Emails sent to all users.")