"""
Configuration constants and settings for the Meta AI API.
"""

# API Endpoints
META_AI_BASE_URL = "https://www.meta.ai"
META_AI_API_URL = "https://www.meta.ai/api/graphql/"
META_AI_GRAPH_URL = "https://graph.meta.ai/graphql?locale=user"

# Request Configuration
MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds
TOKEN_DELAY = 1  # seconds after getting access token

# User Agent
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# GraphQL Document IDs
DOC_ID_ACCEPT_TOS = "7604648749596940"
DOC_ID_SEND_MESSAGE = "7783822248314888"
DOC_ID_SEARCH_PLUGIN = "6946734308765963"

# Default Values
DEFAULT_DOB = "1999-01-01"
DEFAULT_ICEBREAKER_TYPE = "TEXT"
DEFAULT_ENTRYPOINT = "ABRA__CHAT__TEXT"