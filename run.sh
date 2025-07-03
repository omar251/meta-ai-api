
#!/bin/bash

# Check if a prompt was provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <prompt>"
    exit 1
fi

# Assign the prompt to a variable
PROMPT="$1"

# Execute the command with the provided prompt
meta-ai prompt "$PROMPT" --format text | ~/Dev/python/tts/.venv/bin/tts -t -
