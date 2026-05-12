from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import json

from app.utils import chunk_list, format_batch, format_email, logger, Paper
from app.llm import analyze_with_llm

# analyze the papers with the agent and return the results as a list of dictionaries
def analyze_papers(papers, query, batch_size=10):
	"""Analyze a list of papers using an agent, processing them in batches.
	Returns a list of dictionaries containing the analysis results for all papers.
	The function formats each batch of papers with the user query, sends it to the agent, and collects the results. It handles JSON parsing errors gracefully, skipping batches that fail to produce valid JSON output."""
	all_results = []
	for batch in chunk_list(papers, batch_size):
		content = format_batch(batch, query)
		response = analyze_with_llm(content)
		try:
			batch_result = json.loads(response)
			all_results.extend(batch_result)
		except json.JSONDecodeError:
			logger.error("Skipping batch due to json error")
			continue
	return all_results

def get_best_papers(query, papers, n_of_papers):
	docs = [Document(page_content=f"{p.abstract}", metadata={"pmid": p.pmid, "journal": p.journal, "title": p.title}) for p in papers]
	embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
	vectorstore = FAISS.from_documents(docs, embeddings)
	results = vectorstore.similarity_search(query, k=n_of_papers)
	best_papers = []
	for p in results:
		best_papers.append(
			Paper
				(
					pmid=p.metadata['pmid'],
					journal=p.metadata['journal'],
					title=p.metadata['title'],
					abstract=p.page_content
				)
			)
	return best_papers

def run_pipeline(query, papers, n_of_papers):
	best_papers_with_faiss = get_best_papers(query, papers, n_of_papers)
	return best_papers_with_faiss
	# best_papers_with_llm = analyze_papers(best_papers_with_faiss, query)
	# return format_email(best_papers_with_faiss)
	# return format_email(best_papers_with_llm)