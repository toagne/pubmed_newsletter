import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH")

def init_db():
	"""Initialize the SQLite database and create the users table if it doesn't exist."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			email TEXT UNIQUE NOT NULL,
			query TEXT,
			journals TEXT,
			num_papers INTEGER,
			receive_email BOOL
		)
	""")
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS journals (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			pmid TEXT UNIQUE NOT NULL
		)
	""")
	conn.commit()
	conn.close()

def add_user(email):
	"""Add a new user query to the database."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO users (email, receive_email) VALUES (?, ?)", (email, True))
	conn.commit()
	conn.close()

def update_user_interests(journals_join_split, email, query, journals, num_papers, receive_email):
	"""Update the query and interests for an existing user in the database."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	updates = []
	params = []
	if query:
		updates.append("query = ?")
		params.append(query)
	if journals:
		updates.append("journals = ?")
		params.append(journals_join_split.join(journals))
	if num_papers:
		updates.append("num_papers = ?")
		params.append(num_papers)
	updates.append("receive_email = ?")
	params.append(receive_email)
	params.append(email)
	update_query = f"UPDATE users SET {', '.join(updates)} WHERE email = ?"
	cursor.execute(update_query, tuple(params))
	conn.commit()
	conn.close()

def get_user(email):
	"""Fetch a user query from the database based on the email."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
	user = cursor.fetchone()
	conn.close()
	return user

def get_all_users():
	"""Fetch all user queries from the database and return them as a list of tuples (email, query)."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM users")
	users = cursor.fetchall()
	conn.close()
	return users

def get_journal_pmids():
	"""Fetch all journal PMIDs from the database and return them as a list."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute("SELECT pmid FROM journals")
	pmids = [row[0] for row in cursor.fetchall()]
	conn.close()
	return pmids

def add_journals(info):
	"""Add new journals to the database."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.executemany("INSERT INTO journals (name, pmid) VALUES (?, ?)", info)
	conn.commit()
	conn.close()

def get_all_journals():
	"""Fetch all journal names from the database and return them as a list."""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute("SELECT name FROM journals ORDER BY name")
	names = [row[0] for row in cursor.fetchall()]
	conn.close()
	return names