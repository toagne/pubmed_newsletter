from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import json

from app.utils import chunk_list, format_batch, logger
from app import llm

# analyze the papers with the agent and return the results as a list of dictionaries
def analyze_papers(papers, query, batch_size=10):
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
	papers_by_pmid = {str(p.pmid): p for p in papers}
	for pmid, analysis in llm_res.items():
		paper = papers_by_pmid.get(str(pmid))
		if not paper:
			continue
		paper.summary = analysis.get("summary", "")
		paper.relevance_score = analysis.get("relevance_score", 0)
		paper.relevance_explanation = analysis.get("relevance_explanation", "")
	papers.sort(
		key=lambda p: p.relevance_score,
		reverse=True
	)
	return papers

def get_best_papers(query, papers, n_of_papers):
	paper_by_pmid = {p.pmid: p for p in papers}
	docs = [Document(page_content=p.abstract, metadata={"pmid": p.pmid}) for p in papers]
	embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
	vectorstore = FAISS.from_documents(docs, embeddings)
	results = vectorstore.similarity_search(query, k=n_of_papers)
	return [paper_by_pmid[result.metadata["pmid"]] for result in results if result.metadata.get("pmid") in paper_by_pmid]

def run_pipeline(similarity_search_query, user_query, papers, n_of_papers):
	# !! ATTENTION query for similarity search and user query are different 
	best_papers_with_similarity_search = get_best_papers(similarity_search_query, papers, n_of_papers)
	# return best_papers_with_similarity_search
	best_papers_with_llm = analyze_papers(best_papers_with_similarity_search, user_query)
	return best_papers_with_llm