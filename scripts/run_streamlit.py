import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from app.db import init_db
from app.streamlit_app import show_instructions, handle_new_user, show_verification, handle_edit_research_interests, show_success_message

def main():
	st.set_page_config(page_title="Query Submission", layout="centered")
	st.title("Stay Current With the Research That Matters to You")

	# Initialize the database
	init_db()

	# Initialize session states
	if 'new_user' not in st.session_state:
		st.session_state.new_user = False
	if 'edit_research_interests' not in st.session_state:
		st.session_state.edit_research_interests = False
	if 'form_submitted' not in st.session_state:
		st.session_state.form_submitted = False
	if 'verification_step' not in st.session_state:
		st.session_state.verification_step = False

	# show instructions
	if not st.session_state.new_user and not st.session_state.edit_research_interests:
		show_instructions()

	elif st.session_state.new_user and not st.session_state.verification_step:
		handle_new_user()

	# Show verification step
	elif st.session_state.new_user and st.session_state.verification_step:
		show_verification()

	elif st.session_state.edit_research_interests:
		handle_edit_research_interests()

	# Show success message
	elif st.session_state.form_submitted:
		show_success_message()

if __name__ == "__main__":
	main()