#!/usr/bin/env python3
"""
Command Line Interface for Meta AI API.

This module provides a comprehensive CLI tool for interacting with Meta AI,
supporting both interactive and batch modes with various output formats.
"""

import argparse
import json
import sys
import os
import warnings
from typing import Optional, Dict, Any
import getpass
from pathlib import Path

# Suppress the runpy warning that occurs when running as module
warnings.filterwarnings("ignore", message=".*found in sys.modules.*", category=RuntimeWarning)

# Handle imports for both package and direct execution
try:
    from .client import MetaAI
    from .config import DEFAULT_USER_AGENT, MAX_RETRIES
    from .exceptions import MetaAIException, FacebookRegionBlocked, AuthenticationError
except ImportError:
    from client import MetaAI
    from config import DEFAULT_USER_AGENT, MAX_RETRIES
    from exceptions import MetaAIException, FacebookRegionBlocked, AuthenticationError


class MetaAICLI:
    """Command Line Interface for Meta AI API."""

    def __init__(self):
        """Initialize the CLI."""
        self.client: Optional[MetaAI] = None
        self.config_file = Path.home() / ".meta_ai_config.json"

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}", file=sys.stderr)

    def setup_client(self, args) -> None:
        """Set up the Meta AI client with authentication if provided."""
        fb_email = args.email
        fb_password = args.password
        proxy = None

        # Load from config if not provided via args
        if not fb_email or not fb_password:
            config = self.load_config()
            fb_email = fb_email or config.get('email')
            fb_password = fb_password or config.get('password')

        # Set up proxy if provided
        if args.proxy:
            proxy = {"http": args.proxy, "https": args.proxy}

        # Interactive authentication if requested
        if args.auth and not (fb_email and fb_password):
            print("Facebook Authentication Setup")
            print("-" * 30)
            if not fb_email:
                fb_email = input("Facebook Email: ").strip()
            if not fb_password:
                fb_password = getpass.getpass("Facebook Password: ")

            # Save credentials if requested
            if input("Save credentials? (y/N): ").lower().startswith('y'):
                config = self.load_config()
                config.update({
                    'email': fb_email,
                    'password': fb_password
                })
                self.save_config(config)
                print("Credentials saved to ~/.meta_ai_config.json")

        try:
            self.client = MetaAI(
                fb_email=fb_email,
                fb_password=fb_password,
                proxy=proxy
            )
            
            if args.verbose:
                auth_status = "authenticated" if self.client.is_authenticated else "anonymous"
                print(f"✓ Client initialized ({auth_status})", file=sys.stderr)
                
        except Exception as e:
            print(f"Error initializing client: {e}", file=sys.stderr)
            sys.exit(1)

    def format_output(self, response: Dict[str, Any], format_type: str) -> str:
        """Format the response according to the specified format."""
        if format_type == "json":
            return json.dumps(response, indent=2, ensure_ascii=False)
        
        elif format_type == "text":
            output = response.get("message", "")
            return output.strip()
        
        elif format_type == "detailed":
            lines = []
            lines.append("=" * 50)
            lines.append("META AI RESPONSE")
            lines.append("=" * 50)
            lines.append("")
            lines.append(response.get("message", "").strip())
            
            if response.get("sources"):
                lines.append("")
                lines.append("SOURCES:")
                lines.append("-" * 20)
                for i, source in enumerate(response["sources"], 1):
                    lines.append(f"{i}. {source.get('title', 'Unknown')}")
                    lines.append(f"   {source.get('link', 'No link')}")
            
            if response.get("media"):
                lines.append("")
                lines.append("MEDIA:")
                lines.append("-" * 20)
                for i, media in enumerate(response["media"], 1):
                    lines.append(f"{i}. {media.get('type', 'Unknown')} - {media.get('url', 'No URL')}")
                    if media.get('prompt'):
                        lines.append(f"   Prompt: {media['prompt']}")
            
            lines.append("")
            lines.append("=" * 50)
            return "\n".join(lines)
        
        else:
            return str(response)

    def handle_prompt(self, args) -> None:
        """Handle the prompt command."""
        # Get message from args or stdin
        message = args.message
        if not message:
            # Check if there's piped input
            if not sys.stdin.isatty():
                message = sys.stdin.read().strip()
            
            if not message:
                print("Error: Message is required (provide as argument or pipe input)", file=sys.stderr)
                sys.exit(1)

        try:
            # Default to streaming for text format
            should_stream = args.stream or (args.format == "text" and not args.no_stream)
            
            if should_stream:
                self.handle_streaming_prompt(args, message)
            else:
                response = self.client.prompt(
                    message=message,
                    new_conversation=args.new_conversation
                )
                
                output = self.format_output(response, args.format)
                print(output)
                
        except MetaAIException as e:
            print(f"Meta AI Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)

    def handle_streaming_prompt(self, args, message: str) -> None:
        """Handle streaming prompt with real-time output."""
        try:
            if args.format == "json":
                # For JSON format, collect all chunks and output as array
                chunks = []
                for chunk in self.client.prompt(
                    message=message,
                    stream=True,
                    new_conversation=args.new_conversation
                ):
                    chunks.append(chunk)
                print(json.dumps(chunks, indent=2, ensure_ascii=False))
            
            elif args.format == "text":
                # For text format, show incremental updates
                previous_text = ""
                for chunk in self.client.prompt(
                    message=message,
                    stream=True,
                    new_conversation=args.new_conversation
                ):
                    current_text = chunk.get("message", "")
                    if current_text and current_text != previous_text:
                        new_part = current_text[len(previous_text):]
                        if new_part.strip():
                            print(new_part, end="", flush=True)
                        previous_text = current_text
                print()  # Final newline
            
            else:
                # For detailed format, show final result
                final_response = None
                for chunk in self.client.prompt(
                    message=message,
                    stream=True,
                    new_conversation=args.new_conversation
                ):
                    final_response = chunk
                
                if final_response:
                    output = self.format_output(final_response, args.format)
                    print(output)
                    
        except KeyboardInterrupt:
            print("\nStreaming interrupted by user", file=sys.stderr)
            sys.exit(1)

    def handle_interactive(self, args) -> None:
        """Handle interactive mode."""
        print("Meta AI Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit")
        print("-" * 40)
        
        if self.client.is_authenticated:
            print("✓ Authenticated with Facebook")
        else:
            print("ℹ Using anonymous mode")
        print()

        while True:
            try:
                user_input = input("meta-ai> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    self.show_interactive_help()
                    continue
                
                elif user_input.lower() == 'new':
                    self.client.start_new_conversation()
                    print("✓ Started new conversation")
                    continue
                
                elif user_input.lower() == 'status':
                    self.show_status()
                    continue
                
                # Regular prompt
                should_stream = args.stream or (args.format == "text" and not args.no_stream)
                
                if should_stream:
                    previous_text = ""
                    for chunk in self.client.prompt(user_input, stream=True):
                        current_text = chunk.get("message", "")
                        if current_text and current_text != previous_text:
                            new_part = current_text[len(previous_text):]
                            if new_part.strip():
                                print(new_part, end="", flush=True)
                            previous_text = current_text
                    print("\n")
                else:
                    response = self.client.prompt(user_input)
                    output = self.format_output(response, args.format)
                    print(output)
                    print()
                
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)

    def show_interactive_help(self) -> None:
        """Show help for interactive mode."""
        help_text = """
Interactive Mode Commands:
  help     - Show this help message
  new      - Start a new conversation
  status   - Show client status
  quit     - Exit interactive mode
  
Any other input will be sent as a prompt to Meta AI.
        """
        print(help_text.strip())

    def show_status(self) -> None:
        """Show current client status."""
        print("Client Status:")
        print(f"  Authenticated: {self.client.is_authenticated}")
        print(f"  Conversation ID: {self.client.conversation_id or 'None'}")
        print(f"  Config file: {self.config_file}")
        print(f"  Config exists: {self.config_file.exists()}")

    def handle_config(self, args) -> None:
        """Handle configuration commands."""
        if args.config_action == "show":
            config = self.load_config()
            if config:
                # Hide password for security
                display_config = config.copy()
                if 'password' in display_config:
                    display_config['password'] = '*' * len(display_config['password'])
                print(json.dumps(display_config, indent=2))
            else:
                print("No configuration found")
        
        elif args.config_action == "clear":
            if self.config_file.exists():
                self.config_file.unlink()
                print("Configuration cleared")
            else:
                print("No configuration to clear")
        
        elif args.config_action == "path":
            print(f"Configuration file: {self.config_file}")

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            prog="meta-ai",
            description="Command Line Interface for Meta AI API",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  meta-ai prompt "What is the capital of France?"
  echo "Tell me a joke" | meta-ai prompt
  meta-ai prompt "Hello" --no-stream
  meta-ai prompt "Generate code" --format detailed
  meta-ai interactive
  meta-ai prompt "Hello" --auth --format json
  meta-ai config show
            """
        )

        # Global options
        parser.add_argument(
            "--email", 
            help="Facebook email for authentication"
        )
        parser.add_argument(
            "--password", 
            help="Facebook password for authentication"
        )
        parser.add_argument(
            "--proxy", 
            help="Proxy URL (e.g., http://proxy:8080)"
        )
        parser.add_argument(
            "--verbose", "-v", 
            action="store_true", 
            help="Verbose output"
        )
        # Note: format is added to individual subcommands that need it

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Prompt command
        prompt_parser = subparsers.add_parser(
            "prompt", 
            help="Send a prompt to Meta AI"
        )
        prompt_parser.add_argument(
            "message", 
            nargs="?",
            help="The message to send to Meta AI (or pipe input via stdin)"
        )
        prompt_parser.add_argument(
            "--stream", 
            action="store_true", 
            help="Force streaming mode (text format streams by default)"
        )
        prompt_parser.add_argument(
            "--no-stream", 
            action="store_true", 
            help="Disable streaming mode"
        )
        prompt_parser.add_argument(
            "--new-conversation", 
            action="store_true", 
            help="Start a new conversation"
        )
        prompt_parser.add_argument(
            "--auth", 
            action="store_true", 
            help="Prompt for Facebook authentication"
        )
        prompt_parser.add_argument(
            "--format", 
            choices=["text", "json", "detailed"], 
            default="text",
            help="Output format (default: text)"
        )

        # Interactive command
        interactive_parser = subparsers.add_parser(
            "interactive", 
            help="Start interactive mode"
        )
        interactive_parser.add_argument(
            "--stream", 
            action="store_true", 
            help="Force streaming mode for responses (text format streams by default)"
        )
        interactive_parser.add_argument(
            "--no-stream", 
            action="store_true", 
            help="Disable streaming mode for responses"
        )
        interactive_parser.add_argument(
            "--auth", 
            action="store_true", 
            help="Prompt for Facebook authentication"
        )
        interactive_parser.add_argument(
            "--format", 
            choices=["text", "json", "detailed"], 
            default="text",
            help="Output format for responses (default: text)"
        )

        # Config command
        config_parser = subparsers.add_parser(
            "config", 
            help="Manage configuration"
        )
        config_parser.add_argument(
            "config_action", 
            choices=["show", "clear", "path"],
            help="Configuration action"
        )

        return parser

    def run(self, args=None) -> None:
        """Run the CLI with the given arguments."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        # Handle config command separately (doesn't need client)
        if parsed_args.command == "config":
            self.handle_config(parsed_args)
            return

        # Set up client for other commands
        if parsed_args.command in ["prompt", "interactive"]:
            self.setup_client(parsed_args)

            if parsed_args.command == "prompt":
                self.handle_prompt(parsed_args)
            elif parsed_args.command == "interactive":
                self.handle_interactive(parsed_args)
        else:
            parser.print_help()


def main():
    """Main entry point for the CLI."""
    cli = MetaAICLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()