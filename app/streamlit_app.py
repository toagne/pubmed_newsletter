import streamlit as st
from app import db
import random
from app.emailer import send_email
import time

def generate_number():
	"""Generate a random 6-digit number as a string."""
	return str(random.randint(100000, 999999))

def send_verification_email(to_email, number):
	"""Send verification code to the user's email to check if the email is valid."""
	send_email(to_email, "Your Verification Code", f"Your verification code is: {number}")

def show_instructions():
	st.markdown("""
Keeping up with scientific literature is difficult. Thousands of papers are published every month across journals, preprint servers, and research communities. This tool helps you discover the articles most relevant to your work — automatically.

**How It Works**
- *Create your profile*  
Tell us about your research interests, background, current projects, and topics you care about.
- *Select your journals and sources*  
Choose the journals, conferences, or article sources you want us to monitor.
- *Monthly AI-powered filtering*  
Each month, the system collects newly published articles from your selected sources and evaluates how relevant they are to your profile.
- *Receive your personalized research digest*  
You’ll receive an email containing:
  - The top 100 most relevant papers
  - A relevance score for each article
  - A short AI-generated summary
  - Direct links to the original publications

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
		col1, col2 = st.columns(2)
		with col1:
			submit_button = st.form_submit_button(label='✅ Submit', use_container_width=True)
		with col2:
			if st.form_submit_button(label='↩️ Back', use_container_width=True):
				st.session_state.enter_email = False
				st.rerun()
		if submit_button:
			if email:
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
	journals_join_split = "***"
	st.markdown("### Edit Your Research Interests")
	with st.form(key='edit_research_interests_form'):
		db_email, db_query, temp_db_journals, db_n_of_papers =db.get_user(st.session_state.pending_email)[1:]
		db_journals = temp_db_journals.split(journals_join_split)
		st.text(db_email)
		u_query = st.text_area("💬 Your Query", value=db_query if db_query else None, placeholder="Describe your query here..." if not db_query else None, )
		all_journals = db.get_all_journals()
		u_journals = st.multiselect("Journals", all_journals, filter_mode="contains", default=db_journals if db_journals else None)
		u_n_of_papers = st.slider("Number of papers to receive each month", min_value=10, max_value=100, value=db_n_of_papers if db_n_of_papers else 20, step=10)
		if u_query == db_query:
			u_query = None
		if u_journals == db_journals:
			u_journals = None
		if u_n_of_papers == db_n_of_papers:
			u_n_of_papers = None

		col1, col2 = st.columns(2)
		with col1:
			submit_button = st.form_submit_button(label='✅ Submit', use_container_width=True)
		with col2:
			if st.form_submit_button(label='↩️ Back', use_container_width=True):
				if not db_journals or not db_query:
					missing_values_for_new_user = True
				else:
					st.session_state.edit_research_interests = False
					st.rerun()
		if missing_values_for_new_user:
			st.error("❌ You are a new user so for the first time you need to set the missing values")

		if submit_button:
			if len(u_journals) >= 1 and u_query:
				db.update_user_interests(
					journals_join_split=journals_join_split,
					email=db_email,
					query=u_query if u_query else None,
					journals=u_journals if u_journals else None,
					num_papers=u_n_of_papers if u_n_of_papers else None,
				)
				st.session_state.form_submitted = True
				st.session_state.edit_research_interests = False
				missing_values_for_new_user = False
				st.success("🎉 Your query has been submitted successfully!")
				time.sleep(2)
				st.rerun()
			if not u_query:
				st.error("❌ You need to to enter a query")
			if len(u_journals) < 1:
				st.error("❌ You need to select at least one Journal")

def show_verification():
	st.info("✉️ A verification code has been sent to your email. Please check your inbox.")
	st.markdown("### Verify your email")
	c1, c2, c3 = st.columns(3)
	with c1:
		verification_input = st.text_input("🔐 Enter the verification code", placeholder="000000")
	
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