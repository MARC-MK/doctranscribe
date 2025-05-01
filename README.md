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

## Quick Start
```bash
# Start FastAPI, LocalStack S3, and (later) frontend
make dev
```

LocalStack spins up an S3 mock on `http://localhost:4566` so no AWS account is needed for local tests.

Navigate to `http://localhost:3000` for the front-end and `http://localhost:8000/docs` for the FastAPI Swagger UI.

## CI / CD
- GitHub Actions run linting, tests, and container image builds on every PR.
- Terraform modules deploy S3, KMS, ECS/Fargate, RDS, and Lambda in blue-green fashion.

## License
Apache-2.0 – see `LICENSE` for details. 