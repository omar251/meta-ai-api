"""
Authentication module for Meta AI API.
Handles access token generation and Facebook authentication.
"""

import json
import time
import urllib.parse
from typing import Optional, Dict

import requests

try:
    from .config import (
        META_AI_API_URL,
        DOC_ID_ACCEPT_TOS,
        DEFAULT_DOB,
        DEFAULT_ICEBREAKER_TYPE,
        TOKEN_DELAY,
    )
    from .exceptions import FacebookRegionBlocked
except ImportError:
    from config import (
        META_AI_API_URL,
        DOC_ID_ACCEPT_TOS,
        DEFAULT_DOB,
        DEFAULT_ICEBREAKER_TYPE,
        TOKEN_DELAY,
    )
    from exceptions import FacebookRegionBlocked


class AuthenticationManager:
    """Manages authentication for Meta AI API."""

    def __init__(self, session: requests.Session, cookies: Dict[str, str]):
        """
        Initialize the authentication manager.

        Args:
            session: HTTP session to use for requests
            cookies: Dictionary of cookies required for authentication
        """
        self.session = session
        self.cookies = cookies
        self._access_token: Optional[str] = None

    def get_access_token(self) -> str:
        """
        Retrieves an access token using Meta's authentication API.

        Returns:
            str: A valid access token.

        Raises:
            FacebookRegionBlocked: If the region is blocked or response is invalid.
        """
        if self._access_token:
            return self._access_token

        payload = {
            "lsd": self.cookies["lsd"],
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "useAbraAcceptTOSForTempUserMutation",
            "variables": {
                "dob": DEFAULT_DOB,
                "icebreaker_type": DEFAULT_ICEBREAKER_TYPE,
                "__relay_internal__pv__WebPixelRatiorelayprovider": 1,
            },
            "doc_id": DOC_ID_ACCEPT_TOS,
        }

        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "cookie": self._build_cookie_header(),
            "sec-fetch-site": "same-origin",
            "x-fb-friendly-name": "useAbraAcceptTOSForTempUserMutation",
        }

        response = self.session.post(
            META_AI_API_URL,
            headers=headers,
            data=urllib.parse.urlencode(payload)
        )

        try:
            auth_json = response.json()
        except json.JSONDecodeError:
            raise FacebookRegionBlocked(
                "Unable to receive a valid response from Meta AI. This is likely due to your region being blocked. "
                "Try manually accessing https://www.meta.ai/ to confirm."
            )

        try:
            self._access_token = auth_json["data"]["xab_abra_accept_terms_of_service"][
                "new_temp_user_auth"
            ]["access_token"]
        except KeyError as e:
            raise FacebookRegionBlocked(
                f"Unexpected response structure from Meta AI API: {e}"
            )

        # API requires a brief delay after token generation
        time.sleep(TOKEN_DELAY)

        return self._access_token

    def _build_cookie_header(self) -> str:
        """Build the cookie header for authentication requests."""
        return (
            f'_js_datr={self.cookies["_js_datr"]}; '
            f'abra_csrf={self.cookies["abra_csrf"]}; '
            f'datr={self.cookies["datr"]};'
        )

    def get_auth_payload(self, is_authenticated: bool) -> Dict[str, str]:
        """
        Get the appropriate authentication payload.

        Args:
            is_authenticated: Whether the user is authenticated with Facebook

        Returns:
            Dictionary containing authentication parameters
        """
        if is_authenticated:
            return {"fb_dtsg": self.cookies["fb_dtsg"]}
        else:
            return {"access_token": self.get_access_token()}

    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token without generating a new one."""
        return self._access_token