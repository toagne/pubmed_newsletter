import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def add_user(email):
	"""Add a new user query to the database."""
	supabase.table("users").insert({
		"email": email,
		"receive_email": True
	}).execute()

def update_user_interests(email, query, journals, num_papers, receive_email):
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
	if not updates:
		return
	supabase.table("users").update(updates).eq("email", email).execute()

def get_user(email):
	"""Fetch a user from the database based on the email."""
	res = supabase.table("users").select("*").eq("email", email).execute()
	user = res.data
	if not user:
		return None
	return user[0]

def get_all_users():
	res = supabase.table("users").select("*").execute()
	users = res.data
	if not users:
		return None
	return users

def get_journals_pmids():
	"""Fetch all journal PMIDs from the database and return them as a list."""
	all_pmids = []
	batch_size = 1000
	start = 0
	while True:
		end = start + batch_size - 1
		res = (
			supabase
			.table("journals")
			.select("pmid")
			.range(start, end)
			.execute()
		)
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
	supabase.table("journals").insert(info).execute()

def get_all_journals():
	"""Fetch all journals from the database and return them as a list."""
	all_journals = []
	batch_size = 1000
	start = 0
	while True:
		end = start + batch_size - 1
		res = (
			supabase
			.table("journals")
			.select("*")
			.order("name")
			.range(start, end)
			.execute()
		)
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
	res = supabase.table("journals").select("name").in_("pmid", pmids).execute()
	rows = res.data
	return [row["name"] for row in rows]