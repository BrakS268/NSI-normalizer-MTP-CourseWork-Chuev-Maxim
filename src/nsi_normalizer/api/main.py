from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nsi_normalizer.api.routers import health, jobs, records, train

app = FastAPI(
    title="NSI Normalizer",
    description="ML-based module for automatic normalization of NSI reference data",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(records.router, prefix="/api/v1/records", tags=["records"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(train.router, prefix="/api/v1/train", tags=["train"])
