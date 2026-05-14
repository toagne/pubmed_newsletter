import requests
from requests.exceptions import RequestException
import xml.etree.ElementTree as ET
import logging
import math
from dataclasses import dataclass
from datetime import timedelta, date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Paper:
	pmid: str
	doi: str
	journal: str
	journal_type: str
	publication_date: str
	title: str
	authors: str
	abstract: str
	summary: str = ""
	relevance_score = 0
	relevance_explanation = ""

# helper function to fetch and parse XML from a URL
def fetch_xml(url, params):
	"""Fetch XML from a URL and return the parsed ElementTree root.
	Return None on failure."""
	try:
		response = requests.get(url, params=params, timeout=15)
		response.raise_for_status()
	except RequestException as exc:
		logger.error(f"HTTP request failed for {url}: {exc}")
		return None
	try:
		return ET.fromstring(response.text)
	except ET.ParseError as exc:
		logger.error(f"XML parse error for {url}: {exc}")
		return None

# split list into batches
def chunk_list(data, size, verbose=True):
	"""Yield successive batches of a list with progress indication."""
	n = 1
	tot = math.ceil(len(data) / size)
	for i in range(0, len(data), size):
		if verbose:
			logger.info(f"Processing batch {n}/{tot}")
		n+=1
		yield data[i:i + size]
	print()

# format the batch of articles and the query into a string to be sent to the agent
def format_batch(papers, query):
	"""Format a batch of papers and a user query into a structured string for agent processing.
	Returns a string that includes the user query followed by a numbered list of papers with their journal, title, and abstract.
	The format is designed to be clear and consistent for the agent to analyze effectively."""
	text = f"User query:\n{query}\n\nPapers:\n"
	for i, p in enumerate(papers, 1):
		text += f"""
Paper {i}
PMID: {p.pmid}
Abstract: {p.abstract}
--------------------
"""
	text += "Return the result strictly as valid JSON as specified."
	return text

def format_email(papers):
	text = ""
	for i, p in enumerate(papers, 1):
		text += f"""
Paper {i}
PMID: {p.pmid}
Journal: {p.journal}
Title: {p.title}
Abstract: {p.abstract}
--------------------
"""
	return text

def format_journals(journals):
	text = ""
	for journal in journals.split("***"):
		text += f'"{journal}"[journal] OR '
	return text.strip(" OR ")

def get_last_month():
	today = date.today()
	last_month = today - (timedelta(days=today.day + 1))
	return f"{last_month.year}/{last_month.month if last_month.month > 9 else f"0{last_month.month}"}"