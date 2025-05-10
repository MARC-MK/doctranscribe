# Environment File Fix Instructions

I've identified several issues with the environment configuration in your project:

## Issues Found

1. **Multiple inconsistent .env files**:
   - Root `.env` sets API_PORT=8082
   - `.env.new` sets API_PORT=8080 and OPENAI_MODEL=gpt-4o
   - docker-compose.override.yml sets OPENAI_MODEL=gpt-4.1

2. **Broken API key in docker-compose.override.yml**:
   - The OPENAI_API_KEY in docker-compose.override.yml appears to be accidentally split across multiple lines

3. **Port mismatch**:
   - The API port in the main .env file (8082) doesn't match the port exposed in docker-compose.yml (8080)

4. **Separate backend/.env file**:
   - backend/.env file only has S3_ENDPOINT_URL, but the application's config.py is looking for a .env file in the project root

## Solution

1. Create a consolidated `.env` file in the project root with these settings:

```
# DocTranscribe Environment Variables

# OpenAI API Key
OPENAI_API_KEY=YOUR_API_KEY_HERE

# API Configuration
API_PORT=8080

# AWS Configuration
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY_HERE
AWS_REGION=us-east-1
S3_ENDPOINT_URL=http://localhost:4566

# Model Configuration
OPENAI_MODEL=gpt-4.1
```

2. Fix the docker-compose.override.yml file by ensuring the OPENAI_API_KEY is on a single line

3. Remove or rename the other .env files to avoid confusion (.env.new, .env.fixed)

4. If you need a separate backend/.env for development outside Docker, ensure it has all the same variables as the root .env

These changes will ensure that:
- Docker and local development use the same environment variables
- The API port is consistent (8080)
- The OPENAI_MODEL is consistently set to gpt-4.1 (matching docker-compose.yml)
- Environment variable loading works properly for both Docker and local development 