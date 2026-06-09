# NSI Normalizer

ML-based module for automatic normalization of NSI (Normative Reference Information) records.

## Features

- **Data cleaning** — Unicode normalization, whitespace, abbreviations, OKVED code formatting
- **Deduplication** — ML classifier (GradientBoosting) + string metrics (rapidfuzz) + optional embeddings
- **Canonicalization** — unified format for OKVED-2 and FSTEC BDU records
- **REST API** — FastAPI with async job processing via Celery
- **LLM fallback** — Claude API for uncertain deduplication cases

## Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

API available at http://localhost:8000  
Swagger UI at http://localhost:8000/docs  
Celery Flower at http://localhost:5555

## Development

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pre-commit install
pytest
```

## Architecture

```
[Client] → FastAPI → Celery Worker → ML Pipeline → PostgreSQL
                  ↑                               ↑
               Redis (broker)              pgvector (embeddings)
```

## Project Structure

```
src/nsi_normalizer/
├── api/          # FastAPI routers
├── core/         # Parsers, cleaning, normalization rules
├── ml/           # Deduplication ML pipeline
├── schemas/      # Pydantic V2 models
├── db/           # SQLAlchemy ORM + session
└── workers/      # Celery tasks
```
