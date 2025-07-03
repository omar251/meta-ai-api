#!/usr/bin/env python3
"""
Example demonstrating the refactored Meta AI API usage.

This example shows both the legacy interface (for backward compatibility)
and the new clean interface (recommended for new code).
"""

import sys
import os

# Add the src directory to the path so we can import meta_ai_api
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from meta_ai_api import MetaAI, MetaAIClient


def demo_legacy_interface():
    """Demonstrate the legacy interface (backward compatibility)."""
    print("=== Legacy Interface Demo ===")
    
    # This will show a deprecation warning
    client = MetaAI()
    
    print(f"Authenticated: {client.is_authed}")
    print(f"Has session: {hasattr(client, 'session')}")
    print(f"Has cookies: {hasattr(client, 'cookies')}")
    
    # Legacy properties still work
    print(f"Access token: {client.access_token}")
    print(f"Conversation ID: {client.external_conversation_id}")
    
    print("Legacy interface working correctly!\n")


def demo_new_interface():
    """Demonstrate the new clean interface (recommended)."""
    print("=== New Interface Demo ===")
    
    # No deprecation warning
    client = MetaAIClient()
    
    print(f"Authenticated: {client.is_authenticated}")
    print(f"Has session manager: {hasattr(client, 'session_manager')}")
    print(f"Has auth manager: {hasattr(client, 'auth_manager')}")
    
    # New properties and methods
    print(f"Conversation ID: {client.conversation_id}")
    
    # Demonstrate new methods
    client.start_new_conversation()
    print("Started new conversation")
    
    # Show component access
    print(f"Session manager type: {type(client.session_manager).__name__}")
    print(f"Auth manager type: {type(client.auth_manager).__name__}")
    print(f"Message processor type: {type(client.message_processor).__name__}")
    
    print("New interface working correctly!\n")


def demo_configuration():
    """Demonstrate the centralized configuration."""
    print("=== Configuration Demo ===")
    
    from meta_ai_api.config import (
        MAX_RETRIES, 
        RETRY_DELAY, 
        DEFAULT_USER_AGENT,
        META_AI_BASE_URL
    )
    
    print(f"Max retries: {MAX_RETRIES}")
    print(f"Retry delay: {RETRY_DELAY} seconds")
    print(f"Base URL: {META_AI_BASE_URL}")
    print(f"User agent: {DEFAULT_USER_AGENT[:50]}...")
    
    print("Configuration accessible and working!\n")


def demo_exceptions():
    """Demonstrate the improved exception hierarchy."""
    print("=== Exception Hierarchy Demo ===")
    
    from meta_ai_api.exceptions import (
        MetaAIException,
        FacebookRegionBlocked,
        AuthenticationError,
        APIError
    )
    
    # Test exception hierarchy
    exceptions_to_test = [
        FacebookRegionBlocked("Region blocked"),
        AuthenticationError("Auth failed"),
        APIError("API error")
    ]
    
    for exc in exceptions_to_test:
        try:
            raise exc
        except MetaAIException as e:
            print(f"✓ {type(e).__name__}: {e}")
    
    print("Exception hierarchy working correctly!\n")


def main():
    """Run all demos."""
    print("Meta AI API Refactoring Demo")
    print("=" * 40)
    
    try:
        demo_legacy_interface()
        demo_new_interface()
        demo_configuration()
        demo_exceptions()
        
        print("🎉 All demos completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()