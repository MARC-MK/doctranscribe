#!/bin/bash

# set_openai_key.sh - Set up the OpenAI API key for DocTranscribe

# Check if an API key was provided
if [ -z "$1" ]; then
    echo "Usage: ./set_openai_key.sh YOUR_OPENAI_API_KEY"
    echo "Please provide your OpenAI API key as an argument."
    exit 1
fi

API_KEY=$1

# Create or update .env file
if [ -f .env ]; then
    # Check if OPENAI_API_KEY already exists in .env
    if grep -q "OPENAI_API_KEY=" .env; then
        # Replace existing key
        sed -i.bak "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$API_KEY|" .env
        rm -f .env.bak 2>/dev/null
        echo "Updated OPENAI_API_KEY in .env file"
    else
        # Add key to existing file
        echo "OPENAI_API_KEY=$API_KEY" >> .env
        echo "Added OPENAI_API_KEY to .env file"
    fi
else
    # Create new .env file
    echo "OPENAI_API_KEY=$API_KEY" > .env
    echo "Created new .env file with OPENAI_API_KEY"
fi

# Make script executable
chmod +x set_openai_key.sh

# Provide next steps
echo ""
echo "✅ OpenAI API key has been set."
echo ""
echo "Next steps:"
echo "1. Start the application with 'docker-compose up'"
echo "2. Upload a PDF document at http://localhost:5173/upload"
echo "3. Process the document using your OpenAI API key"
echo ""
echo "Note: This will use OpenAI's GPT-4.1 with vision capabilities to analyze handwritten content."
echo "      API usage will incur charges on your OpenAI account based on their pricing." 