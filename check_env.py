import os
import sys
from pathlib import Path

def find_env_files():
    """Find all .env files in the project"""
    root_dir = Path('.')
    env_files = list(root_dir.glob("**/.env*"))
    return [str(f) for f in env_files if not f.name.startswith('.env.')]

def check_env_vars():
    """Check if important environment variables are set"""
    env_vars = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "Not set"),
        "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "Not set"),
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID", "Not set"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY", "Not set"),
        "AWS_REGION": os.environ.get("AWS_REGION", "Not set"),
        "S3_ENDPOINT_URL": os.environ.get("S3_ENDPOINT_URL", "Not set"),
        "API_PORT": os.environ.get("API_PORT", "Not set")
    }
    
    # Mask sensitive information
    for key in ["OPENAI_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        if env_vars[key] != "Not set" and len(env_vars[key]) > 10:
            env_vars[key] = f"{env_vars[key][:5]}...{env_vars[key][-5:]}"
    
    return env_vars

if __name__ == "__main__":
    # Try to load dotenv if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded environment variables with python-dotenv")
    except ImportError:
        print("python-dotenv not installed - using environment variables as is")
    
    # Find .env files
    env_files = find_env_files()
    print("\nFound .env files:")
    for env_file in env_files:
        print(f"- {env_file}")
    
    # Check environment variables
    print("\nEnvironment variables:")
    env_vars = check_env_vars()
    for key, value in env_vars.items():
        print(f"- {key}: {value}")
