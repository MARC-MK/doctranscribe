#!/usr/bin/env python
"""
Script to fix the API key in the .env file by removing any line breaks.
"""

import os
import re

# Read the current .env file
with open(".env", "r") as f:
    env_content = f.read()

# Find the OpenAI API key line(s)
openai_key_pattern = r"OPENAI_API_KEY=(.*?)(?:\n[^O]|\n$|$)"
match = re.search(openai_key_pattern, env_content, re.DOTALL)

if match:
    # Get the API key with potential line breaks
    api_key_with_breaks = match.group(1)
    
    # Clean the API key by removing all whitespace and line breaks
    cleaned_api_key = re.sub(r'\s+', '', api_key_with_breaks)
    
    # Replace the old API key definition with the cleaned version
    fixed_env_content = re.sub(
        openai_key_pattern,
        f"OPENAI_API_KEY={cleaned_api_key}",
        env_content,
        flags=re.DOTALL
    )
    
    # Write the fixed content to a new .env.fixed file
    with open(".env.fixed", "w") as f:
        f.write(fixed_env_content)
    
    print(f"Fixed .env file written to .env.fixed")
    print(f"Original API key length: {len(api_key_with_breaks)}")
    print(f"Cleaned API key length: {len(cleaned_api_key)}")
    print(f"First 5 characters: {cleaned_api_key[:5]}...")
    print(f"Last 5 characters: ...{cleaned_api_key[-5:]}")
else:
    print("Could not find OPENAI_API_KEY in .env file") 