#!/usr/bin/env python
"""
Script to fix the API key in the .env file by removing any line breaks.
"""

import os
import shutil
from pathlib import Path

def backup_env_file(env_path):
    """Create a backup of the .env file"""
    if env_path.exists():
        backup_path = env_path.with_suffix('.env.bak')
        shutil.copy(env_path, backup_path)
        print(f"Created backup of {env_path} at {backup_path}")
    
def fix_env_files():
    """Fix environment file inconsistencies"""
    # Paths to env files
    root_env = Path('.env')
    backend_env = Path('backend/.env')
    
    # Read existing .env file content if it exists
    existing_env_vars = {}
    if root_env.exists():
        with open(root_env, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_env_vars[key.strip()] = value.strip()
    
    # Create new consolidated .env file content
    new_env_content = """# DocTranscribe Environment Variables

# OpenAI API Key
OPENAI_API_KEY={api_key}

# API Configuration
API_PORT=8080

# AWS Configuration
AWS_ACCESS_KEY_ID={aws_key}
AWS_SECRET_ACCESS_KEY={aws_secret}
AWS_REGION={aws_region}
S3_ENDPOINT_URL=http://localhost:4566

# Model Configuration
OPENAI_MODEL=gpt-4.1
""".format(
        api_key=existing_env_vars.get('OPENAI_API_KEY', ''),
        aws_key=existing_env_vars.get('AWS_ACCESS_KEY_ID', ''),
        aws_secret=existing_env_vars.get('AWS_SECRET_ACCESS_KEY', ''),
        aws_region=existing_env_vars.get('AWS_REGION', 'us-east-1')
    )
    
    # Backup original files
    backup_env_file(root_env)
    backup_env_file(backend_env)
    
    # Write the new consolidated .env file
    with open('.env.fixed', 'w') as f:
        f.write(new_env_content)
    
    print("\nCreated new consolidated .env file at .env.fixed")
    print("Please review the file and rename it to .env if it looks correct.")
    print("\nTo apply the changes, run:")
    print("  cp .env.fixed .env")
    
    # Suggest docker-compose.override.yml fix
    docker_compose_override = Path('docker-compose.override.yml')
    if docker_compose_override.exists():
        print("\nYour docker-compose.override.yml file may contain a broken API key.")
        print("Please check the file and ensure the OPENAI_API_KEY is on a single line.")
    
    # Instructions for backend/.env
    print("\nYour backend/.env file should either be removed or updated to match the root .env file.")
    print("For local development outside Docker, you may need to copy the root .env to backend/.env")

if __name__ == "__main__":
    fix_env_files()
    print("\nDone! Please review the generated files before using them.") 