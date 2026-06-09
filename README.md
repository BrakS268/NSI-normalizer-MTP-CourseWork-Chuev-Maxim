# NSI Normalizer

[![CI](https://github.com/BrakS268/NSI-normalizer-MTP-CourseWork-Chuev-Maxim/actions/workflows/ci.yml/badge.svg)](https://github.com/BrakS268/NSI-normalizer-MTP-CourseWork-Chuev-Maxim/actions/workflows/ci.yml)
[![SAST](https://github.com/BrakS268/NSI-normalizer-MTP-CourseWork-Chuev-Maxim/actions/workflows/sast.yml/badge.svg)](https://github.com/BrakS268/NSI-normalizer-MTP-CourseWork-Chuev-Maxim/actions/workflows/sast.yml)

ML-модуль автоматической нормализации записей нормативно-справочной информации (НСИ).

## Возможности

- **Очистка данных** — Unicode NFC, пробелы, аббревиатуры, правовые суффиксы (ООО/ОАО/ИП), нормализация кодов ОКВЭД
- **Дедупликация** — ML-классификатор (GradientBoosting) + строковые метрики (rapidfuzz) + блокировка O(n·W)
- **Нормализация** — единый формат для ОКВЭД-2 и ФСТЭК БДУ: коды, severity, даты, CVE ID, CVSS
- **REST API** — FastAPI с асинхронной обработкой задач через Celery
- **Безопасность** — defusedxml (XXE), bandit SAST, pip-audit CVE проверка

## Быстрый старт

```bash
cp .env.example .env
docker-compose up --build
```

| Сервис | URL |
|--------|-----|
| API + Swagger UI | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |

### Пример использования

```bash
# Загрузить справочник ОКВЭД
curl -X POST http://localhost:8000/api/v1/records/ingest \
  -H "X-API-Key: changeme" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "my_data",
    "record_type": "okved",
    "records": [
      {"code": "62.1", "name": "  разраб. прогр. обеспеч.  "},
      {"code": "62.01", "name": "Разработка программного обеспечения"}
    ]
  }'

# Нормализовать одну запись (синхронно)
curl -X POST http://localhost:8000/api/v1/records/normalize \
  -H "X-API-Key: changeme" \
  -H "Content-Type: application/json" \
  -d '{"source": "test", "record_type": "okved", "payload": {"code": "62.1", "name": "разраб. ПО"}}'

# Запустить дедупликацию (асинхронно)
curl -X POST http://localhost:8000/api/v1/records/deduplicate \
  -H "X-API-Key: changeme" \
  -H "Content-Type: application/json" \
  -d '{"record_type": "okved", "threshold": 0.65}'
```

## Разработка

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
pytest tests/ --no-cov
```

## Архитектура

```
[Клиент] ──► FastAPI (8000)
               │  ├─► POST /normalize  ──► FieldNormalizer (синхронно)
               │  └─► POST /deduplicate ─► Celery.delay()
               │                              │
               │                          Celery Worker
               │                              │
               │                          DeduplicationPipeline
               │                           ├─ Blocker (CodePrefix + SortedNeighborhood)
               │                           ├─ FeatureExtractor (8 признаков, rapidfuzz)
               │                           ├─ DedupClassifier (GradientBoosting / heuristic)
               │                           └─ GraphClustering (networkx connected components)
               │
            Redis ◄──────────────────────── Celery broker + result backend
            PostgreSQL + pgvector ◄───────── Records, clusters, jobs
```

## Структура проекта

```
src/nsi_normalizer/
├── api/            # FastAPI роутеры, схемы запросов/ответов, auth
├── core/
│   ├── parsers/    # ОКВЭД XML/CSV, ФСТЭК CSV/XML, generic JSON/CSV
│   ├── cleaning/   # CleaningPipeline, text_cleaner
│   └── normalization/  # field_normalizer, canonical_selector
├── ml/
│   ├── blocking/   # CodePrefixBlocker, SortedNeighborhoodBlocker
│   ├── features/   # FeatureExtractor (8 признаков)
│   ├── classification/  # DedupClassifier (GBM + hard rules)
│   ├── training/   # Trainer: load_labeled_pairs, fit, CV metrics
│   └── pipeline.py # Оркестрация 4 этапов, DeduplicationReport
├── schemas/        # Pydantic V2: RawRecord, NormalizedRecord, OkvedRecord, FstecRecord
├── db/             # SQLAlchemy ORM, async session, Alembic migrations
├── workers/        # Celery app + tasks
└── config.py       # Pydantic Settings (env vars)

tests/
├── unit/           # 140 тестов без внешних зависимостей
├── integration/    # 14 API тестов с TestClient
└── ml/fixtures/    # Размеченные пары для обучения классификатора

data/samples/       # Примеры: okved_sample.csv, okved_dirty.csv, fstec_sample.csv
docs/               # architecture.md (Mermaid), api.md, ml-pipeline.md
```

## Документация

- [Архитектура и диаграммы](docs/architecture.md)
- [API Reference](docs/api.md)
- [ML Pipeline](docs/ml-pipeline.md)

## Тестирование

```bash
pytest tests/ --no-cov          # все тесты
pytest tests/unit/              # только unit
pytest tests/integration/       # только интеграционные
```

**154 тестов, все зелёные.**

## Безопасность

```bash
# SAST (статический анализ)
python -m bandit -r src/ --severity-level medium --format screen

# Проверка зависимостей на CVE
pip-audit --local
```
