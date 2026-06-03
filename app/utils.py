import requests
from requests.exceptions import RequestException
import xml.etree.ElementTree as ET
import logging
import math
from dataclasses import dataclass
from datetime import timedelta, date
from app import llm
import json

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
def chunk_list(data, size, caller_function, verbose=True):
	"""Yield successive batches of a list with progress indication."""
	n = 1
	tot = math.ceil(len(data) / size)
	for i in range(0, len(data), size):
		if verbose:
			logger.info(f"{caller_function} - Processing batch {n}/{tot}")
		n+=1
		yield data[i:i + size]
	print()

# format the batch of articles and the query into a string to be sent to the agent
def format_batch(papers, query):
	res = {}
	res["query"] = query
	res["papers"] = {str(p.pmid): p.abstract for p in papers}
	return res

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

def format_params(data, data_type=""):
	if not data:
		return ""
	data = [f'"{d}"' for d in data]
	data_str = f"{data_type} OR ".join(data)
	data_str += data_type
	return data_str

def get_last_month():
	today = date.today()
	first_day_this_month = today.replace(day=1)
	last_day_previous_month = first_day_this_month - timedelta(days=1)
	return f"{last_day_previous_month.year}/{last_day_previous_month.month:02d}"

def adapt_queries_with_llm(query):
	response = llm.analyze_with_llm(llm.USER_QUERY_ANALYSIS_PROMPT, query)
	query_data = json.loads(response)
	return query_data