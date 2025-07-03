"""
Source fetching utilities for Meta AI API.
"""

import json
import urllib.parse
from typing import Dict, List, Optional

import requests

try:
    from .config import META_AI_GRAPH_URL, DOC_ID_SEARCH_PLUGIN
except ImportError:
    from config import META_AI_GRAPH_URL, DOC_ID_SEARCH_PLUGIN


class SourceFetcher:
    """Handles fetching of sources/references from Meta AI API."""

    def __init__(self, session: requests.Session, auth_manager, cookies: Dict[str, str]):
        """
        Initialize the source fetcher.

        Args:
            session: HTTP session for requests
            auth_manager: Authentication manager instance
            cookies: Dictionary of cookies
        """
        self.session = session
        self.auth_manager = auth_manager
        self.cookies = cookies

    def fetch_sources(self, fetch_id: str) -> List[Dict]:
        """
        Fetch sources from the Meta AI API based on the given fetch ID.

        Args:
            fetch_id: The fetch ID to use for the query

        Returns:
            List of dictionaries containing the fetched sources
        """
        if not fetch_id:
            return []

        # Only fetch sources if we have an access token
        if not hasattr(self.auth_manager, 'access_token') or not self.auth_manager.access_token:
            return []

        payload = {
            "access_token": self.auth_manager.access_token,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "AbraSearchPluginDialogQuery",
            "variables": json.dumps({"abraMessageFetchID": fetch_id}),
            "server_timestamps": "true",
            "doc_id": DOC_ID_SEARCH_PLUGIN,
        }

        headers = {
            "authority": "graph.meta.ai",
            "accept-language": "en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7",
            "content-type": "application/x-www-form-urlencoded",
            "cookie": self._build_cookie_header(),
            "x-fb-friendly-name": "AbraSearchPluginDialogQuery",
        }

        try:
            response = self.session.post(
                META_AI_GRAPH_URL,
                headers=headers,
                data=urllib.parse.urlencode(payload)
            )
            response.raise_for_status()
            
            response_json = response.json()
            return self._extract_references(response_json)
            
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            # Log the error but don't fail the entire request
            import logging
            logging.warning(f"Failed to fetch sources: {e}")
            return []

    def _build_cookie_header(self) -> str:
        """Build the cookie header for source requests."""
        return (
            f'dpr=2; '
            f'abra_csrf={self.cookies.get("abra_csrf", "")}; '
            f'datr={self.cookies.get("datr", "")}; '
            f'ps_n=1; ps_l=1'
        )

    def _extract_references(self, response_json: Dict) -> List[Dict]:
        """
        Extract references from the API response.

        Args:
            response_json: The JSON response from the API

        Returns:
            List of reference dictionaries
        """
        try:
            message = response_json.get("data", {}).get("message", {})
            if not message:
                return []

            search_results = message.get("searchResults")
            if not search_results:
                return []

            references = search_results.get("references", [])
            return references if isinstance(references, list) else []
            
        except (KeyError, TypeError):
            return []

    def fetch_sources_safe(self, fetch_id: Optional[str]) -> List[Dict]:
        """
        Safely fetch sources, returning empty list on any error.

        Args:
            fetch_id: The fetch ID to use for the query

        Returns:
            List of dictionaries containing the fetched sources, or empty list on error
        """
        try:
            return self.fetch_sources(fetch_id) if fetch_id else []
        except Exception:
            return []