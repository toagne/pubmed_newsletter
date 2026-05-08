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
	col1, col2 = st.columns(2)
	with col1:
		new_user_button = st.button("✅ New User", use_container_width=True)
	with col2:
		change_settings_button = st.button("⚙️ Edit Research Interests", use_container_width=True)
	if new_user_button:
		st.session_state.new_user = True
		st.rerun()
	if change_settings_button:
		st.session_state.edit_research_interests = True
		st.rerun()

def handle_new_user():
	st.markdown("### Enter your email below")
	with st.form(key='new_user_form'):
		email = st.text_input("📧 Email", placeholder="your.email@example.com")
		col1, col2 = st.columns(2)
		with col1:
			submit_button = st.form_submit_button(label='✅ Submit', use_container_width=True)
		with col2:
			if st.form_submit_button(label='↩️ Back', use_container_width=True):
				st.session_state.new_user = False
				st.rerun()
		if submit_button:
			if email:
				if db.get_user(email):
					st.warning("This email is already registered. Please enter a different email.")
				else:
					number = generate_number()
					send_verification_email(email, number)
					st.session_state['verification_number'] = number
					st.session_state['pending_email'] = email
					st.session_state['verification_step'] = True
					st.rerun()
			else:
				st.error("❌ Please enter your email.")

def handle_edit_research_interests():
	st.markdown("### Edit Your Research Interests")
	with st.form(key='edit_research_interests_form'):
		email = st.text_input("📧 Email", placeholder="your.email@example.com")
		query = st.text_area("💬 Your Query", placeholder="Describe your query here...", height=150)
		all_journals = db.get_journals_name()
		journals = st.multiselect("Journals", all_journals, filter_mode="contains")
		num_papers = st.slider("Number of papers to receive each month", min_value=10, max_value=100, value=20, step=10)

		col1, col2 = st.columns(2)
		with col1:
			submit_button = st.form_submit_button(label='✅ Submit', use_container_width=True)
		with col2:
			if st.form_submit_button(label='↩️ Back', use_container_width=True):
				st.session_state.edit_research_interests = False
				st.rerun()

		if submit_button:
			if email and (query or journals or num_papers):
				# Add the user query to the database
				if db.get_user(email):
					db.update_user_interests(
						email=email,
						query=query if query else None,
						journals=journals if journals else None,
						num_papers=num_papers if num_papers else None
					)
					st.session_state.form_submitted = True
					st.session_state.edit_research_interests = False
					st.rerun()
				else:
					st.warning("This email is not registered. Please enter a registered email.")
			else:
				st.error("❌ Please fill in at least your email and one of the other fields.")

def show_verification():
	st.info("✉️ A verification code has been sent to your email. Please check your inbox.")
	st.markdown("### Verify your email")
	verification_input = st.text_input("🔐 Enter the verification code", placeholder="000000")
	
	col1, col2 = st.columns(2)
	with col1:
		verify_button = st.button("✅ Verify", use_container_width=True)
	with col2:
		if st.button("↩️ Back", use_container_width=True):
			st.session_state.verification_step = False
			st.session_state.new_user = False
			st.rerun()
	
	if verify_button:
		if verification_input == st.session_state['verification_number']:
			db.add_user(st.session_state['pending_email'], "")
			st.session_state.verification_step = False
			st.session_state.edit_research_interests = True
			st.session_state.new_user = False
			st.success("✅ Email verified successfully! Now you can edit your research interests.")
			time.sleep(2)
			st.rerun()
		else:
			st.error("❌ Invalid verification code. Please try again.")

def show_success_message():
	st.success("🎉 Your query has been submitted successfully!")
	st.markdown("""
	---
	### What's next?
	We've received your query and will get back to you shortly.
	Check your email for further updates.
	""")
	
	if st.button("📝 Submit Another Query"):
		st.session_state.form_submitted = False
		st.rerun()