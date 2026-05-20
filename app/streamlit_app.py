import streamlit as st
import random
import time
import re
from langdetect import detect
import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import db
from app.emailer import send_email

def generate_number():
	"""Generate a random 6-digit number as a string."""
	return str(random.randint(100000, 999999))

def send_verification_email(to_email, number):
	"""Send verification code to the user's email to check if the email is valid."""
	send_email(to_email, "Your Verification Code", f"Your verification code is: {number}")

@st.cache_data(ttl=604800) # 7 days
def cached_journals():
	return db.get_all_journals()

def go_to(page):
	st.session_state["page"] = page

def exit():
	keys_to_reset = [
		"pending_email",
		"verification_number",
		"email_error",
		"query_error",
		"journals_error",
		"verification_code_error"
	]
	for key in keys_to_reset:
		st.session_state[key] = None
	go_to("home")

def init_sessions_state():
	defaults = {
		"page": "home",
		"pending_email": None,
		"verification_number": None,
		"email_error": None,
		"query_error": None,
		"journals_error": None,
		"verification_code_error": None
	}
	for key, value in defaults.items():
		if key not in st.session_state:
			st.session_state[key] = value

def show_instructions():
	st.markdown("""
Keeping up with scientific literature is difficult. Thousands of papers are published every month across journals, preprint servers, and research communities. This tool helps you discover the articles most relevant to your work — automatically.

**How It Works**
- *Create your profile*  
Tell us about your research interests, background, current projects, and topics you care about.
- *Select your journals*  
Choose the journals you want us to monitor and the number of articles you want to receive.
- *Monthly AI-powered filtering*  
Each month, the system collects newly published articles from your selected sources and evaluates how relevant they are to your profile.
- *Receive your personalized research digest*  
You’ll receive an email containing:
  - The most relevant papers details
  - A relevance score for each article
  - A short AI-generated summary

The goal is simple: help you spend less time searching and more time reading the papers that actually matter to your work.
""")
	col1, col2, col3 = st.columns(3)
	with col2:
		st.button("Start", on_click=go_to, args=["enter_email"], use_container_width=True)

