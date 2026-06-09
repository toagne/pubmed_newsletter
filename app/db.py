import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logger = logging.getLogger(__name__)

def add_user(email):
	"""Add a new user query to the database."""
	try:
		supabase.table("users").insert({
			"email": email,
			"receive_email": False
		}).execute()
	except Exception as e:
		logger.error(f"DB error in add_user for {email}: {e}")
		raise

def update_user_interests(email, query, journals, num_papers, receive_email, query_data):
	"""Update the query and interests for an existing user in the database."""
	updates = {}
	if query is not None:
		updates["query"] = query
	if journals is not None:
		updates["journals"] = journals
	if num_papers is not None:
		updates["num_papers"] = num_papers
	if receive_email is not None:
		updates["receive_email"] = receive_email
	if query_data is not None:
		updates["pubmed_keywords"] = query_data["pubmed_keywords"]
		updates["vector_query"] = query_data["vector_query"]
	if not updates:
		return
	try:
		supabase.table("users").update(updates).eq("email", email).execute()
	except Exception as e:
		logger.error(f"DB error in update_user_interests for {email}: {e}")
		raise

def get_user(email):
	"""Fetch a user from the database based on the email."""
	try:
		res = supabase.table("users").select("*").eq("email", email).execute()
	except Exception as e:
		logger.error(f"DB error in get_user for {email}: {e}")
		raise
	user = res.data
	if not user:
		return None
	return user[0]

def get_all_users():
	try:
		res = supabase.table("users").select("*").order("id").execute()
	except Exception as e:
		logger.error(f"DB error in get_all_users: {e}")
		raise
	users = res.data
	if not users:
		return []
	return users

def get_journals_pmids():
	"""Fetch all journal PMIDs from the database and return them as a list."""
	all_pmids = []
	batch_size = 1000
	start = 0
	while True:
		end = start + batch_size - 1
		try:
			res = (
				supabase
				.table("journals")
				.select("pmid")
				.range(start, end)
				.execute()
			)
		except Exception as e:
			logger.error(f"DB error in get_journals_pmids at offset {start}: {e}")
			raise
		rows = res.data
		if not rows:
			break
		all_pmids.extend(row["pmid"] for row in rows)
		if len(rows) < batch_size:
			break
		start += batch_size
	return all_pmids

def add_journals(info):
	"""Add new journals to the database."""
	try:
		supabase.table("journals").upsert(info).execute()
	except Exception as e:
		logger.error(f"DB error in add_journals: {e}")
		raise

def get_all_journals():
	"""Fetch all journals from the database and return them as a list."""
	all_journals = []
	batch_size = 1000
	start = 0
	while True:
		end = start + batch_size - 1
		try:
			res = (
				supabase
				.table("journals")
				.select("*")
				.order("name")
				.range(start, end)
				.execute()
			)
		except Exception as e:
			logger.error(f"DB error in get_all_journals at offset {start}: {e}")
			raise
		batch = res.data
		if not batch:
			break
		all_journals.extend(batch)
		if len(batch) < batch_size:
			break
		start += batch_size
	return all_journals

def get_journal_names_using_pmid(pmids):
	if not pmids:
		return []
	try:
		res = supabase.table("journals").select("name").in_("pmid", pmids).execute()
	except Exception as e:
		logger.error(f"DB error in get_journal_names_using_pmid: {e}")
		raise
	rows = res.data
	return [row["name"] for row in rows]

def add_feedback(feedback):
	try:
		supabase.table("feedbacks").insert(feedback).execute()
	except Exception as e:
		logger.error(f"DB error in add_feedback: {e}")
		raise
