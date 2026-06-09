FROM python:3.11-slim AS builder

WORKDIR /build

RUN pip install hatchling

COPY pyproject.toml .
COPY src/ src/

RUN pip wheel --no-cache-dir --wheel-dir /wheels .


FROM python:3.11-slim AS runtime

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links /wheels nsi-normalizer && \
    rm -rf /wheels

COPY migrations/ migrations/
COPY alembic.ini .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "nsi_normalizer.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
