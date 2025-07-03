"""
Main client class for Meta AI API.
This is the refactored version with improved separation of concerns.
"""

from typing import Dict, Generator, Optional, Union

# Handle both relative and absolute imports for direct execution
try:
    from .auth import AuthenticationManager
    from .config import DEFAULT_USER_AGENT
    from .media_extractor import MediaExtractor
    from .message_processor import MessageProcessor
    from .session_manager import SessionManager
    from .source_fetcher import SourceFetcher
except ImportError:
    from auth import AuthenticationManager
    from config import DEFAULT_USER_AGENT
    from media_extractor import MediaExtractor
    from message_processor import MessageProcessor
    from session_manager import SessionManager
    from source_fetcher import SourceFetcher


class MetaAI:
    """
    A client for interacting with the Meta AI API.
    
    This class provides a clean interface for sending messages to Meta AI
    and receiving responses, with support for both authenticated and
    unauthenticated access.
    """

    def __init__(
        self,
        fb_email: Optional[str] = None,
        fb_password: Optional[str] = None,
        proxy: Optional[Dict] = None,
    ):
        """
        Initialize the Meta AI client.

        Args:
            fb_email: Facebook email for authenticated access (optional)
            fb_password: Facebook password for authenticated access (optional)
            proxy: Proxy configuration dictionary (optional)
        """
        # Initialize session manager
        self.session_manager = SessionManager(
            fb_email=fb_email,
            fb_password=fb_password,
            proxy=proxy,
            user_agent=DEFAULT_USER_AGENT,
        )

        # Initialize authentication manager
        self.auth_manager = AuthenticationManager(
            session=self.session_manager.session,
            cookies=self.session_manager.cookies,
        )

        # Initialize media extractor
        self.media_extractor = MediaExtractor()

        # Initialize source fetcher
        self.source_fetcher = SourceFetcher(
            session=self.session_manager.session,
            auth_manager=self.auth_manager,
            cookies=self.session_manager.cookies,
        )

        # Initialize message processor
        self.message_processor = MessageProcessor(
            session=self.session_manager.session,
            auth_manager=self.auth_manager,
            source_fetcher=self.source_fetcher,
            media_extractor=self.media_extractor,
        )

    def prompt(
        self,
        message: str,
        stream: bool = False,
        new_conversation: bool = False,
    ) -> Union[Dict, Generator[Dict, None, None]]:
        """
        Send a message to Meta AI and get a response.

        Args:
            message: The message to send to Meta AI
            stream: Whether to stream the response (default: False)
            new_conversation: Whether to start a new conversation (default: False)

        Returns:
            Dictionary containing the response, sources, and media (if stream=False)
            Generator yielding response chunks (if stream=True)

        Raises:
            Exception: If unable to get a valid response after retries
        """
        return self.message_processor.send_message(
            message=message,
            stream=stream,
            new_conversation=new_conversation,
        )

    def start_new_conversation(self) -> None:
        """Start a new conversation, resetting the conversation context."""
        self.message_processor.start_new_conversation()

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with Facebook."""
        return self.session_manager.is_authenticated

    @property
    def conversation_id(self) -> Optional[str]:
        """Get the current conversation ID."""
        return self.message_processor.external_conversation_id

    def refresh_session(self) -> None:
        """
        Refresh the session and cookies.
        Useful if you encounter authentication issues.
        """
        self.session_manager.refresh_cookies()
        
        # Update auth manager with new cookies
        self.auth_manager.cookies = self.session_manager.cookies
        
        # Update source fetcher with new cookies
        self.source_fetcher.cookies = self.session_manager.cookies