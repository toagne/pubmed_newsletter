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
from app.utils import adapt_queries_with_llm

def generate_number():
	"""Generate a random 6-digit number as a string."""
	return str(random.randint(100000, 999999))

def send_verification_email(to_email, number):
	"""Send verification code to the user's email to check if the email is valid."""
	send_email(to_email, "Your Verification Code", f"Your verification code is: {number}", None)

@st.cache_data(ttl=604800) # 7 days
def cached_journals():
	return db.get_all_journals()

def go_to(page):
	st.session_state["page"] = page

def back_to_home():
	keys_to_reset = [
		"pending_email",
		"verification_number",
		"email_error",
		"query_error",
		"journals_error",
		"verification_code_error",
		"is_feedback",
		"feedback_error",
		"query_data",
		"show_journal_dialog",
		"update_journals",
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
		"verification_code_error": None,
		"is_feedback": None,
		"feedback_error": None,
		"query_data": None,
		"show_journal_dialog": None,
		"update_journals": None,
	}
	for key, value in defaults.items():
		if key not in st.session_state:
			st.session_state[key] = value

# HOME
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
	col1, col2 = st.columns(2)
	with col1:
		st.button("Start", on_click=go_to, args=["enter_email"], use_container_width=True)
	with col2:
		st.button("Feedback", on_click=go_to, args=["feedback"], use_container_width=True)

