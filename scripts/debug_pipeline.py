"""
Debug script: runs the full pipeline for a user without sending emails.

Usage:
    python scripts/debug_pipeline.py <email>

Output:
    - JSON summary printed to stdout
    - JSON file saved to data/debug_YYYY-MM-DD_<email>.json
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import db, pubmed
from app import pipeline
from app.utils import get_last_month, logger

PUB_TYPES = ["Journal Article", "Meta-Analysis", "Preprint", "Review", "Systematic Review"]

# def multiple_similarity_search(papers_list, n_of_papers):
#     queries = [
#         "Ovarian cancer chemotherapy resistance mechanisms and tumor evolution.",
#         "Genomic and transcriptomic analysis of treatment failure in ovarian neoplasms.",
#         "Molecular pathways driving therapeutic resistance in gynecologic cancers."
#     ]
#     all_results = {}
#     for query in queries:
#         results = pipeline.run_similarity_search(query, papers_list, n_of_papers)
#         for doc, score in results:
#             pmid = doc.metadata["pmid"]
#             if pmid not in all_results:
#                 all_results[pmid] = []
#             all_results[pmid].append(score)
#     final_scores = {pmid: max(scores) for pmid, scores in all_results.items()}
#     return sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:n_of_papers]

def run_debug(email: str) -> dict:
    user = db.get_user(email)
    if not user:
        raise ValueError(f"User not found: {email}")
    if not user.get("query") or not user.get("journals"):
        raise ValueError(f"User {email} is missing query or journals")
    if not user.get("num_papers"):
        raise ValueError(f"User {email} is missing num_papers")

    last_month = get_last_month()
    num_papers = user["num_papers"]
    journals_names = db.get_journal_names_using_pmid(user["journals"])

    pipeline.update_keywords_and_sim_query_if_missing(user)

    # --- PubMed search ---
    logger.info("Fetching PubMed IDs with keywords...")
    ids_with_keywords = set(pubmed.get_ids(journals_names, user["pubmed_keywords"], PUB_TYPES, last_month))
    target_ratio = 3
    used_keywords = len(ids_with_keywords) >= num_papers * target_ratio

    if not used_keywords:
        logger.info("Not enough papers with keywords, retrying without keywords...")
        paper_ids = set(pubmed.get_ids(journals_names, None, PUB_TYPES, last_month))
    else:
        paper_ids = ids_with_keywords

    logger.info(f"Fetching abstracts for {len(paper_ids)} IDs...")
    papers_list = pubmed.get_all_papers(list(paper_ids))
    paper_by_pmid = {p.pmid: p for p in papers_list}

    # --- FAISS similarity search ---
    sim_results = pipeline.run_similarity_search(user["vector_query"], papers_list, user["num_papers"] * 2)
    sim_papers = [
        paper_by_pmid[doc.metadata["pmid"]]
        for doc, _ in sim_results
        if doc.metadata.get("pmid") in paper_by_pmid
    ]
    sim_scores = [round(float(score), 4) for _, score in sim_results]
    sim_titles = [paper_by_pmid[doc.metadata["pmid"]].title for doc, _ in sim_results[:10] if doc.metadata.get("pmid") in paper_by_pmid]
    # multiple_sim_res = multiple_similarity_search(papers_list, user["num_papers"])
    # multiple_sim_scores = [round(float(score), 4) for _, score in multiple_sim_res]
    # multiple_sim_titles = [paper_by_pmid[pmid].title for pmid, _ in multiple_sim_res[:10] if pmid in paper_by_pmid]

    # --- LLM analysis ---
    # analyzed_papers = pipeline.analyze_papers(sim_papers, user["query"])[:user["num_papers"]]
    # llm_scores = [round(p.relevance_score, 4) for p in analyzed_papers]
    # llm_titles = [p.title for p in analyzed_papers[:10]]

    return {
        "user_id": user["id"],
        "user_query": user["query"],
        "pubmed": {
            "pubmed_keywords": user["pubmed_keywords"],
            "used_keywords": used_keywords,
            "papers_found_with_keywords": len(ids_with_keywords),
            "journals": journals_names,
            "papers_found": len(papers_list),
            "papers_required": num_papers,
            "ratio": round(len(papers_list) / num_papers, 2),
        },
        "similarity_search": {
            "similarity_search_query": user["vector_query"],
            "max_score": max(sim_scores) if sim_scores else 0,
            "min_score": min(sim_scores) if sim_scores else 0,
            "average_score": round(sum(sim_scores) / len(sim_scores), 4) if sim_scores else 0,
            "top_10_scores": sim_scores[:10],
            "top_10_titles": sim_titles,
        },
        # "multiple_similarity_search": {
        #     "max_score": max(multiple_sim_scores) if multiple_sim_scores else 0,
        #     "min_score": min(multiple_sim_scores) if multiple_sim_scores else 0,
        #     "average_score": round(sum(multiple_sim_scores) / len(multiple_sim_scores), 4) if multiple_sim_scores else 0,
        #     "top_10_scores": multiple_sim_scores[:10],
        #     "top_10_titles": multiple_sim_titles,
        # },
        # "llm": {
        #     "max_score": max(llm_scores) if llm_scores else 0,
        #     "min_score": min(llm_scores) if llm_scores else 0,
        #     "average_score": round(sum(llm_scores) / len(llm_scores), 4) if llm_scores else 0,
        #     "top_10_scores": llm_scores[:10],
        #     "top_10_titles": llm_titles,
        # },
    }


def main():
    parser = argparse.ArgumentParser(description="Debug pipeline for a user without sending emails.")
    parser.add_argument("email", help="User email address")
    args = parser.parse_args()

    try:
        result = run_debug(args.email)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output = json.dumps(result, indent=2, ensure_ascii=False)
    # print(output)

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    safe_email = args.email.replace("@", "_at_").replace(".", "_")
    filename = f"debug_{date.today().isoformat()}_{safe_email}.json"
    output_path = output_dir / filename
    output_path.write_text(output, encoding="utf-8")
    print(f"\nSaved to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
