#!/usr/bin/env python3
"""
Direct HTTP test for OpenAI API key functionality
This bypasses the OpenAI client library to test if the issue is with the key or the library
"""
import os
import sys
import json
import httpx
import asyncio

# Get API key from environment or command line
api_key = os.environ.get("OPENAI_API_KEY")
if len(sys.argv) > 1:
    api_key = sys.argv[1]

if not api_key:
    print("Please provide an API key as an argument or set OPENAI_API_KEY environment variable")
    sys.exit(1)

print(f"Testing API key directly via HTTP: {api_key[:8]}...{api_key[-4:]}")

async def test_direct_api_call():
    # Direct API call to models endpoint (simpler than completions)
    url = "https://api.openai.com/v1/models"
    
    # With project-specific API key
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Organization": os.environ.get("OPENAI_ORG_ID", ""),  # Optional
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print("\nTesting direct HTTP request to /v1/models endpoint...")
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                print("✅ Direct API test PASSED")
                models = response.json()
                print(f"Found {len(models['data'])} models")
                print(f"First few models: {[m['id'] for m in models['data'][:3]]}")
                return True
            else:
                print(f"❌ Direct API test FAILED: Status {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Direct API test FAILED with exception: {e}")
        return False

# Test chat completions directly
async def test_direct_chat_completion():
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Organization": os.environ.get("OPENAI_ORG_ID", ""),  # Optional
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello, this is a direct HTTP test."}],
        "max_tokens": 10
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print("\nTesting direct HTTP request to /v1/chat/completions endpoint...")
            response = await client.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                print("✅ Direct chat completion test PASSED")
                result = response.json()
                print(f"Response: {result['choices'][0]['message']['content']}")
                return True
            else:
                print(f"❌ Direct chat completion test FAILED: Status {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Direct chat completion test FAILED with exception: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_direct_api_call())
    asyncio.run(test_direct_chat_completion()) 