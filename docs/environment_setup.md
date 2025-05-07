# Environment Setup for DocTranscribe

## OpenAI GPT-4.1 Integration

The handwriting recognition feature uses OpenAI's GPT-4.1 multimodal model to extract text from handwritten surveys. Follow these steps to set it up:

### 1. Create a .env file

Create a `.env` file in the project root with the following configuration:

```
# AWS Configuration
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET=lab-sheets-private
S3_ENDPOINT_URL=http://localstack:4566

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1

# App Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 2. Obtain an OpenAI API Key

1. Sign up for an OpenAI account at [https://openai.com](https://openai.com)
2. Navigate to the API section and create a new API key
3. Replace `your_openai_api_key_here` in the `.env` file with your actual API key

### 3. Install Additional Dependencies

The backend requires additional Python packages for PDF processing and OpenAI integration:

```bash
cd backend
pip install -r requirements.txt
```

Make sure you have the following packages installed for PDF processing:
- pdf2image
- python-dotenv
- httpx

### 4. Install System Dependencies

The `pdf2image` library requires Poppler to be installed on your system:

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
apt-get install poppler-utils
```

**Windows:**
Download and install Poppler from [https://github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases)

### 5. Test the Setup

After setting up the environment, you can test if everything is working correctly:

```bash
# Start the backend
make dev-backend

# Check if the handwriting recognition endpoint is working
curl http://localhost:8000/handwriting/test
```

## Using the Handwriting Recognition Feature

1. Upload PDF files through the frontend UI
2. The backend will process each page using GPT-4.1
3. Results will be available in structured XLSX format

## Configuration Options

You can adjust the following settings in the `.env` file:

- `OPENAI_MODEL`: The OpenAI model to use (default: gpt-4.1)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)
- `ENVIRONMENT`: Application environment (development, production) 