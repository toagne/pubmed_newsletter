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
		start_button = st.button("Start", use_container_width=True)
	if start_button:
		st.session_state.enter_email = True
		st.rerun()

def handle_enter_email():
	st.markdown("### Enter your email below")
	with st.form(key='new_user_form'):
		email = st.text_input("📧 Email", placeholder="your.email@example.com")
		# Sanitize email input
		email = email.strip().lower() if email else None
		email_valid = bool(email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
		if email and not email_valid:
			st.error("❌ Please enter a valid email address.")
		col1, col2 = st.columns(2)
		with col1:
			submit_button = st.form_submit_button(label='✅ Submit', use_container_width=True)
		with col2:
			if st.form_submit_button(label='↩️ Back', use_container_width=True):
				st.session_state.enter_email = False
				st.rerun()
		if submit_button:
			if email_valid:
				if db.get_user(email):
					st.session_state.enter_email = False
					st.session_state.edit_research_interests = True
					st.session_state.pending_email = email
					st.rerun()
				else:
					number = generate_number()
					send_verification_email(email, number)
					st.session_state.verification_number = number
					st.session_state.pending_email = email
					st.session_state.verification_step = True
					st.rerun()
			else:
				st.error("❌ Please enter your email.")

def handle_edit_research_interests():
	missing_values_for_new_user = False
	st.markdown("### Edit Your Research Interests")
	with st.form(key='edit_research_interests_form'):
		db_user = db.get_user(st.session_state.pending_email)
		journals = cached_journals()
		journals_dict = {j["pmid"]: j["name"] for j in journals}
		st.text(db_user["email"])
		u_query = st.text_area("💬 Research Description", value=db_user["query"] if db_user["query"] else None, placeholder="Describe your research subjects and interests here...\nExample: I am a cancer researcher focusing on tumor evolution using genomic and transcriptomics data" if not db_user["query"] else None)
		# Sanitize user input to prevent potential issues
		u_query = u_query.strip() if u_query else None
		if not u_query:
			st.error("❌ You need to to enter a query")
		elif bool(re.match(r'^(?=.*[A-Za-z0-9])[A-Za-z0-9() .,:]+$', u_query)) == False:
			st.error("❌ You need to to enter a valid query, only alphanumeric and ().,: characters are allowd")
			u_query = None
		elif len(u_query.split(" ")) < 5:
			st.error("❌ Please enter a longer query")
			u_query = None
		elif u_query and len(u_query) > 1000:  # Limit query length to 1000 characters
			st.error("❌ Query is too long. Please limit to 1000 characters.")
			u_query = None
		elif u_query and re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b', u_query, re.IGNORECASE):
			st.error("❌ Query contains potentially harmful SQL-like keywords. Please enter a valid research query.")
			u_query = None
		elif u_query and detect(u_query) != "en":
			st.error("❌ You need to use english for the query")
			u_query = None

		u_journals = st.multiselect(
			label="Journals",
			options=list(journals_dict.keys()),
			default=db_user["journals"],
			format_func=lambda x: journals_dict[x],
			filter_mode="contains",
			max_selections=50
		)
		if not u_journals:
			st.error("❌ You need to select at least one Journal")

		u_n_of_papers = st.slider("Number of papers to receive each month", min_value=10, max_value=100, value=db_user["num_papers"] if db_user["num_papers"] else 20, step=10)

		u_receive_email = st.toggle("Receive_email", db_user["receive_email"])

		col1, col2 = st.columns(2)
		with col1:
			submit_button = st.form_submit_button(label='✅ Submit', use_container_width=True)
		with col2:
			if st.form_submit_button(label='↩️ Back', use_container_width=True):
				if not db_user["journals"] or not db_user["query"]:
					missing_values_for_new_user = True
				else:
					st.session_state.edit_research_interests = False
					st.rerun()
		if missing_values_for_new_user:
			st.error("❌ You are a new user so for the first time you need to set the missing values")

		if submit_button:
			if u_journals and u_query:
				if u_query == db_user["query"]: u_query = None
				if u_journals == db_user["journals"]: u_journals = None
				if u_n_of_papers == db_user["num_papers"]: u_n_of_papers = None
				if u_receive_email == db_user["receive_email"]: u_receive_email = None
				db.update_user_interests(db_user["email"], u_query, u_journals, u_n_of_papers, u_receive_email)
				st.session_state.form_submitted = True
				st.session_state.edit_research_interests = False
				missing_values_for_new_user = False
				st.success("🎉 Your query has been submitted successfully!")
				time.sleep(2)
				st.rerun()

def show_verification():
	st.info("✉️ A verification code has been sent to your email. Please check your inbox.")
	st.markdown("### Verify your email")
	c1, c2, c3 = st.columns(3)
	with c1:
		verification_input = st.text_input("🔐 Enter the verification code", placeholder="000000")
		# Sanitize verification input
		verification_input = verification_input.strip() if verification_input else ""
	
	col1, col2 = st.columns(2)
	with col1:
		verify_button = st.button("✅ Verify", use_container_width=True)
	with col2:
		if st.button("↩️ Back", use_container_width=True):
			st.session_state.verification_step = False
			st.session_state.enter_email = False
			st.rerun()
	
	if verify_button:
		if verification_input == st.session_state.verification_number:
			db.add_user(st.session_state.pending_email)
			st.session_state.verification_step = False
			st.session_state.edit_research_interests = True
			st.session_state.enter_email = False
			st.success("✅ Email verified successfully! Now you can edit your research interests.")
			time.sleep(2)
			st.rerun()
		else:
			st.error("❌ Invalid verification code. Please try again.")

def main():
	st.set_page_config(page_title="Research Newsletter", layout="centered")
	st.title("Your breaking news from the scientific world")

	# Initialize session states
	if 'enter_email' not in st.session_state:
		st.session_state.enter_email = False
	if 'edit_research_interests' not in st.session_state:
		st.session_state.edit_research_interests = False
	if 'verification_step' not in st.session_state:
		st.session_state.verification_step = False

	# show instructions
	if not st.session_state.enter_email and not st.session_state.edit_research_interests:
		show_instructions()

	elif st.session_state.enter_email and not st.session_state.edit_research_interests and not st.session_state.verification_step:
		handle_enter_email()

	# Show verification step
	elif st.session_state.enter_email and st.session_state.verification_step:
		show_verification()

	elif st.session_state.edit_research_interests:
		handle_edit_research_interests()

if __name__ == "__main__":
	main()