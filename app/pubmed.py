from app.utils import fetch_xml, logger, chunk_list, Paper, format_journals
from app import db
import time

# get ids of articles with given keywords and date
def get_ids(journals, keywords, last_month) -> list[str | None]:
	"""Fetch PubMed IDs based on a complex query that includes keywords, journal filters, and publication date.
	Returns a list of PubMed IDs as strings, or an empty list if the fetch or parsing fails.
	Note: The query is currently hardcoded to search for recent articles related to tumors, cancer, or bioinformatics in specific high-impact journals. This can be modified to accept dynamic input in the future."""
	search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
	keywords_str = " OR ".join(keywords)
	journals_str = format_journals(journals)
	search_params = {
		"db": "pubmed", #database
		"term": f"""{keywords_str} AND
			(
				"Journal Article"[pt] OR
				"Meta-Analysis"[pt] OR
				"Preprint"[pt] OR
				"Review"[pt] OR
				"Systematic Review"[pt]
			) AND
			(
				{journals_str}
			)""",
		"mindate": last_month,
		"maxdate": last_month,
		"datetype": "pdat", #pubblication date
		"sort": "relevance", #sort by relevance
		"retmax": 1000, #number of results - to keep it manageable for testing, can be increased later
	}
	root = fetch_xml(search_url, search_params)
	if root is None:
		logger.error("Failed to fetch PubMed IDs.")
		return []
	return [id.text for id in root.findall(".//Id") if id.text]

# get journal, title and abstract of articles with given ids
def get_all_papers(ids):
	"""Fetch journal, title, and abstract information for a list of PubMed IDs.
	Returns a list of dictionaries with keys 'JOURNAL', 'TITLE', and 'ABSTRACT'.
	Handles fetch and parse errors gracefully, skipping batches that fail."""
	info = []
	for batch in chunk_list(ids, 100, get_all_papers.__name__):
		if not batch:
			continue
		ids_str = ",".join(batch)
		fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
		fetch_params = {
			"db": "pubmed",
			"id": ids_str,
			"retmode": "xml"
		}
		root = fetch_xml(fetch_url, fetch_params)
		if root is None:
			logger.error(f"Skipping batch due to fetch/parse failure: {ids_str}")
			continue
		for article in root.findall(".//PubmedArticle"):

			# abstract
			abstract_elem = article.findall(".//AbstractText")
			if abstract_elem:
				abstract = " ".join(" ".join("".join(abstract_part.itertext()).split()) for abstract_part in abstract_elem)
				if len(abstract.split(" ")) < 100: # skip papers with very short abstracts
					continue
			else:
				continue # skip papers with no abstract

			# journal
			journal = article.findtext(".//Title") or "Unknown Journal"

			# title
			title_elem = article.findall(".//ArticleTitle")
			if title_elem:
				title = " ".join(" ".join("".join(title_part.itertext()).split()) for title_part in title_elem)
			else:
				title = ""

			# pmid
			pmid=article.findtext(".//PMID") or "Unknown PMID"

			# doi
			doi=article.findtext(".//ArticleId[@IdType='doi']") or "Unknown doi"

			# journal_type
			journal_type=article.findtext(".//PublicationType") or "Unknown Journal type"

			# date
			year = article.findtext(".//PubDate//Year") or ""
			month = article.findtext(".//PubDate//Month") or ""
			day = article.findtext(".//PubDate//Day") or ""
			publication_date = " ".join([year, month, day])

			# authors
			authors_list = []
			for author in article.find(".//AuthorList"):
				forename = author.findtext(".//ForeName", "")
				lastname = author.findtext(".//LastName", "")
				if forename or lastname:
					authors_list.append(f"{forename} {lastname}".strip())
			authors = ", ".join(authors_list)

			info.append(Paper(
				pmid=pmid,
				doi=doi,
				journal=journal,
				journal_type=journal_type,
				publication_date=publication_date,
				title=title,
				authors=authors,
				abstract=abstract
			))
		time.sleep(0.5) # to avoid hitting rate limits
	return info

def get_journals_id():
	search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
	search_params = {
		"db": "nlmcatalog",
		"term": "(currentlyindexed OR journalspmc) AND eng[la]",
		"retmax": 10000,
	}
	root = fetch_xml(search_url, search_params)
	if root is None:
		logger.error("Failed to fetch journal IDs.")
		return []
	return [id.text for id in root.findall(".//Id") if id.text]

def look_for_journals_not_in_db():
	db_journals = set(db.get_journal_pmids())
	api_journals = set(get_journals_id())
	new_journals = api_journals - db_journals
	return list(new_journals)

def get_journals_info():
	for batch in chunk_list(look_for_journals_not_in_db(), 100, get_journals_info.__name__):
		if not batch:
			continue
		info = []
		ids_str = ",".join(batch)
		fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
		fetch_params = {
			"db": "nlmcatalog",
			"id": ids_str,
			"retmode": "xml"
		}
		root = fetch_xml(fetch_url, fetch_params)
		if root is None:
			logger.error(f"Skipping batch due to fetch/parse failure: {ids_str}")
			continue
		for i, journal in enumerate(root.findall(".//NLMCatalogRecord")):
			info.append((journal.findtext(".//Title") or "Unknown Journal", batch[i]))
		db.add_journals(info)
		time.sleep(0.5) # to avoid hitting rate limits

# I am a cancer researcher focusing on tumor evolution using genomic and transcriptomics data
# I am a cancer researcher focusing on epigenetic and dna methylation

# 			"Nature"[journal] OR
# 			"Nature Medicine"[journal] OR
# 			"Nature Cancer"[journal] OR
# 			"Nature Communications"[journal] OR
# 			"Nature Genetics"[journal] OR
# 			"Nature Reviews Cancer"[journal] OR
# 			"Nature Reviews Genetics"[journal] OR
# 			"Cell"[journal] OR
# 			"Cancer Cell"[journal] OR
# 			"Cell Genomics"[journal] OR
# 			"Cell Reports Medicine"[journal] OR
# 			"Bioinformatics"[journal] OR
# 			"Cancer Discovery"[journal] OR
# 			"Cancer Research"[journal] OR
# 			"Genome Medicine"[journal] OR
# 			"Molecular Cancer Research"[journal] OR
# 			"Science"[journal] OR
# 			"Science Advances"[journal]