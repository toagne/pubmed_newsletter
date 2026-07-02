import unittest
from contextlib import nullcontext
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils import fetch_xml, chunk_list, Paper
from app.pubmed import get_ids, get_all_papers
import app.streamlit_app as streamlit_app

class TestMain(unittest.TestCase):

	@patch('app.utils.requests.get')
	def test_fetch_xml_success(self, mock_get):
		"""Test successful XML fetch and parsing."""
		mock_response = MagicMock()
		mock_response.text = '<root><data>test</data></root>'
		mock_get.return_value = mock_response

		result = fetch_xml('http://example.com', {'param': 'value'})
		self.assertIsNotNone(result)
		self.assertEqual(result.findtext('.//data'), 'test')

	@patch('app.utils.requests.get')
	def test_fetch_xml_http_error(self, mock_get):
		"""Test fetch_xml handles HTTP errors."""
		from requests.exceptions import RequestException
		mock_get.side_effect = RequestException("HTTP Error")
		result = fetch_xml('http://example.com', {})
		self.assertIsNone(result)

	@patch('app.utils.requests.get')
	def test_fetch_xml_parse_error(self, mock_get):
		"""Test fetch_xml handles XML parse errors."""
		mock_response = MagicMock()
		mock_response.text = 'invalid xml'
		mock_get.return_value = mock_response

		result = fetch_xml('http://example.com', {})
		self.assertIsNone(result)

	@patch('app.pubmed.fetch_xml')
	def test_get_ids_success(self, mock_fetch):
		"""Test get_ids with mocked XML response."""
		mock_root = MagicMock()
		mock_root.findtext.return_value = '50'
		mock_id1 = MagicMock()
		mock_id1.text = '12345'
		mock_id2 = MagicMock()
		mock_id2.text = '67890'
		mock_root.findall.return_value = [mock_id1, mock_id2]
		mock_fetch.return_value = mock_root

		result = get_ids(None, None, None, None)
		self.assertEqual(result, ['12345', '67890'])

	@patch('app.pubmed.fetch_xml')
	def test_get_ids_failure(self, mock_fetch):
		"""Test get_ids handles fetch failure."""
		mock_fetch.return_value = None
		result = get_ids(None, None, None, None)
		self.assertEqual(result, [])

	def test_chunk_list(self):
		"""Test chunk_list function."""
		data = [1, 2, 3, 4, 5]
		chunks = list(chunk_list(data, 2, "", verbose=False))
		self.assertEqual(chunks, [[1, 2], [3, 4], [5]])

	@patch('app.streamlit_app.db.update_user_interests')
	@patch('app.streamlit_app.db.get_user')
	@patch('app.streamlit_app.adapt_queries_with_llm')
	def test_submit_description_persists_updated_query_to_db(self, mock_adapt, mock_get_user, mock_update_user_interests):
		"""Ensure a new description is stored immediately when the user submits it."""
		mock_get_user.return_value = {"query": None}
		mock_adapt.return_value = {
			"is_valid_research_query": True,
			"pubmed_keywords": ["cancer"],
			"vector_query": "cancer research"
		}
		mock_session_state = {}
		with patch.object(streamlit_app.st, "session_state", mock_session_state), \
			 patch.object(streamlit_app.st, "spinner", return_value=nullcontext()), \
			 patch.object(streamlit_app, "go_to") as mock_go_to:
			mock_session_state["pending_email"] = "user@example.com"
			mock_session_state["u_query"] = "Updated research description for cancer genomics and transcriptomics"
			streamlit_app.submit_description()
		self.assertEqual(mock_session_state["u_query"], "Updated research description for cancer genomics and transcriptomics")
		mock_update_user_interests.assert_called_once_with(
			"user@example.com",
			"Updated research description for cancer genomics and transcriptomics",
			None,
			None,
			None,
			mock_adapt.return_value,
		)
		mock_go_to.assert_called_once_with("edit_interests")

	def test_paper_dataclass(self):
		"""Test Paper dataclass creation."""
		paper = Paper(
			pmid='123',
			doi='456',
			journal='Nature',
			journal_type='Journal Article',
			publication_date='2026 Apr 02',
			title='Test Title',
			authors='Author1, Author2',
			abstract='Test Abstract'
		)
		self.assertEqual(paper.pmid, '123')
		self.assertEqual(paper.doi, '456')
		self.assertEqual(paper.journal, 'Nature')
		self.assertEqual(paper.journal, 'Nature')
		self.assertEqual(paper.title, 'Test Title')
		self.assertEqual(paper.abstract, 'Test Abstract')

	@patch('app.pubmed.chunk_list')
	@patch('app.pubmed.get_ids')
	@patch('app.pubmed.fetch_xml')
	def test_get_articles_info(self, mock_fetch, mock_get_ids, mock_chunk):
		"""Test get_articles_info with mocked dependencies."""
		# Mock get_ids to return some IDs
		mock_get_ids.return_value = ['12345']

		# Mock chunk_list to return the batch
		mock_chunk.return_value = [['12345']]

		# Mock XML response for article fetch
		mock_root = MagicMock()
		mock_article = MagicMock()
		mock_article.findtext.side_effect = lambda path: {
			'.//Title': 'Nature',
			'.//PMID': '12345'
		}.get(path, '')
		mock_article.findall.side_effect = lambda path: {
			'.//ArticleTitle': [MagicMock()],
			'.//AbstractText': [MagicMock()]
		}.get(path, [])
		mock_root.findall.return_value = [mock_article]
		mock_fetch.return_value = mock_root

		# Mock itertext for title and abstract
		mock_title_part = MagicMock()
		mock_title_part.itertext.return_value = ['Test', 'Title']
		mock_abstract_part = MagicMock()
		mock_abstract_part.itertext.return_value = ['word '] * 120

		mock_article.findall.side_effect = lambda path: {
			'.//ArticleTitle': [mock_title_part],
			'.//AbstractText': [mock_abstract_part]
		}.get(path, [])

		result = get_all_papers(None)
		self.assertEqual(len(result), 1)
		self.assertIsInstance(result[0], Paper)
		self.assertEqual(result[0].pmid, '12345')

if __name__ == '__main__':
	unittest.main()