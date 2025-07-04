import os; os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
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
import time
import subprocess
import shutil
import asyncio
import threading
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
        self.tts_enabled = False
        self.tts_command = None
        self.tts_method = "command"  # "command" or "edge-tts"
        self.edge_tts_voice = "en-US-AriaNeural"  # Default voice
        self._mixer_lock = threading.Lock()
        self._mixer_initialized = False
        self._last_response = None  # Store last response for on-demand TTS
        self._voices_cache = None  # Cache for available voices
        self._language_voices = {}  # Cache voices by language

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

        # Set up TTS if requested
        if hasattr(args, 'tts') and args.tts:
            if hasattr(args, 'tts_voice'):
                self.edge_tts_voice = args.tts_voice
            self.setup_tts(args.tts_command if hasattr(args, 'tts_command') else None)

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
        # Get message from args and/or stdin
        message_parts = []

        # Check for piped input first
        piped_input = ""
        if not sys.stdin.isatty():
            piped_input = sys.stdin.read().strip()
            if piped_input:
                message_parts.append(piped_input)

        # Add the prompt argument if provided
        if args.message:
            message_parts.append(args.message)

        # Combine the parts
        if not message_parts:
            print("Error: Message is required (provide as argument or pipe input)", file=sys.stderr)
            sys.exit(1)

        # Join with a newline if we have both piped input and a prompt
        if len(message_parts) == 2:
            message = f"{message_parts[0]}\n\n{message_parts[1]}"
        else:
            message = message_parts[0]

        try:
            # Default to streaming for text format
            should_stream = args.stream or (args.format == "text" and not args.no_stream)

            # Start timing
            start_time = time.time()

            if should_stream:
                self.handle_streaming_prompt(args, message, start_time)
            else:
                response = self.client.prompt(
                    message=message,
                    new_conversation=args.new_conversation
                )

                # Calculate timing
                end_time = time.time()
                elapsed_time = end_time - start_time

                output = self.format_output(response, args.format)
                print(output)

                # Speak the response if TTS is enabled
                if self.tts_enabled and args.format == "text":
                    self.speak_text(response.get("message", ""))

                # Show timing if requested
                if args.timing:
                    print(f"\n⏱️  Response time: {elapsed_time:.2f} seconds", file=sys.stderr)

        except MetaAIException as e:
            print(f"Meta AI Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)

    def handle_streaming_prompt(self, args, message: str, start_time: float) -> None:
        """Handle streaming prompt with real-time output."""
        try:
            first_chunk_time = None
            final_response = None

            if args.format == "json":
                # For JSON format, collect all chunks and output as array
                chunks = []
                for chunk in self.client.prompt(
                    message=message,
                    stream=True,
                    new_conversation=args.new_conversation
                ):
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                    chunks.append(chunk)
                    final_response = chunk
                print(json.dumps(chunks, indent=2, ensure_ascii=False))

            elif args.format == "text":
                # For text format, show incremental updates
                previous_text = ""
                for chunk in self.client.prompt(
                    message=message,
                    stream=True,
                    new_conversation=args.new_conversation
                ):
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                    current_text = chunk.get("message", "")
                    if current_text and current_text != previous_text:
                        new_part = current_text[len(previous_text):]
                        if new_part.strip():
                            print(new_part, end="", flush=True)
                        previous_text = current_text
                    final_response = chunk
                print()  # Final newline

            else:
                # For detailed format, show final result
                for chunk in self.client.prompt(
                    message=message,
                    stream=True,
                    new_conversation=args.new_conversation
                ):
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                    final_response = chunk

                if final_response:
                    output = self.format_output(final_response, args.format)
                    print(output)

            # Speak the final response if TTS is enabled
            if self.tts_enabled and final_response and args.format == "text":
                self.speak_text(final_response.get("message", ""))

            # Show timing if requested
            if args.timing and first_chunk_time is not None:
                end_time = time.time()
                total_time = end_time - start_time
                first_chunk_time_elapsed = first_chunk_time - start_time

                print(f"\n⏱️  Time to first response: {first_chunk_time_elapsed:.2f}s", file=sys.stderr)
                print(f"⏱️  Total response time: {total_time:.2f}s", file=sys.stderr)

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

                elif user_input.lower().startswith('tts'):
                    self.handle_tts_command(user_input)
                    continue

                elif user_input.lower() == 'speak':
                    self.handle_speak_command()
                    continue

                # Regular prompt
                should_stream = args.stream or (args.format == "text" and not args.no_stream)
                start_time = time.time()

                if should_stream:
                    previous_text = ""
                    first_chunk_time = None
                    for chunk in self.client.prompt(user_input, stream=True):
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                        current_text = chunk.get("message", "")
                        if current_text and current_text != previous_text:
                            new_part = current_text[len(previous_text):]
                            if new_part.strip():
                                print(new_part, end="", flush=True)
                            previous_text = current_text
                    print("\n")

                    # Store last response and speak if TTS is enabled
                    if previous_text:
                        self._last_response = previous_text
                        if self.tts_enabled:
                            self.speak_text(previous_text)

                    # Show timing for streaming in interactive mode
                    if args.timing and first_chunk_time is not None:
                        end_time = time.time()
                        total_time = end_time - start_time
                        first_chunk_time_elapsed = first_chunk_time - start_time
                        print(f"⏱️  Time to first response: {first_chunk_time_elapsed:.2f}s", file=sys.stderr)
                        print(f"⏱️  Total response time: {total_time:.2f}s", file=sys.stderr)
                else:
                    response = self.client.prompt(user_input)
                    end_time = time.time()
                    elapsed_time = end_time - start_time

                    output = self.format_output(response, args.format)
                    print(output)

                    # Store last response and speak if TTS is enabled
                    if args.format == "text":
                        self._last_response = response.get("message", "")
                        if self.tts_enabled:
                            self.speak_text(self._last_response)

                    # Show timing for non-streaming in interactive mode
                    if args.timing:
                        print(f"⏱️  Response time: {elapsed_time:.2f} seconds", file=sys.stderr)
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
  tts      - Toggle TTS on/off
  tts on   - Enable TTS
  tts off  - Disable TTS
  tts voice <voice> - Set edge-tts voice (e.g., en-US-JennyNeural)
  speak    - Speak the last response again
  quit     - Exit interactive mode

Any other input will be sent as a prompt to Meta AI.
        """
        print(help_text.strip())

    def handle_tts_command(self, user_input: str) -> None:
        """Handle TTS-related commands in interactive mode."""
        parts = user_input.split()  # Don't convert to lowercase for voice names

        if len(parts) == 1:  # Just "tts"
            # Toggle TTS
            if self.tts_enabled:
                self.tts_enabled = False
                print("✓ TTS disabled")
            else:
                if self.tts_command or self.tts_method == "edge-tts":
                    self.tts_enabled = True
                    print("✓ TTS enabled")
                else:
                    self.setup_tts()
                    if self.tts_enabled:
                        print("✓ TTS enabled")
                    else:
                        print("✗ TTS could not be enabled")

        elif len(parts) == 2:
            if parts[1].lower() == "on":
                if self.tts_command or self.tts_method == "edge-tts":
                    self.tts_enabled = True
                    print("✓ TTS enabled")
                else:
                    self.setup_tts()
                    if self.tts_enabled:
                        print("✓ TTS enabled")
                    else:
                        print("✗ TTS could not be enabled")

            elif parts[1].lower() == "off":
                self.tts_enabled = False
                print("✓ TTS disabled")

            else:
                print("Usage: tts [on|off|voice <voice_name>]")

        elif len(parts) == 3 and parts[1].lower() == "voice":
            if self.tts_method == "edge-tts":
                self.edge_tts_voice = parts[2]
                print(f"✓ TTS voice set to: {self.edge_tts_voice}")
            else:
                print("Voice selection only available with edge-tts")

        else:
            print("Usage: tts [on|off|voice <voice_name>]")

    def handle_speak_command(self) -> None:
        """Handle the speak command to replay last response."""
        if not self._last_response:
            print("No previous response to speak")
            return

        if not self.tts_enabled:
            # Temporarily enable TTS for this command
            temp_enabled = False
            try:
                import edge_tts
                temp_enabled = True
            except ImportError:
                print("TTS not available. Install edge-tts with: pip install edge-tts pygame googletrans==4.0.0rc1")
                return

            if temp_enabled:
                print("🔊 Speaking last response...")
                # Use edge-tts method directly without changing global state
                self.speak_with_edge_tts(self.clean_text_for_tts(self._last_response), self.select_random_voice(self._last_response))
        else:
            print("🔊 Speaking last response...")
            self.speak_text(self._last_response)

    def setup_tts(self, tts_command: Optional[str] = None) -> None:
        """Set up TTS functionality."""
        # First, try to use edge-tts if available
        try:
            import edge_tts
            self.tts_method = "edge-tts"
            self.tts_enabled = True
            print(f"✓ TTS enabled with edge-tts (voice: {self.edge_tts_voice})", file=sys.stderr)
            return
        except ImportError:
            pass

        # Fall back to external commands
        if tts_command:
            self.tts_command = tts_command
        else:
            # Default TTS command - try to find common TTS tools
            default_commands = [
                "~/Dev/python/tts/.venv/bin/tts -t -",  # Your specific TTS
                "espeak",  # Common Linux TTS
                "say",     # macOS TTS
                "spd-say", # Speech Dispatcher
            ]

            for cmd in default_commands:
                cmd_path = cmd.split()[0]
                if cmd_path.startswith("~/"):
                    cmd_path = os.path.expanduser(cmd_path)

                if shutil.which(cmd_path) or os.path.exists(cmd_path):
                    self.tts_command = cmd
                    break

        if self.tts_command:
            self.tts_method = "command"
            self.tts_enabled = True
            print(f"✓ TTS enabled with command: {self.tts_command}", file=sys.stderr)
        else:
            print("⚠ TTS requested but no TTS method found. Install edge-tts with: pip install edge-tts", file=sys.stderr)
            self.tts_enabled = False

    def speak_text(self, text: str) -> None:
        """Convert text to speech using the configured TTS method."""
        if not self.tts_enabled:
            return
        
        try:
            # Clean the text for TTS (remove markdown, etc.)
            clean_text = self.clean_text_for_tts(text)
            if not clean_text.strip():
                return
            
            if self.tts_method == "edge-tts":
                # Select random voice based on language
                selected_voice = self.select_random_voice(clean_text)
                self.speak_with_edge_tts(clean_text, selected_voice)
            elif self.tts_method == "command" and self.tts_command:
                self.speak_with_command(clean_text)
                
        except Exception as e:
            print(f"TTS Error: {e}", file=sys.stderr)

    def _init_pygame_mixer(self):
        """Initialize pygame mixer once, thread-safely."""
        with self._mixer_lock:
            if not self._mixer_initialized:
                try:
                    import pygame
                    import os

                    # Set audio driver preferences
                    os.environ['SDL_AUDIODRIVER'] = 'pulse,alsa,oss'

                    # Initialize mixer with conservative settings
                    pygame.mixer.pre_init(
                        frequency=22050,
                        size=-16,
                        channels=2,
                        buffer=1024
                    )
                    pygame.mixer.init()
                    self._mixer_initialized = True
                    return True
                except Exception as e:
                    print(f"TTS Error: Failed to initialize pygame mixer: {e}", file=sys.stderr)
                    return False
            return True

    def speak_with_edge_tts(self, text: str, voice: str = None) -> None:
        """Speak text using edge-tts with pygame in a background thread."""
        def _speak_in_background():
            temp_path = None
            try:
                import edge_tts
                import pygame
                import tempfile

                # Create a temporary file for the audio
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_path = temp_file.name

                # Generate speech asynchronously
                async def generate_speech():
                    communicate = edge_tts.Communicate(text, voice or self.edge_tts_voice)
                    await communicate.save(temp_path)

                # Run the async function
                asyncio.run(generate_speech())

                # Initialize mixer if needed (thread-safe)
                if not self._init_pygame_mixer():
                    return

                # Use lock to prevent concurrent audio operations
                with self._mixer_lock:
                    try:
                        # Stop any currently playing audio
                        pygame.mixer.music.stop()

                        # Load and play the new audio
                        pygame.mixer.music.load(temp_path)
                        pygame.mixer.music.play()

                    except Exception as e:
                        print(f"TTS Error: Failed to play audio: {e}", file=sys.stderr)
                        return

                # Wait for playback to finish (outside the lock so other operations can proceed)

                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)


            except ImportError as e:
                missing_pkg = "edge-tts" if "edge_tts" in str(e) else "pygame"
                print(f"TTS Error: {missing_pkg} not installed. Install with: pip install {missing_pkg}", file=sys.stderr)
            except Exception as e:
                print(f"Edge-TTS Error: {e}", file=sys.stderr)
            finally:
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass  # Ignore cleanup errors

        # Run TTS in a background thread so it doesn't block the main thread
        try:
            tts_thread = threading.Thread(target=_speak_in_background, daemon=True)
            tts_thread.start()
        except Exception as e:
            print(f"TTS Error: {e}", file=sys.stderr)

    def speak_with_command(self, text: str) -> None:
        """Speak text using external command."""
        try:
            # Run TTS command - expand paths properly
            cmd_parts = self.tts_command.split()
            # Expand the first part (command path) if it contains ~
            if cmd_parts[0].startswith("~/"):
                cmd_parts[0] = os.path.expanduser(cmd_parts[0])

            process = subprocess.Popen(
                cmd_parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            process.communicate(input=text)
        except Exception as e:
            print(f"Command TTS Error: {e}", file=sys.stderr)

    def clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS pronunciation."""
        import re

        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        text = re.sub(r'#{1,6}\s*(.*)', r'\1', text)  # Headers

        # Remove URLs (replace with "link")
        text = re.sub(r'https?://[^\s]+', 'link', text)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def show_status(self) -> None:
        """Show current client status."""
        print("Client Status:")
        print(f"  Authenticated: {self.client.is_authenticated}")
        print(f"  Conversation ID: {self.client.conversation_id or 'None'}")
        print(f"  TTS Enabled: {self.tts_enabled}")
        if self.tts_enabled:
            print(f"  TTS Method: {self.tts_method}")
            if self.tts_method == "edge-tts":
                print(f"  TTS Voice: {self.edge_tts_voice}")
            elif self.tts_method == "command":
                print(f"  TTS Command: {self.tts_command}")
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
  cat file.txt | meta-ai prompt "summarize this"
  echo "def hello():" | meta-ai prompt "explain this code"
  meta-ai prompt "Hello" --no-stream --timing
  meta-ai prompt "Generate code" --format detailed --timing
  meta-ai interactive --timing
  meta-ai prompt "Hello" --auth --format json
  meta-ai prompt "Tell me a story" --tts
  meta-ai interactive --tts --tts-command "espeak"
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
            help="The message/prompt to send to Meta AI (can be combined with piped input)"
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
        prompt_parser.add_argument(
            "--timing",
            action="store_true",
            help="Show response time information"
        )
        prompt_parser.add_argument(
            "--tts",
            action="store_true",
            help="Enable text-to-speech for the response"
        )
        prompt_parser.add_argument(
            "--tts-command",
            help="Custom TTS command (default: auto-detect)"
        )
        prompt_parser.add_argument(
            "--tts-voice",
            default="en-US-AriaNeural",
            help="Voice for edge-tts (default: en-US-AriaNeural)"
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
        interactive_parser.add_argument(
            "--timing",
            action="store_true",
            help="Show response time information"
        )
        interactive_parser.add_argument(
            "--tts",
            action="store_true",
            help="Enable text-to-speech for responses"
        )
        interactive_parser.add_argument(
            "--tts-command",
            help="Custom TTS command (default: auto-detect)"
        )
        interactive_parser.add_argument(
            "--tts-voice",
            default="en-US-AriaNeural",
            help="Voice for edge-tts (default: en-US-AriaNeural)"
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


    def detect_language(self, text: str) -> str:
        """Detect the language of the text using googletrans."""
        try:
            from googletrans import Translator
            translator = Translator()
            detected = translator.detect(text)
            lang_code = detected.lang
            language_map = {
                "en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
                "it": "it-IT", "pt": "pt-BR", "ru": "ru-RU", "ja": "ja-JP",
                "ko": "ko-KR", "zh": "zh-CN", "ar": "ar-SA", "hi": "hi-IN"
            }
            return language_map.get(lang_code, "en-US")
        except Exception:
            return "en-US"

    async def get_voices_for_language(self, language: str) -> list:
        """Get available voices for a specific language."""
        try:
            import edge_tts
            if self._voices_cache is None:
                self._voices_cache = await edge_tts.list_voices()
                for voice in self._voices_cache:
                    lang = voice["Locale"]
                    if lang not in self._language_voices:
                        self._language_voices[lang] = []
                    self._language_voices[lang].append(voice)
            return self._language_voices.get(language, self._language_voices.get("en-US", []))
        except Exception:
            return []

    def select_random_voice(self, text: str) -> str:
        """Select a random voice based on detected language."""
        try:
            import asyncio, random
            detected_lang = self.detect_language(text)
            async def get_voice():
                voices = await self.get_voices_for_language(detected_lang)
                if voices:
                    neural_voices = [v for v in voices if "Neural" in v.get("VoiceTag", "")]
                    if neural_voices: voices = neural_voices
                    selected = random.choice(voices)
                    return selected["ShortName"]
                return self.edge_tts_voice
            return asyncio.run(get_voice())
        except Exception:
            return self.edge_tts_voice

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
    def detect_language(self, text: str) -> str:
        """Detect the language of the text using googletrans."""
        try:
            from googletrans import Translator
            translator = Translator()
            detected = translator.detect(text)
            lang_code = detected.lang
            
            # Map googletrans language codes to edge-tts compatible ones
            language_map = {
                "en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
                "it": "it-IT", "pt": "pt-BR", "ru": "ru-RU", "ja": "ja-JP",
                "ko": "ko-KR", "zh": "zh-CN", "zh-cn": "zh-CN", "ar": "ar-SA",
                "hi": "hi-IN", "nl": "nl-NL", "sv": "sv-SE", "da": "da-DK",
                "no": "nb-NO", "fi": "fi-FI", "pl": "pl-PL", "tr": "tr-TR",
                "th": "th-TH", "vi": "vi-VN", "ca": "ca-ES", "cs": "cs-CZ",
                "el": "el-GR", "he": "he-IL", "hu": "hu-HU", "id": "id-ID",
                "ms": "ms-MY", "ro": "ro-RO", "sk": "sk-SK", "sl": "sl-SI",
                "uk": "uk-UA"
            }
            return language_map.get(lang_code, "en-US")
        except Exception as e:
            print(f"TTS Warning: Language detection failed, using English: {e}", file=sys.stderr)
            return "en-US"

    async def get_voices_for_language(self, language: str) -> list:
        """Get available voices for a specific language."""
        try:
            import edge_tts
            
            # Cache all voices if not already cached
            if self._voices_cache is None:
                print("🔄 Caching available voices...", file=sys.stderr)
                self._voices_cache = await edge_tts.list_voices()
                
                # Group voices by language
                for voice in self._voices_cache:
                    lang = voice["Locale"]
                    if lang not in self._language_voices:
                        self._language_voices[lang] = []
                    self._language_voices[lang].append(voice)
                
                print(f"✓ Cached {len(self._voices_cache)} voices for {len(self._language_voices)} languages", file=sys.stderr)
            
            # Return voices for the requested language, fallback to en-US
            voices = self._language_voices.get(language, self._language_voices.get("en-US", []))
            return voices
            
        except Exception as e:
            print(f"TTS Warning: Could not get voices: {e}", file=sys.stderr)
            return []

    def select_random_voice(self, text: str) -> str:
        """Select a random voice based on detected language."""
        try:
            import asyncio
            import random
            
            # Detect language
            detected_lang = self.detect_language(text)
            
            # Get voices for the language
            async def get_voice():
                voices = await self.get_voices_for_language(detected_lang)
                if voices:
                    # Filter for Neural voices (higher quality)
                    neural_voices = [v for v in voices if "Neural" in v.get("VoiceTag", "")]
                    if neural_voices:
                        voices = neural_voices
                    
                    # Select random voice
                    selected_voice = random.choice(voices)
                    voice_name = selected_voice["ShortName"]
                    friendly_name = selected_voice.get("FriendlyName", voice_name)
                    
                    print(f"🎭 Using {friendly_name} for {detected_lang}", file=sys.stderr)
                    return voice_name
                else:
                    print(f"⚠ No voices found for {detected_lang}, using default", file=sys.stderr)
                    return self.edge_tts_voice
            
            # Run async function
            return asyncio.run(get_voice())
            
        except Exception as e:
            print(f"TTS Warning: Voice selection failed, using default: {e}", file=sys.stderr)
            return self.edge_tts_voice



if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
