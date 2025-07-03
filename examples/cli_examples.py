#!/usr/bin/env python3
"""
Examples of using the Meta AI CLI tool programmatically.

This script demonstrates various ways to integrate the CLI tool
into other Python applications and scripts.
"""

import subprocess
import json
import sys
import os

# Add src to path for direct CLI access
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_cli_command(args, input_text=None):
    """
    Run a CLI command and return the result.
    
    Args:
        args: List of command arguments
        input_text: Optional input for interactive commands
        
    Returns:
        Tuple of (success, output, error)
    """
    try:
        # Try different CLI invocation methods (in order of preference)
        cli_commands = [
            ["meta-ai"] + args,
            ["python", "-m", "meta_ai_api"] + args,
            ["python", "-m", "meta_ai_api.cli"] + args,
            ["python", "src/meta_ai_api/cli.py"] + args
        ]
        
        for cmd in cli_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    input=input_text,
                    timeout=30
                )
                if result.returncode == 0:
                    return True, result.stdout.strip(), result.stderr.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return False, "", "No working CLI command found"
        
    except Exception as e:
        return False, "", str(e)

def example_basic_prompt():
    """Example: Basic prompt with different formats."""
    print("📝 Example 1: Basic Prompts")
    print("-" * 30)
    
    # Text format
    success, output, error = run_cli_command(
        ["prompt", "What is the capital of France?", "--format", "text"]
    )
    if success:
        print(f"Text format: {output}")
    else:
        print(f"Error: {error}")
    
    # JSON format
    success, output, error = run_cli_command(
        ["prompt", "What is 2+2?", "--format", "json"]
    )
    if success:
        try:
            data = json.loads(output)
            print(f"JSON format - Message: {data['message']}")
            print(f"JSON format - Sources: {len(data.get('sources', []))}")
        except json.JSONDecodeError:
            print(f"Invalid JSON: {output}")
    else:
        print(f"Error: {error}")

def example_streaming():
    """Example: Streaming responses."""
    print("\n🌊 Example 2: Streaming")
    print("-" * 30)
    
    success, output, error = run_cli_command(
        ["prompt", "Count from 1 to 5", "--stream", "--format", "text"]
    )
    if success:
        print(f"Streaming output: {output}")
    else:
        print(f"Error: {error}")

def example_conversation():
    """Example: Conversation management."""
    print("\n💬 Example 3: Conversation")
    print("-" * 30)
    
    # First message
    success, output, error = run_cli_command(
        ["prompt", "My name is Alice", "--format", "text"]
    )
    if success:
        print(f"First message: {output[:50]}...")
    
    # Follow-up message
    success, output, error = run_cli_command(
        ["prompt", "What is my name?", "--format", "text"]
    )
    if success:
        print(f"Follow-up: {output}")
    
    # New conversation
    success, output, error = run_cli_command(
        ["prompt", "What is my name?", "--new-conversation", "--format", "text"]
    )
    if success:
        print(f"New conversation: {output[:50]}...")

def example_config_management():
    """Example: Configuration management."""
    print("\n⚙️ Example 4: Configuration")
    print("-" * 30)
    
    # Show config path
    success, output, error = run_cli_command(["config", "path"])
    if success:
        print(f"Config path: {output}")
    
    # Show current config
    success, output, error = run_cli_command(["config", "show"])
    if success:
        if output:
            print(f"Current config: {output}")
        else:
            print("No configuration found")

def example_ai_assistant():
    """Example: AI assistant for code review."""
    print("\n🤖 Example 5: AI Code Assistant")
    print("-" * 30)
    
    # Example code to review
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
    """
    
    prompt = f"Review this Python code and suggest improvements:\n{code}"
    
    success, output, error = run_cli_command(
        ["prompt", prompt, "--format", "text"]
    )
    if success:
        print("Code review:")
        print(output[:200] + "..." if len(output) > 200 else output)
    else:
        print(f"Error: {error}")

def example_batch_processing():
    """Example: Batch processing multiple prompts."""
    print("\n📦 Example 6: Batch Processing")
    print("-" * 30)
    
    prompts = [
        "What is machine learning?",
        "Explain quantum computing",
        "What is blockchain?"
    ]
    
    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"Processing prompt {i}/{len(prompts)}...")
        success, output, error = run_cli_command(
            ["prompt", prompt, "--format", "json"]
        )
        if success:
            try:
                data = json.loads(output)
                results.append({
                    "prompt": prompt,
                    "response": data["message"][:100] + "...",
                    "sources": len(data.get("sources", []))
                })
            except json.JSONDecodeError:
                results.append({
                    "prompt": prompt,
                    "response": "Invalid JSON response",
                    "sources": 0
                })
        else:
            results.append({
                "prompt": prompt,
                "response": f"Error: {error}",
                "sources": 0
            })
    
    print("\nBatch results:")
    for result in results:
        print(f"- {result['prompt'][:30]}...")
        print(f"  Response: {result['response'][:50]}...")
        print(f"  Sources: {result['sources']}")

def example_direct_cli_usage():
    """Example: Using the CLI class directly."""
    print("\n🔧 Example 7: Direct CLI Usage")
    print("-" * 30)
    
    try:
        from meta_ai_api.cli import MetaAICLI
        
        cli = MetaAICLI()
        
        # Simulate command line arguments
        args = ["prompt", "Hello from direct CLI!", "--format", "text"]
        cli.run(args)
        
    except ImportError:
        print("Direct CLI import not available")
    except SystemExit:
        print("CLI executed successfully (SystemExit is normal)")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all examples."""
    print("🚀 Meta AI CLI Examples")
    print("=" * 50)
    print("This script demonstrates various ways to use the CLI tool.")
    print()
    
    try:
        example_basic_prompt()
        example_streaming()
        example_conversation()
        example_config_management()
        example_ai_assistant()
        example_batch_processing()
        example_direct_cli_usage()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed!")
        print("=" * 50)
        print("\nThese examples show how to integrate the Meta AI CLI")
        print("into your own scripts and applications.")
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")

if __name__ == "__main__":
    main()