def submit_email():
	email = st.session_state.get("email", "").strip().lower()
	email_valid = bool(email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
	if not email_valid:
		st.session_state["email_error"] = "❌ Please enter a valid email address."
		return
	if db.get_user(email):
		st.session_state["pending_email"] = email
		go_to("edit_interests")
	else:
		number = generate_number()
		send_verification_email(email, number)
		st.session_state["verification_number"] = number
		st.session_state["pending_email"] = email
		go_to("verification")

def handle_enter_email():
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Enter your email below")
	with col_btn:
		st.button("❌", on_click=exit, use_container_width=True)
	with st.form(key='new_user_form'):
		st.text_input("📧 Email", placeholder="your.email@example.com", key="email")
		if st.session_state["email_error"]:
			st.error(st.session_state["email_error"])
		col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
		with col2:
			st.form_submit_button(label='✅ Submit', on_click=submit_email, use_container_width=True)

def validate_query(u_query):
	u_query = u_query.strip() if u_query else None
	if not u_query:
		return False, "❌ You need to to enter a query"
	if not re.match(r'^(?=.*[A-Za-z0-9])[A-Za-z0-9() .,:]+$', u_query):
		return False, "❌ You need to to enter a valid query, only alphanumeric and ().,: characters are allowed"
	if len(u_query.split(" ")) < 5:
		return False, "❌ Please enter a longer query"
	if len(u_query) > 1000:
		return False, "❌ Query is too long. Please limit to 1000 characters."
	if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b', u_query, re.IGNORECASE):
		return False, "❌ Query contains potentially harmful SQL-like keywords. Please enter a valid research query."
	if detect(u_query) != "en":
		return False, "❌ Please use English"
	return True, None

def submit_interests():
	u_query = st.session_state.get("u_query")
	ok, error = validate_query(u_query)
	u_journals = st.session_state.get("u_journals")
	if not ok or not u_journals:
		if not ok:
			st.session_state["query_error"] = error
		if not u_journals:
			st.session_state["journals_error"] = "❌ You need to select at least one Journal"
		return
	db_user = db.get_user(st.session_state["pending_email"])
	u_n_of_papers = st.session_state.get("u_n_of_papers")
	u_receive_email = st.session_state.get("u_receive_email")
	if u_query == db_user["query"]:
		u_query = None
	if u_journals == db_user["journals"]:
		u_journals = None
	if u_n_of_papers == db_user["num_papers"]:
		u_n_of_papers = None
	if u_receive_email == db_user["receive_email"]:
		u_receive_email = None
	db.update_user_interests(db_user["email"], u_query, u_journals, u_n_of_papers, u_receive_email)
	st.toast("🎉 Your research interests has been submitted successfully!")
	exit()

def handle_edit_research_interests():
	db_user = db.get_user(st.session_state["pending_email"])
	journals = cached_journals()
	journals_dict = {j["pmid"]: j["name"] for j in journals}
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Edit Your Research Interests")
	with col_btn:
		st.button("❌", on_click=exit, use_container_width=True)
	with st.form(key='edit_research_interests_form'):
		st.text(db_user["email"])
		st.text_area(
			label="💬 Research Description",
			value=db_user["query"] if db_user["query"] else None,
			key="u_query",
			placeholder="Describe your research subjects and interests here...\nExample: I am a cancer researcher focusing on tumor evolution using genomic and transcriptomics data" if not db_user["query"] else None
		)
		if st.session_state["query_error"]:
			st.error(st.session_state["query_error"])
		st.multiselect(
			label="Journals",
			options=list(journals_dict.keys()),
			default=db_user["journals"],
			format_func=lambda x: journals_dict[x],
			key="u_journals",
			filter_mode="contains",
			max_selections=50
		)
		if st.session_state["journals_error"]:
			st.error(st.session_state["journals_error"])
		st.slider(
			label="Number of papers to receive each month",
			min_value=10,
			max_value=100,
			value=db_user["num_papers"] if db_user["num_papers"] else 20,
			step=10,
			key="u_n_of_papers"
		)
		st.toggle(
			label="Receive_email",
			value=db_user["receive_email"],
			key="u_receive_email"
		)
		col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
		with col2:
			st.form_submit_button(
				label='✅ Save Preferences',
				on_click=submit_interests,
				use_container_width=True
			)

def verify_code():
	input_code = st.session_state.get("verification_input", "").strip()
	if input_code == st.session_state["verification_number"]:
		if st.session_state["verification_code_error"]:
			st.session_state["verification_code_error"] = None
		db.add_user(st.session_state["pending_email"])
		st.toast("✅ Email verified successfully!")
		go_to("edit_interests")
	else:
		st.session_state["verification_code_error"] = "❌ Invalid verification code. Please try again."

def show_verification():
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Verify your email")
	with col_btn:
		st.button("❌", on_click=exit, use_container_width=True)
	st.info("✉️ A verification code has been sent to your email. Please check your inbox.")
	with st.form("verification form"):
		c1, c2, c3 = st.columns(3)
		with c1:
			st.text_input("🔐 Enter the verification code", placeholder="000000", key="verification_input")
		if st.session_state["verification_code_error"]:
				st.error(st.session_state["verification_code_error"])
		col1, col2 = st.columns(2)
		with col1:
			st.form_submit_button("✅ Verify", on_click=verify_code, use_container_width=True)

def main():
	init_sessions_state()

	st.set_page_config(page_title="Research Newsletter", layout="centered")
	st.title("Your breaking news from the scientific world")

	if st.session_state["page"] == "home":
		show_instructions()
	elif st.session_state["page"] == "enter_email":
		handle_enter_email()
	elif st.session_state["page"] == "verification":
		show_verification()
	elif st.session_state["page"] == "edit_interests":
		handle_edit_research_interests()

if __name__ == "__main__":
	main()