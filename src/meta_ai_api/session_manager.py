"""
Session and cookie management for Meta AI API.
"""

from typing import Dict, Optional

import requests
from requests_html import HTMLSession

try:
    from .utils import extract_value, get_fb_session
except ImportError:
    from utils import extract_value, get_fb_session


class SessionManager:
    """Manages HTTP sessions and cookies for Meta AI API."""

    def __init__(
        self,
        fb_email: Optional[str] = None,
        fb_password: Optional[str] = None,
        proxy: Optional[Dict] = None,
        user_agent: str = None,
    ):
        """
        Initialize the session manager.

        Args:
            fb_email: Facebook email for authentication
            fb_password: Facebook password for authentication
            proxy: Proxy configuration
            user_agent: User agent string to use
        """
        self.fb_email = fb_email
        self.fb_password = fb_password
        self.proxy = proxy
        self.is_authenticated = fb_password is not None and fb_email is not None

        # Initialize session
        self.session = requests.Session()
        if user_agent:
            self.session.headers.update({"user-agent": user_agent})
        if proxy:
            self.session.proxies = proxy

        # Get cookies
        self.cookies = self._get_cookies()

    def _get_cookies(self) -> Dict[str, str]:
        """
        Extracts necessary cookies from the Meta AI main page.

        Returns:
            dict: A dictionary containing essential cookies.
        """
        session = HTMLSession()
        headers = {}

        # If authenticated, get Facebook session first
        if self.is_authenticated:
            fb_session = get_fb_session(self.fb_email, self.fb_password, self.proxy)
            headers = {"cookie": f"abra_sess={fb_session['abra_sess']}"}

        response = session.get("https://www.meta.ai/", headers=headers)

        cookies = {
            "_js_datr": extract_value(
                response.text, start_str='_js_datr":{"value":"', end_str='",'
            ),
            "datr": extract_value(
                response.text, start_str='datr":{"value":"', end_str='",'
            ),
            "lsd": extract_value(
                response.text, start_str='"LSD",[],{"token":"', end_str='"}'
            ),
            "fb_dtsg": extract_value(
                response.text, start_str='DTSGInitData",[],{"token":"', end_str='"'
            ),
        }

        if self.is_authenticated:
            cookies["abra_sess"] = fb_session["abra_sess"]
        else:
            cookies["abra_csrf"] = extract_value(
                response.text, start_str='abra_csrf":{"value":"', end_str='",'
            )

        return cookies

    def create_authenticated_session(self) -> requests.Session:
        """
        Create a new session for authenticated requests.
        This helps avoid cookie leakage.

        Returns:
            A new requests session configured for authenticated use.
        """
        new_session = requests.Session()
        new_session.proxies = self.proxy
        return new_session

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get headers for authenticated requests.

        Returns:
            Dictionary of headers for authenticated requests.
        """
        if self.is_authenticated:
            return {"cookie": f'abra_sess={self.cookies["abra_sess"]}'}
        return {}

    def refresh_cookies(self) -> None:
        """Refresh the cookies by re-fetching them."""
        self.cookies = self._get_cookies()