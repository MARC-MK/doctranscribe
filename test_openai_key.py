#!/usr/bin/env python3
"""
Test script for verifying OpenAI API key functionality
This specifically tests project-specific keys (sk-proj-...)
"""
import os
import sys
from openai import OpenAI, AsyncOpenAI

# Print OpenAI client version for debugging
import openai
print(f"OpenAI Python library version: {openai.__version__}")

# Get API key from environment or command line
api_key = os.environ.get("OPENAI_API_KEY")
if len(sys.argv) > 1:
    api_key = sys.argv[1]

if not api_key:
    print("Please provide an API key as an argument or set OPENAI_API_KEY environment variable")
    sys.exit(1)

print(f"Testing API key: {api_key[:8]}...{api_key[-4:]}")

# Use the specific model version
model = "gpt-4.1-2025-04-14"
print(f"Using model: {model}")

# Try using synchronous client
print("\nTesting synchronous client...")
try:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hello, this is a test."}],
        max_tokens=10
    )
    print("✅ Synchronous client test PASSED")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ Synchronous client test FAILED: {e}")

# Try using asynchronous client (used in pdf_service.py)
print("\nTesting asynchronous client (as used in the application)...")
import asyncio

async def test_async_client():
    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, this is an async test."}],
            max_tokens=10
        )
        print("✅ Asynchronous client test PASSED")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Asynchronous client test FAILED: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_async_client()) 