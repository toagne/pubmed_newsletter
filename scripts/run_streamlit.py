import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from app.db import init_db
from app.streamlit_app import show_instructions, handle_enter_email, handle_edit_research_interests, show_verification

def main():
	st.set_page_config(page_title="Query Submission", layout="centered")
	st.title("Stay Current With the Research That Matters to You")

	# Initialize the database
	init_db()

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