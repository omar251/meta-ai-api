# Meta AI CLI Tool Documentation

The Meta AI CLI tool provides a comprehensive command-line interface for interacting with Meta AI. It supports both one-off prompts and interactive sessions, with various output formats and authentication options.

## Installation

After installing the package, the CLI tool is available as `meta-ai`:

```bash
pip install meta-ai-api
meta-ai --help
```

Or run directly from source:

```bash
# Preferred method (no warnings)
python -m meta_ai_api --help

# Alternative methods
python -m meta_ai_api.cli --help
python src/meta_ai_api/cli.py --help
```

## Quick Start

### Basic Usage

```bash
# Simple prompt
meta-ai prompt "What is the capital of France?"

# Get text-only output
meta-ai prompt "Tell me a joke" --format text

# Get JSON output
meta-ai prompt "What is 2+2?" --format json

# Stream response in real-time
meta-ai prompt "Tell me a story" --stream

# Enable text-to-speech for responses
meta-ai prompt "What is artificial intelligence?" --tts

# Use specific voice for TTS
meta-ai prompt "Hello world" --tts --tts-voice "en-US-JennyNeural"
```

**From source (development):**
```bash
# Preferred method
python -m meta_ai_api prompt "Hello!"

# Alternative methods
python -m meta_ai_api.cli prompt "Hello!"
python src/meta_ai_api/cli.py prompt "Hello!"
```

### Interactive Mode

```bash
# Start interactive session
meta-ai interactive

# Interactive session with streaming
meta-ai interactive --stream
```

## Commands

### 1. `prompt` - Send a single prompt

Send a message to Meta AI and get a response.

```bash
meta-ai prompt "Your message here" [options]
```

**Options:**
- `--format {text,json,detailed}` - Output format (default: detailed)
- `--stream` - Stream response in real-time
- `--new-conversation` - Start a new conversation
- `--auth` - Prompt for Facebook authentication

**Examples:**
```bash
# Basic prompt with detailed output
meta-ai prompt "What is machine learning?"

# Text-only output
meta-ai prompt "Hello" --format text

# JSON output for programmatic use
meta-ai prompt "What is AI?" --format json

# Streaming response
meta-ai prompt "Tell me a long story" --stream

# Start new conversation
meta-ai prompt "My name is Alice" --new-conversation
meta-ai prompt "What is my name?"  # Will remember Alice

# With authentication
meta-ai prompt "Generate an image of a cat" --auth
```

### 2. `interactive` - Interactive mode

Start an interactive session where you can have ongoing conversations.

```bash
meta-ai interactive [options]
```

**Options:**
- `--format {text,json,detailed}` - Output format for responses
- `--stream` - Use streaming for all responses
- `--auth` - Prompt for Facebook authentication

**Interactive Commands:**
- `help` - Show available commands
- `new` - Start a new conversation
- `status` - Show client status
- `quit` or `exit` - Exit interactive mode
- `tts` - Toggle text-to-speech on/off
- `tts on` - Enable text-to-speech
- `tts off` - Disable text-to-speech
- `tts voice <voice>` - Set TTS voice (e.g., en-US-JennyNeural)

**Example:**
```bash
meta-ai interactive
meta-ai> Hello, how are you?
meta-ai> new
✓ Started new conversation
meta-ai> What is my name?  # Won't remember previous conversation
meta-ai> quit
```

### 3. `config` - Configuration management

Manage saved configuration and credentials.

```bash
meta-ai config {show,clear,path}
```

**Subcommands:**
- `show` - Display current configuration (passwords hidden)
- `clear` - Remove saved configuration
- `path` - Show configuration file location

**Examples:**
```bash
# Show current config
meta-ai config show

# Show config file location
meta-ai config path

# Clear saved credentials
meta-ai config clear
```

## Global Options

These options can be used with any command:

- `--email EMAIL` - Facebook email for authentication
- `--password PASSWORD` - Facebook password for authentication
- `--proxy PROXY` - Proxy URL (e.g., http://proxy:8080)
- `--verbose, -v` - Verbose output
- `--help, -h` - Show help message

## Output Formats

### 1. `text` - Plain text only
Returns just the message content without formatting.

```bash
meta-ai prompt "Hello" --format text
# Output: Hello! How can I help you today?
```

### 2. `json` - JSON format
Returns structured JSON with message, sources, and media.

```bash
meta-ai prompt "Hello" --format json
# Output:
# {
#   "message": "Hello! How can I help you today?",
#   "sources": [],
#   "media": []
# }
```

### 3. `detailed` - Formatted output (default)
Returns nicely formatted output with sections for message, sources, and media.

```bash
meta-ai prompt "What is AI?" --format detailed
# Output:
# ==================================================
# META AI RESPONSE
# ==================================================
# 
# Artificial Intelligence (AI) refers to...
# 
# SOURCES:
# --------------------
# 1. Wikipedia - Artificial Intelligence
#    https://en.wikipedia.org/wiki/Artificial_intelligence
# 
# ==================================================
```

## Authentication

### Anonymous Mode (Default)
By default, the CLI uses anonymous access which works for most queries but has some limitations.

### Facebook Authentication
For full features (like image generation), you can authenticate with Facebook:

```bash
# Interactive authentication
meta-ai prompt "Generate an image" --auth

# Direct credentials
meta-ai prompt "Hello" --email your@email.com --password yourpassword

# Save credentials for future use
meta-ai prompt "Hello" --auth
# Follow prompts and choose to save credentials
```

**Security Note:** Saved credentials are stored in `~/.meta_ai_config.json`. Keep this file secure.

## Streaming

Streaming mode shows responses as they're generated in real-time:

```bash
# Stream a single prompt
meta-ai prompt "Tell me a story" --stream

# Use streaming in interactive mode
meta-ai interactive --stream

# Enable TTS in interactive mode
meta-ai interactive --tts

# Interactive mode with specific TTS voice
meta-ai interactive --tts --tts-voice "en-US-AriaNeural"
```

**Streaming Behavior:**
- `text` format: Shows incremental text as it arrives
- `json` format: Collects all chunks and outputs as JSON array
- `detailed` format: Shows final formatted result

## Configuration File

The CLI can save configuration in `~/.meta_ai_config.json`:

```json
{
  "email": "your@email.com",
  "password": "your_password"
}
```

**Management:**
```bash
# View config location
meta-ai config path

# View config (passwords hidden)
meta-ai config show

# Clear config
meta-ai config clear
```

## Error Handling

The CLI provides helpful error messages:

```bash
# Region blocked
meta-ai prompt "Hello"
# Error: Meta AI Error: Unable to receive a valid response from Meta AI...

# Invalid credentials
meta-ai prompt "Hello" --email wrong@email.com --password wrong
# Error: Meta AI Error: Was not able to login to Facebook...

# Network issues
meta-ai prompt "Hello" --proxy http://invalid:8080
# Error: Unexpected error: Proxy is not working.
```

## Advanced Usage

### Scripting with JSON Output

```bash
#!/bin/bash
# Get AI response and extract just the message
response=$(meta-ai prompt "What is the weather like?" --format json)
message=$(echo "$response" | jq -r '.message')
echo "AI says: $message"
```

### Batch Processing

```bash
# Process multiple prompts
while IFS= read -r line; do
    echo "Prompt: $line"
    meta-ai prompt "$line" --format text
    echo "---"
done < prompts.txt
```

### Using with Proxy

```bash
# Corporate proxy
meta-ai prompt "Hello" --proxy http://proxy.company.com:8080

# SOCKS proxy
meta-ai prompt "Hello" --proxy socks5://127.0.0.1:1080
```

## Troubleshooting

### Common Issues

1. **Import warnings when running directly:**
   ```bash
   # Use the module form instead
   python -m meta_ai_api.cli prompt "Hello"
   ```

2. **Region blocked errors:**
   ```bash
   # Try with a VPN or proxy
   meta-ai prompt "Hello" --proxy http://your-proxy:8080
   ```

3. **Authentication failures:**
   ```bash
   # Clear saved config and try again
   meta-ai config clear
   meta-ai prompt "Hello" --auth
   ```

4. **Permission errors with config file:**
   ```bash
   # Check config file permissions
   meta-ai config path
   ls -la ~/.meta_ai_config.json
   ```

### Debug Mode

Use verbose mode for debugging:

```bash
meta-ai prompt "Hello" --verbose
```

## Examples

### Basic Queries
```bash
# Simple questions
meta-ai prompt "What is the capital of Japan?"
meta-ai prompt "Explain quantum computing in simple terms"
meta-ai prompt "Write a haiku about programming"

# Math and calculations
meta-ai prompt "What is 15% of 200?"
meta-ai prompt "Convert 100 fahrenheit to celsius"
```

### Creative Tasks
```bash
# Creative writing
meta-ai prompt "Write a short story about a robot" --stream
meta-ai prompt "Create a poem about the ocean"

# Code generation
meta-ai prompt "Write a Python function to sort a list"
meta-ai prompt "Explain this code: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
```

### Information Gathering
```bash
# Current events (requires internet connection)
meta-ai prompt "What are the latest news about AI?"
meta-ai prompt "What is the current weather in New York?"

# Research assistance
meta-ai prompt "Summarize the benefits of renewable energy" --format detailed
```

### Interactive Sessions
```bash
meta-ai interactive
meta-ai> I'm planning a trip to Paris
meta-ai> What are the must-see attractions?
meta-ai> How many days should I spend there?
meta-ai> new
meta-ai> What is the best time to visit Japan?
meta-ai> quit
```

## Integration Examples

### Shell Scripts
```bash
#!/bin/bash
# AI-powered commit message generator
diff=$(git diff --cached)
if [ -n "$diff" ]; then
    echo "Generating commit message..."
    commit_msg=$(meta-ai prompt "Generate a concise git commit message for these changes: $diff" --format text)
    echo "Suggested commit message: $commit_msg"
fi
```

### Python Scripts
```python
#!/usr/bin/env python3
import subprocess
import json

def ask_ai(question):
    result = subprocess.run([
        'meta-ai', 'prompt', question, '--format', 'json'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        response = json.loads(result.stdout)
        return response['message']
    else:
        return f"Error: {result.stderr}"

# Usage
answer = ask_ai("What is machine learning?")
print(answer)
```

The Meta AI CLI tool provides a powerful and flexible way to interact with Meta AI from the command line, suitable for both interactive use and automation scripts.