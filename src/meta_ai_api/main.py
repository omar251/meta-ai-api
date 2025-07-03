"""
Legacy main module for backward compatibility.
The refactored code is in client.py, but this maintains the original interface.
"""

import warnings
from typing import Dict, List, Generator, Union

# Handle both relative and absolute imports for direct execution
try:
    from .client import MetaAI as RefactoredMetaAI
except ImportError:
    # If relative import fails (when running directly), try absolute import
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from client import MetaAI as RefactoredMetaAI


class MetaAI(RefactoredMetaAI):
    """
    Legacy MetaAI class for backward compatibility.

    This class wraps the new refactored implementation while maintaining
    the original interface. New code should use the client.MetaAI class directly.
    """

    def __init__(
        self, fb_email: str = None, fb_password: str = None, proxy: dict = None
    ):
        """
        Initialize MetaAI client (legacy interface).

        Args:
            fb_email: Facebook email for authentication
            fb_password: Facebook password for authentication
            proxy: Proxy configuration dictionary
        """
        # Issue deprecation warning for the old interface
        warnings.warn(
            "The main.MetaAI class is deprecated. Use client.MetaAI instead.",
            DeprecationWarning,
            stacklevel=2
        )

        super().__init__(fb_email=fb_email, fb_password=fb_password, proxy=proxy)

    def prompt(
        self,
        message: str,
        stream: bool = False,
        attempts: int = 0,
        new_conversation: bool = False,
    ) -> Union[Dict, Generator[Dict, None, None]]:
        """
        Legacy prompt method with attempts parameter for backward compatibility.

        Args:
            message: The message to send
            stream: Whether to stream the response
            attempts: Deprecated parameter (ignored)
            new_conversation: Whether to start a new conversation

        Returns:
            Response dictionary or generator
        """
        if attempts > 0:
            warnings.warn(
                "The 'attempts' parameter is deprecated and will be ignored. "
                "Retry logic is now handled internally.",
                DeprecationWarning,
                stacklevel=2
            )

        return super().prompt(
            message=message,
            stream=stream,
            new_conversation=new_conversation
        )

    # Legacy property accessors for backward compatibility
    @property
    def access_token(self) -> str:
        """Get access token (legacy property)."""
        return getattr(self.auth_manager, '_access_token', None)

    @property
    def is_authed(self) -> bool:
        """Check if authenticated (legacy property)."""
        return self.is_authenticated

    @property
    def external_conversation_id(self) -> str:
        """Get conversation ID (legacy property)."""
        return self.conversation_id

    @property
    def offline_threading_id(self) -> str:
        """Get offline threading ID (legacy property)."""
        return getattr(self.message_processor, 'offline_threading_id', None)

    @property
    def cookies(self) -> Dict[str, str]:
        """Get cookies (legacy property)."""
        return self.session_manager.cookies

    @property
    def session(self):
        """Get session (legacy property)."""
        return self.session_manager.session

    # Legacy methods for backward compatibility
    def get_access_token(self) -> str:
        """Get access token (legacy method)."""
        return self.auth_manager.get_access_token()

    def get_cookies(self) -> Dict[str, str]:
        """Get cookies (legacy method)."""
        return self.session_manager.cookies

    def extract_media(self, json_line: dict) -> List[Dict]:
        """Extract media (legacy static method)."""
        return self.media_extractor.extract_media(json_line)

    def fetch_sources(self, fetch_id: str) -> List[Dict]:
        """Fetch sources (legacy method)."""
        return self.source_fetcher.fetch_sources(fetch_id)


if __name__ == "__main__":
    meta = RefactoredMetaAI()
    prompt = input("Enter your prompt: ")
    resp = meta.prompt(prompt, stream=True)
    previous_message = ""
    for chunk in resp:
        new_message = chunk["message"]
        print(new_message[len(previous_message):], end="", flush=True)
        previous_message = new_message
    print()  # for a final newline
    # print(resp["message"])
