"""
Custom exceptions for Meta AI API.
"""


class MetaAIException(Exception):
    """Base exception for Meta AI API errors."""
    pass


class FacebookInvalidCredentialsException(MetaAIException):
    """Raised when Facebook credentials are invalid."""
    pass


class FacebookRegionBlocked(MetaAIException):
    """Raised when the region is blocked from accessing Meta AI."""
    pass


class AuthenticationError(MetaAIException):
    """Raised when authentication fails."""
    pass


class APIError(MetaAIException):
    """Raised when the API returns an error."""
    pass


class RateLimitError(MetaAIException):
    """Raised when rate limits are exceeded."""
    pass


class NetworkError(MetaAIException):
    """Raised when network requests fail."""
    pass
