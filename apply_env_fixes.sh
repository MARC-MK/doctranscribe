#!/bin/bash
# Script to apply all environment file fixes

set -e  # Exit on any error

echo "Applying environment file fixes..."

# Create a new .env file with the correct settings
cat > .env << 'EOL'
# DocTranscribe Environment Variables

# OpenAI API Key
OPENAI_API_KEY=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

# API Configuration
API_PORT=8080

# AWS Configuration
AWS_ACCESS_KEY_ID=AKIAQG5ED7HVSJZV5UK7
AWS_SECRET_ACCESS_KEY=2C9B9KKIZ5Qeddi8SpeUOi6XnB4K51XdEOGIzyN
AWS_REGION=us-east-1
S3_ENDPOINT_URL=http://localhost:4566

# Model Configuration
OPENAI_MODEL=gpt-4.1-2025-04-14
EOL

echo "Created new .env file"

# Copy to backend directory for local development
cp .env backend/.env
echo "Copied .env to backend/.env"

# Clean up extra .env files
echo "Cleaning up extra .env files..."
rm -f .env.fixed .env.updated .env.new .env.env.bak backend/.env.env.bak 2>/dev/null

echo "Environment fixes applied successfully!"
echo "Run 'python check_env.py' to verify the changes" 