from app import db
from app.emailer import send_email
from app import pubmed
from app.pipeline import run_pipeline
from app.utils import chunk_list
from app import llm
import logging
import json

logging.basicConfig(level=logging.INFO)

def run_monthly_job():
	# logging.info("Running monthly job to send emails to users.")
	users = db.get_all_users()
	llm_queries = {}
	queries = [[u[0], u[2]] for u in users]
	for batch in chunk_list(queries, 10):
		queries_payload = json.dumps({str(q[0]): q[1] for q in batch})
		response = llm.analyze_with_llm(llm.USER_QUERY_ANALYSIS_PROMPT, queries_payload)
		try:
			batch_result = json.loads(response)
			llm_queries.update(batch_result)
		except json.JSONDecodeError:
			for q in batch:
				keywords = llm.analyze_with_llm(llm.USER_QUERY_ANALYSIS_PROMPT, json.dumps({str(q[0]): q[1]}))
				llm_queries.update(json.loads(keywords))
	pubmed.get_journals_info() # to keep the journals info updated in the database
	papers_cache = {}
	fetched_paper_ids = set()
	
	for user_id, email, query, journals, n_of_papers in users:
		if llm_queries.get(str(user_id)).get('is_valid_research_query') == False:
			# do something else here
			continue
		pubmed_keywords = llm_queries.get(str(user_id)).get('pubmed_keywords')
		user_papers_ids = set(pubmed.get_ids(journals, pubmed_keywords))
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
		similarity_search_query = llm_queries.get(str(user_id)).get('vector_query')
		body = run_pipeline(similarity_search_query, query, user_papers, n_of_papers)
		# send_email(email, subject, body)
	
	# logging.info("Monthly job completed. Emails sent to all users.")