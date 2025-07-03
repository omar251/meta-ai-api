"""
Message processing and response handling for Meta AI API.
"""

import json
import logging
import time
import urllib.parse
import uuid
from typing import Dict, Generator, Iterator, Optional, Union

import requests

try:
    from .config import (
        META_AI_API_URL,
        META_AI_GRAPH_URL,
        DOC_ID_SEND_MESSAGE,
        DEFAULT_ICEBREAKER_TYPE,
        DEFAULT_ENTRYPOINT,
        MAX_RETRIES,
        RETRY_DELAY,
    )
    from .utils import generate_offline_threading_id, format_response
except ImportError:
    from config import (
        META_AI_API_URL,
        META_AI_GRAPH_URL,
        DOC_ID_SEND_MESSAGE,
        DEFAULT_ICEBREAKER_TYPE,
        DEFAULT_ENTRYPOINT,
        MAX_RETRIES,
        RETRY_DELAY,
    )
    from utils import generate_offline_threading_id, format_response


class MessageProcessor:
    """Handles message sending and response processing."""

    def __init__(
        self,
        session: requests.Session,
        auth_manager,
        source_fetcher,
        media_extractor,
    ):
        """
        Initialize the message processor.

        Args:
            session: HTTP session for requests
            auth_manager: Authentication manager instance
            source_fetcher: Source fetcher instance
            media_extractor: Media extractor instance
        """
        self.session = session
        self.auth_manager = auth_manager
        self.source_fetcher = source_fetcher
        self.media_extractor = media_extractor

        self.external_conversation_id: Optional[str] = None
        self.offline_threading_id: Optional[str] = None

    def send_message(
        self,
        message: str,
        stream: bool = False,
        new_conversation: bool = False,
        attempts: int = 0,
    ) -> Union[Dict, Generator[Dict, None, None]]:
        """
        Sends a message to the Meta AI and returns the response.

        Args:
            message: The message to send
            stream: Whether to stream the response
            new_conversation: Whether to start a new conversation
            attempts: Current retry attempt number

        Returns:
            Response dictionary or generator for streaming responses

        Raises:
            Exception: If unable to obtain a valid response after retries
        """
        # Determine URL and auth payload based on authentication status
        is_authenticated = 'abra_sess' in self.auth_manager.cookies
        
        if is_authenticated:
            url = META_AI_API_URL
            auth_payload = self.auth_manager.get_auth_payload(True)
        else:
            url = META_AI_GRAPH_URL
            auth_payload = self.auth_manager.get_auth_payload(False)

        # Handle conversation ID
        if not self.external_conversation_id or new_conversation:
            self.external_conversation_id = str(uuid.uuid4())

        # Build request payload
        payload = self._build_message_payload(message, auth_payload)
        headers = self._build_message_headers(is_authenticated)

        # Handle session for authenticated users
        if is_authenticated:
            # Create new session to avoid cookie leakage
            self.session = requests.Session()
            if hasattr(self.auth_manager, 'session') and self.auth_manager.session.proxies:
                self.session.proxies = self.auth_manager.session.proxies

        # Send request
        response = self.session.post(url, headers=headers, data=payload, stream=stream)

        if stream:
            return self._handle_streaming_response(response, message, attempts)
        else:
            return self._handle_regular_response(response, message, attempts)

    def _build_message_payload(self, message: str, auth_payload: Dict) -> str:
        """Build the payload for sending a message."""
        payload = {
            **auth_payload,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "useAbraSendMessageMutation",
            "variables": json.dumps({
                "message": {"sensitive_string_value": message},
                "externalConversationId": self.external_conversation_id,
                "offlineThreadingId": generate_offline_threading_id(),
                "suggestedPromptIndex": None,
                "flashVideoRecapInput": {"images": []},
                "flashPreviewInput": None,
                "promptPrefix": None,
                "entrypoint": DEFAULT_ENTRYPOINT,
                "icebreaker_type": DEFAULT_ICEBREAKER_TYPE,
                "__relay_internal__pv__AbraDebugDevOnlyrelayprovider": False,
                "__relay_internal__pv__WebPixelRatiorelayprovider": 1,
            }),
            "server_timestamps": "true",
            "doc_id": DOC_ID_SEND_MESSAGE,
        }
        return urllib.parse.urlencode(payload)

    def _build_message_headers(self, is_authenticated: bool) -> Dict[str, str]:
        """Build headers for message requests."""
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "x-fb-friendly-name": "useAbraSendMessageMutation",
        }
        
        if is_authenticated:
            headers["cookie"] = f'abra_sess={self.auth_manager.cookies["abra_sess"]}'
        
        return headers

    def _handle_regular_response(self, response: requests.Response, message: str, attempts: int) -> Dict:
        """Handle non-streaming response."""
        raw_response = response.text
        last_streamed_response = self._extract_last_response(raw_response)
        
        if not last_streamed_response:
            return self._retry_message(message, stream=False, attempts=attempts)

        return self._extract_data(last_streamed_response)

    def _handle_streaming_response(
        self, 
        response: requests.Response, 
        message: str, 
        attempts: int
    ) -> Generator[Dict, None, None]:
        """Handle streaming response."""
        lines = response.iter_lines()
        
        try:
            first_line = next(lines)
            is_error = json.loads(first_line)
            if len(is_error.get("errors", [])) > 0:
                return self._retry_message(message, stream=True, attempts=attempts)
        except (StopIteration, json.JSONDecodeError):
            return self._retry_message(message, stream=True, attempts=attempts)

        return self._stream_response(lines)

    def _extract_last_response(self, response: str) -> Optional[Dict]:
        """Extract the last complete response from the API response."""
        last_streamed_response = None
        
        for line in response.split("\n"):
            if not line.strip():
                continue
                
            try:
                json_line = json.loads(line)
            except json.JSONDecodeError:
                continue

            bot_response_message = (
                json_line.get("data", {})
                .get("node", {})
                .get("bot_response_message", {})
            )
            
            # Update conversation IDs
            chat_id = bot_response_message.get("id")
            if chat_id and "_" in chat_id:
                parts = chat_id.split("_")
                if len(parts) >= 2:
                    self.external_conversation_id = parts[0]
                    self.offline_threading_id = parts[1]

            # Check if this is the final response
            streaming_state = bot_response_message.get("streaming_state")
            if streaming_state == "OVERALL_DONE":
                last_streamed_response = json_line

        return last_streamed_response

    def _stream_response(self, lines: Iterator[str]) -> Generator[Dict, None, None]:
        """Stream response data as it arrives."""
        for line in lines:
            if not line:
                continue
                
            try:
                json_line = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            extracted_data = self._extract_data(json_line)
            if extracted_data.get("message"):
                yield extracted_data

    def _extract_data(self, json_line: Dict) -> Dict:
        """Extract message, sources, and media from a JSON response."""
        bot_response_message = (
            json_line.get("data", {})
            .get("node", {})
            .get("bot_response_message", {})
        )
        
        # Extract message text
        message = format_response(response=json_line)
        
        # Extract sources
        fetch_id = bot_response_message.get("fetch_id")
        sources = self.source_fetcher.fetch_sources(fetch_id) if fetch_id else []
        
        # Extract media
        media = self.media_extractor.extract_media(bot_response_message)
        
        return {
            "message": message,
            "sources": sources,
            "media": media
        }

    def _retry_message(self, message: str, stream: bool = False, attempts: int = 0):
        """Retry sending a message if an error occurs."""
        if attempts < MAX_RETRIES:
            logging.warning(
                f"Unable to obtain valid response from Meta AI. "
                f"Retrying... Attempt {attempts + 1}/{MAX_RETRIES + 1}."
            )
            time.sleep(RETRY_DELAY)
            return self.send_message(message, stream=stream, attempts=attempts + 1)
        else:
            raise Exception(
                "Unable to obtain a valid response from Meta AI. Try again later."
            )

    def start_new_conversation(self) -> None:
        """Start a new conversation by resetting conversation IDs."""
        self.external_conversation_id = None
        self.offline_threading_id = None