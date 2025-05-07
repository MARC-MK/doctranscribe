#!/usr/bin/env python
"""
Simple script to check how the API key is being read from the .env file.
"""
import os
import re
from pathlib import Path

# Method 1: Read the file directly
env_path = Path(".env")
if env_path.exists():
    with open(env_path, "r") as f:
        content = f.read()
        print("Raw .env file content:")
        print(content)
        
        # Look for the API key
        match = re.search(r"OPENAI_API_KEY=(.+?)(\n|$)", content, re.DOTALL)
        if match:
            key = match.group(1).strip()
            print(f"\nFound API key (raw): '{key[:10]}...{key[-5:]}' (length: {len(key)})")
        else:
            print("\nCould not find API key in .env file")

# Method 2: Using dotenv
print("\n--- Using python-dotenv ---")
try:
    import dotenv
    dotenv.load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY", "")
    print(f"API key from dotenv: '{api_key[:10]}...{api_key[-5:] if len(api_key) > 10 else ''}' (length: {len(api_key)})")
except Exception as e:
    print(f"Error with dotenv: {str(e)}")

# Method 3: Check all environment variables
print("\n--- All environment variables containing 'API' ---")
for key, value in os.environ.items():
    if "API" in key:
        print(f"{key}: '{value[:10]}...{value[-5:] if len(value) > 10 else ''}' (length: {len(value)})") 