# DocTranscribe

Turn handwritten 8 × 11 lab sheets into tagged PDFs and clean Excel files—no manual typing.

## Monorepo Structure

```text
backend/   # FastAPI + SQLModel service
frontend/  # React 18 + Vite + Tailwind dashboard
infra/     # Terraform and IaC modules
scripts/   # Helper scripts
docs/      # Architecture diagrams and ADRs
```

## Requirements
- Docker & Docker Compose
- make (GNU or BSD)
- Git
- OpenAI API key (for handwriting recognition)

## Quick Start
```bash
# Set your OpenAI API key
./set_openai_key.sh YOUR_OPENAI_API_KEY

# Start FastAPI, LocalStack S3, and (later) frontend
make dev
```

LocalStack spins up an S3 mock on `http://localhost:4566` so no AWS account is needed for local tests.

Navigate to `http://localhost:3000` for the front-end and `http://localhost:8000/docs` for the FastAPI Swagger UI.

## 🐳 Docker Compose Networking Note

When running both frontend and backend in Docker Compose, always use the Docker Compose service name (e.g., `backend:8000`) for inter-container communication. Do NOT use `localhost` for backend API URLs in the frontend proxy config. Example for Vite:

```js
// frontend/vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://backend:8000', // Use service name, not localhost
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    }
  }
}
```

This ensures the frontend container can reach the backend container. For local (non-Docker) dev, you can use `localhost:8000`.

## Handwriting Recognition

DocTranscribe uses OpenAI's GPT-4.1 multimodal model to extract text from handwritten survey forms. The system converts PDFs to images, processes them with GPT-4.1, and generates structured XLSX files.

### OpenAI API Integration

The system uses OpenAI's GPT-4.1 with vision capabilities to recognize and extract handwritten text from your PDF documents. This API usage may incur charges on your OpenAI account.

To use the OpenAI integration:

1. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set your API key:
   ```bash
   ./set_openai_key.sh YOUR_OPENAI_API_KEY
   ```
3. Start the application and upload a document
4. Process the document using the API key (automatically loaded from .env file)

You can also provide an API key manually in the web interface if needed.

### Setup

1. Create a `.env` file with your OpenAI API key:
   ```bash 
   ./set_openai_key.sh YOUR_OPENAI_API_KEY
   ```
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Make sure Poppler is installed (for pdf2image library)

### Testing

Use the test script to process a sample PDF:

```bash
# Process a sample PDF
./scripts/test_handwriting_recognition.py path/to/sample.pdf

# Process and poll up to 10 times for results
./scripts/test_handwriting_recognition.py path/to/sample.pdf --poll 10
```

See `docs/environment_setup.md` for detailed setup instructions.

## CI / CD
- GitHub Actions run linting, tests, and container image builds on every PR.
- Terraform modules deploy S3, KMS, ECS/Fargate, RDS, and Lambda in blue-green fashion.

## License
Apache-2.0 – see `LICENSE` for details. 