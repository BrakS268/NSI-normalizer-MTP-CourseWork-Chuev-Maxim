# ML Deduplication Pipeline

## Overview

Пайплайн дедупликации состоит из 4 последовательных этапов.  
Цель — найти дублирующиеся записи в справочнике и выбрать каноническую.

## Stage 1: Blocking

**Проблема:** Попарное сравнение всех записей — O(n²). При 10 000 записях это 50 млн пар.

**Решение:** Блокировка — разбить записи на группы, сравнивать только внутри группы.

| Blocker | Ключ группировки | Применение |
|---------|-----------------|-----------|
| `CodePrefixBlocker` | Первые 2 цифры кода ОКВЭД | `62.*` отдельно от `47.*` |
| `SortedNeighborhoodBlocker` | Первые 4 символа очищенного названия | Скользящее окно W=5 |

`CompositeBlocker` объединяет оба метода (union), максимизируя recall.

**Reduction Ratio:** доля пар пропущенных vs брутфорс. Типично 80–95%.

## Stage 2: Feature Extraction

Для каждой кандидатной пары вычисляются 8 признаков:

| Признак | Библиотека | Описание |
|---------|-----------|---------|
| `jaro_winkler` | rapidfuzz | Сходство строк с бонусом за общий префикс |
| `token_sort_ratio` | rapidfuzz | Сортировка токенов перед сравнением |
| `token_set_ratio` | rapidfuzz | Пересечение множеств токенов |
| `levenshtein_norm` | rapidfuzz | Нормализованное расстояние Левенштейна |
| `code_exact_match` | — | 1.0 если коды полностью совпадают |
| `code_prefix_2_match` | — | 1.0 если первые 2 цифры кода совпадают |
| `description_jaccard` | — | Jaccard по множеству слов описания |
| `name_length_diff` | — | Нормализованная разница длин названий |

## Stage 3: Classification

**Жёсткие правила** (без ML, мгновенно):
- `jaro_winkler ≥ 0.97` И `code_exact_match = 1.0` → confidence = 0.99 (дубликат)
- `jaro_winkler ≤ 0.30` И `code_prefix ≠` → confidence = 0.01 (не дубликат)

**ML классификатор** для неоднозначных случаев:
- `GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.05)`
- Обучается на размеченных парах (`tests/ml/fixtures/okved_pairs_labeled.csv`)
- Выдаёт вероятность дубликата `[0..1]`
- Порог по умолчанию: `threshold=0.65`

**Fallback** (модель не обучена):
```
confidence = jw×0.4 + token_sort×0.3 + token_set×0.2 + code_exact×0.1
```

## Stage 4: Clustering

Дублирующиеся пары → рёбра в графе → **connected components** (networkx).

Каждая компонента = кластер дубликатов.

**Выбор канонической записи** (`elect_canonical`):

```
score = source_weight×0.4 + completeness×0.35 + name_length×0.15 + desc_length×0.10
```

| Источник | Вес |
|---------|-----|
| `okved2_fns` (ФНС) | 1.0 |
| `fstec_bdu_xml` | 1.0 |
| `fstec_bdu_csv` | 0.9 |
| `okved2_csv` | 0.85 |
| `generic_*` | 0.5–0.6 |

## Training

Для обучения классификатора на своих данных:

```python
from nsi_normalizer.ml.training.trainer import train

metrics = train("my_labeled_pairs.csv", model_path=Path("models/dedup_classifier.joblib"))
print(metrics)  # {"f1_mean": 0.92, "f1_std": 0.03, "n_samples": 500}
```

Формат CSV размеченных пар:
```
left_code,left_name,left_description,right_code,right_name,right_description,label
62.01,Разработка ПО,,62.01,разраб. прогр. обеспеч.,,1
62.01,Разработка ПО,,47.91,Торговля через интернет,,0
```
