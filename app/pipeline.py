from copy import copy
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.stores import InMemoryByteStore
from langchain_classic.embeddings import CacheBackedEmbeddings

import json

from app.utils import chunk_list, format_batch, logger, adapt_queries_with_llm
from app import llm
from app import db
from app import pubmed
from app.emailer import send_email

_embedding_store = InMemoryByteStore()
_base_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
_embeddings = CacheBackedEmbeddings.from_bytes_store(
	_base_embeddings,
	_embedding_store,
	namespace="text-embedding-3-small"
)


def analyze_papers(papers, query, batch_size=10):
	logger.info("Running LLM analysis...")
	llm_res = {}
	for batch in chunk_list(papers, batch_size, analyze_papers.__name__):
		content = format_batch(batch, query)
		response = llm.analyze_with_llm(llm.TOP_PAPERS_ANALYSIS_PROMPT, json.dumps(content))
		try:
			batch_result = json.loads(response)
			llm_res.update(batch_result)
		except json.JSONDecodeError:
			logger.error("Skipping batch due to json error")
			continue
	papers_copies = {str(p.pmid): copy(p) for p in papers}
	for pmid, analysis in llm_res.items():
		paper = papers_copies.get(str(pmid))
		if not paper:
			continue
		paper.summary = analysis.get("summary", "")
		paper.relevance_score = max(0.0, min(1.0, float(analysis.get("relevance_score", 0.0))))
		paper.relevance_explanation = analysis.get("relevance_explanation", "")
	return sorted(papers_copies.values(), key=lambda p: p.relevance_score, reverse=True)


def run_similarity_search(query, papers, n_of_papers):
	logger.info("Running similarity search...")
	docs = [Document(page_content=p.abstract, metadata={"pmid": p.pmid}) for p in papers]
	vectorstore = FAISS.from_documents(docs, _embeddings)
	results = vectorstore.similarity_search_with_relevance_scores(query, k=n_of_papers)
	return results


def update_keywords_and_sim_query_if_missing(user):
	if not user.get("pubmed_keywords"):
		logger.info(f"user id {user['id']} doesn't have pubmed_keywords and vector_query values in the db. Creating them and updating db.")
		query_data = adapt_queries_with_llm(user["query"])
		db.update_user_interests(user["email"], None, None, None, None, query_data)
		user["pubmed_keywords"] = query_data["pubmed_keywords"]
		user["vector_query"] = query_data["vector_query"]


def get_papers_on_pubmed(user, journal_names, last_month, papers_cache, fetched_paper_ids, pub_types):
	logger.info("Fetching PubMed IDs with keywords...")
	papers_ids_with_keywords = set(pubmed.get_ids(journal_names, user["pubmed_keywords"], pub_types, last_month))
	# if fetch with keywords gives no ids fetch without keywords
	if not papers_ids_with_keywords:
		logger.info(f"Not enough papers found with keywords for user id {user['id']}, fetching without keywords")
		paper_ids = set(pubmed.get_ids(journal_names, None, pub_types, last_month))
	else:
		paper_ids = papers_ids_with_keywords
	# Find which papers we've already fetched
	new_ids = paper_ids - fetched_paper_ids
	# Fetch only new papers from PubMed
	if new_ids:
		logger.info(f"Fetching abstracts for {len(new_ids)} IDs...")
		new_papers = pubmed.get_all_papers(list(new_ids))
		for paper in new_papers:
			papers_cache[paper.pmid] = paper
		fetched_paper_ids.update(new_ids)
	return [papers_cache[pid] for pid in paper_ids if pid in papers_cache]


def run_pipeline(user, last_month, papers_cache, fetched_paper_ids, pub_types, subject):
	logger.info(f"Processing user id {user['id']}")

	journals_names = db.get_journal_names_using_pmid(user["journals"])

	update_keywords_and_sim_query_if_missing(user)

	# --- PubMed search ---
	papers = get_papers_on_pubmed(user, journals_names, last_month, papers_cache, fetched_paper_ids, pub_types)

	# --- FAISS similarity search ---
	sim_search_res = run_similarity_search(user["vector_query"], papers, user["num_papers"])
	papers_by_pmid = {p.pmid: p for p in papers}
	sim_papers = [
		papers_by_pmid[doc.metadata["pmid"]]
		for doc, _ in sim_search_res
		if doc.metadata.get("pmid") in papers_by_pmid
	]
	# sim_scores = [round(float(score), 4) for _, score in sim_search_res]

	# --- LLM analysis ---
	llm_papers = analyze_papers(sim_papers, user["query"])
	# llm_scores = [round(p.relevance_score, 4) for p in llm_papers]

	email_body = {
		"Description": user["query"],
		"Journals": journals_names,
		"N of papers": user["num_papers"],
		"Date": last_month,
		"Pub types": pub_types
	}
	send_email(user["email"], subject, email_body, llm_papers)
