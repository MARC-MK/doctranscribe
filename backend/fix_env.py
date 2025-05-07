#!/usr/bin/env python
"""
Fix .env file OpenAI API key by combining the multiline key into a single line
"""

def fix_env_file():
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    while i < len(lines):
        if lines[i].startswith('OPENAI_API_KEY='):
            # Start collecting the API key
            key_line = lines[i].strip()
            i += 1
            # Keep adding lines until we find a line that starts with another variable
            while i < len(lines) and not any(lines[i].startswith(prefix) for prefix in ['S3_', 'AWS_', 'DB_']):
                key_line += lines[i].strip()
                i += 1
            new_lines.append(key_line + '\n')
        else:
            new_lines.append(lines[i])
            i += 1
    
    with open('.env', 'w') as f:
        f.writelines(new_lines)
    
    print("Fixed .env file - API key is now on a single line")

if __name__ == "__main__":
    fix_env_file() 