# EMAIL
def submit_email():
	email = st.session_state.get("email", "").strip().lower()
	email_valid = bool(email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
	if not email_valid:
		st.session_state["email_error"] = "❌ Please enter a valid email address."
		return
	user = db.get_user(email)
	if user:
		st.session_state["pending_email"] = email
		if st.session_state["page"] == "feedback":
			st.session_state["is_feedback"] = True
		elif user.get("query"):
			go_to("user_profile")
		else:
			go_to("edit_description")
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
		st.button("❌", on_click=back_to_home, use_container_width=True)
	with st.form(key='new_user_form'):
		st.text_input("📧 Email", placeholder="your.email@example.com", key="email")
		if st.session_state["email_error"]:
			st.error(st.session_state["email_error"])
		col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
		with col2:
			st.form_submit_button(label='✅ Submit', on_click=submit_email, use_container_width=True)

# USER RESEARCH INTERESTS
def submit_interests():
	st.session_state["journals_error"] = None
	u_journals = st.session_state.get("u_journals")
	if not u_journals:
		st.session_state["journals_error"] = "❌ You need to select at least one Journal"
		return
	db_user = db.get_user(st.session_state["pending_email"])
	u_query = st.session_state.get("u_query")
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
	db.update_user_interests(
		db_user["email"],
		u_query,
		u_journals,
		u_n_of_papers,
		u_receive_email,
		st.session_state["query_data"]
	)
	st.toast("🎉 Your research interests has been submitted successfully!")
	go_to("user_profile")

def handle_edit_research_interests():
	db_user = db.get_user(st.session_state["pending_email"])
	journals = cached_journals()
	journals_dict = {j["pmid"]: j["name"] for j in journals}
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Edit Your Research Interests")
	with col_btn:
		st.button("❌", on_click=back_to_home, use_container_width=True)
	with st.form(key='edit_research_interests_form'):
		st.text_input("Email", value=db_user["email"], disabled=True)
		if not st.session_state.get("u_query"):
			st.session_state["u_query"] = db_user.get("query")
		st.text_area(
			label="Research Description",
			value=st.session_state.get("u_query") or "",
			disabled=True,
		)
		st.caption("Email and research description are locked here. To update your research description, use the dedicated edit description flow from your profile page.")
		if st.session_state["update_journals"]:
			st.info("The automatic journal update feature is not available yet. Your journal selection is the same as before.")
			default_journals = db_user.get("journals", []) # change this
		else:
			default_journals = db_user.get("journals", [])
		st.multiselect(
			label="Journals",
			options=list(journals_dict.keys()),
			default=default_journals,
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

# VERIFICATION CODE
def verify_code():
	input_code = st.session_state.get("verification_input", "").strip()
	if input_code == st.session_state["verification_number"]:
		if st.session_state["verification_code_error"]:
			st.session_state["verification_code_error"] = None
		db.add_user(st.session_state["pending_email"])
		st.toast("✅ Email verified successfully!")
		go_to("edit_description")
	else:
		st.session_state["verification_code_error"] = "❌ Invalid verification code. Please try again."

def show_verification():
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Verify your email")
	with col_btn:
		st.button("❌", on_click=back_to_home, use_container_width=True)
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

# FEEDBACK
def validate_feedback(feedback):
	feedback = feedback.strip() if feedback else None
	if not feedback:
		return False, "❌ You need to to enter a feedback"
	if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b', feedback, re.IGNORECASE):
		return False, "❌ Feedback contains potentially harmful SQL-like keywords. Please enter a valid Feedback."
	return True, None

def submit_feedback():
	st.session_state["feedback_error"] = None
	db_user = db.get_user(st.session_state["pending_email"])
	feedback_text = st.session_state["u_feedback"]
	ok, error = validate_feedback(feedback_text)
	if not ok:
		st.session_state["feedback_error"] = error
		return
	feedback = {
		"user_id": db_user["id"],
		"feedback": feedback_text
	}
	db.add_feedback(feedback)
	st.toast("✅ Feedback submitted successfully!")
	back_to_home()

def handle_feedback():
	if not st.session_state["is_feedback"]:
		handle_enter_email()
	else:
		col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
		with col_title:
			st.markdown("### Feedback for the literature update you received")
		with col_btn:
			st.button("❌", on_click=back_to_home, use_container_width=True)
		with st.form(key='feedback'):
			st.text_area(label="Your feedback", key="u_feedback")
			if st.session_state["feedback_error"]:
				st.error(st.session_state["feedback_error"])
			col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
			with col2:
				st.form_submit_button(
					label='✅ Submit Feedback',
					on_click=submit_feedback,
					use_container_width=True
				)

# UPDATE JOURNALS
@st.dialog("Update Journals Recommendations", width="medium")
def journals_update_dialog():
	st.write("Would you like to update your journal selection based on your new research description?")
	col1, col2 = st.columns(2)
	with col1:
		if st.button("Yes, show me the recommendations"):
			st.session_state["show_journal_dialog"] = False
			st.session_state["update_journals"] = True
			go_to("edit_interests")
			st.rerun()
	with col2:
		if st.button("No, keep my current selection"):
			st.session_state["show_journal_dialog"] = False
			st.session_state["update_journals"] = False
			go_to("edit_interests")
			st.rerun()

# USER DESCRIPTION
def validate_query(u_query):
	u_query = u_query.strip() if u_query else None
	if not u_query:
		return False, "❌ You need to to enter a description"
	if not re.match(r'^(?=.*[A-Za-z0-9])[A-Za-z0-9() .,:]+$', u_query):
		return False, "❌ You need to to enter a valid description, only alphanumeric and ().,: characters are allowed"
	if len(u_query.split(" ")) < 5:
		return False, "❌ Please enter a longer description"
	if len(u_query) > 1000:
		return False, "❌ Description is too long. Please limit to 1000 characters."
	if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b', u_query, re.IGNORECASE):
		return False, "❌ Description contains potentially harmful SQL-like keywords. Please enter a valid research description."
	if detect(u_query) != "en":
		return False, "❌ Please use English"
	return True, None

def submit_description():
	st.session_state["query_error"] = None
	u_query = st.session_state.get("u_query")
	ok, error = validate_query(u_query)
	if not ok:
		st.session_state["query_error"] = error
		return
	with st.spinner("Analyzing your description...", show_time=True):
		try:
			query_data = adapt_queries_with_llm(u_query)
		except Exception:
			st.session_state["query_error"] = "❌ Failed to analyze your description. Please try again."
			return
	if query_data.get("is_valid_research_query") == False:
		st.session_state["query_error"] = query_data.get("explanation")
		return
	st.session_state["query_error"] = None
	st.session_state["query_data"] = query_data
	if db.get_user(st.session_state["pending_email"]).get("query"):
		st.session_state["show_journal_dialog"] = True
	else:
		go_to("edit_interests")

def handle_edit_description():
	db_user = db.get_user(st.session_state["pending_email"])
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Edit Your Research Description")
	with col_btn:
		st.button("❌", on_click=back_to_home, use_container_width=True)
	with st.form(key='edit_research_description_form'):
		st.text_input("Email", value=db_user["email"], disabled=True)
		value = db_user.get("query") if db_user.get("query") else None
		placeholder = ("Describe your research subjects and interests here...\nExample: I am a cancer researcher focusing on tumor evolution using genomic and transcriptomics data"
			if not db_user["query"]
			else None)
		st.text_area(
			label="💬 Research Description",
			value=value,
			key="u_query",
			placeholder=placeholder
		)
		if st.session_state["query_error"]:
			st.error(st.session_state["query_error"])
		col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
		with col2:
			st.form_submit_button(
				label='✅ Save your description',
				on_click=submit_description,
				use_container_width=True
			)
	if st.session_state.get("show_journal_dialog"):
		journals_update_dialog()

# USER PROFILE
def handle_user_profile():
	db_user = db.get_user(st.session_state["pending_email"])
	col_title, col_btn = st.columns([0.9, 0.1], vertical_alignment="center")
	with col_title:
		st.markdown("### Your Profile")
	with col_btn:
		st.button("❌", on_click=back_to_home, use_container_width=True)
	st.markdown("<hr style='margin: 0rem 0;'>", unsafe_allow_html=True)
	st.markdown("##### Profile Summary")
	col1, col2, col3 = st.columns([.5, .25, .25], border=True,)
	col1.markdown("**Email**")
	col1.text(db_user.get("email", "—"))
	col2.markdown("**Papers / month**")
	col2.write(str(db_user.get("num_papers", "—")))
	col3.markdown("**Email updates**")
	col3.write("Yes" if db_user.get("receive_email") else "No")
	st.markdown("<hr style='margin: 0rem 0;'>", unsafe_allow_html=True)
	st.markdown("##### Research Description")
	if db_user.get("query"):
		st.info(db_user["query"])
	else:
		st.warning("No research description provided yet.")
	c1, c2, c3 = st.columns([.25, .5, .25])
	with c2:
		st.button("Edit research description", on_click=go_to, args=["edit_description"], use_container_width=True)
	journals = db.get_journal_names_using_pmid(db_user.get("journals", []))
	st.markdown("<hr style='margin: 0rem 0;'>", unsafe_allow_html=True)
	st.markdown("##### Selected Journals")
	if journals:
		row_cols = st.columns(3)
		for index, journal_name in enumerate(journals):
			col = row_cols[index % len(row_cols)]
			col.markdown(f"- {journal_name}")
	else:
		st.warning("No journals selected yet.")
	st.divider()
	c1, c2, c3 = st.columns([.25, .5, .25])
	with c2:
		st.button("Edit journals & preferences", on_click=go_to, args=["edit_interests"], use_container_width=True)

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
	elif st.session_state["page"] == "edit_description":
		handle_edit_description()
	elif st.session_state["page"] == "edit_interests":
		handle_edit_research_interests()
	elif st.session_state["page"] == "feedback":
		handle_feedback()
	elif st.session_state["page"] == "user_profile":
		handle_user_profile()

if __name__ == "__main__":
	main()