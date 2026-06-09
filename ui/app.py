"""NSI Normalizer — Streamlit UI."""

from __future__ import annotations

import io
import json
import time

import httpx
import pandas as pd
import streamlit as st

API_BASE = "http://localhost:8000/api/v1"
API_KEY = "changeme"
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(
    page_title="NSI Normalizer",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
.metric-card {
    background: #f0f2f6;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-card .value { font-size: 2rem; font-weight: 700; color: #1f77b4; }
.metric-card .label { font-size: 0.85rem; color: #555; margin-top: 4px; }
.stAlert { border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/database.png", width=64)
    st.title("NSI Normalizer")
    st.caption("Автоматическая нормализация справочников НСИ")
    st.divider()

    try:
        r = httpx.get(f"{API_BASE}/health/live", timeout=2)
        if r.status_code == 200:
            st.success("🟢 API онлайн")
            v = r.json().get("version", "")
            st.caption(f"Версия: {v}")
        else:
            st.error("🔴 API недоступен")
    except Exception:
        st.error("🔴 API недоступен")
        st.info("Запустите `docker-compose up`")

    st.divider()
    st.markdown("**Технологии:**")
    st.markdown("🐍 FastAPI + Celery")
    st.markdown("🤖 GradientBoosting ML")
    st.markdown("📊 rapidfuzz + networkx")
    st.markdown("🔒 defusedxml + bandit")
    st.divider()
    st.markdown(
        "**[GitHub](https://github.com/BrakS268/NSI-normalizer-MTP-CourseWork-Chuev-Maxim)**"
    )


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🚀 Обработка справочника",
        "✨ Нормализация записи",
        "🎓 Обучение модели",
        "📖 О проекте",
    ]
)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Полная обработка
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("🚀 Полная обработка справочника")
    st.markdown(
        "Загрузите CSV с «грязными» данными — "
        "система очистит, нормализует и уберёт дубли за один шаг."
    )

    col_upload, col_settings = st.columns([3, 1])

    with col_upload:
        uploaded = st.file_uploader(
            "Загрузить CSV (колонки: code, name, description — опционально)",
            type=["csv"],
            key="process_upload",
        )

    with col_settings:
        rec_type = st.selectbox("Тип справочника", ["okved", "fstec"], key="proc_type")
        source = st.text_input("Источник", value="upload", key="proc_source")

    with st.expander("⚙️ Дополнительные настройки"):
        threshold = st.slider(
            "Порог дедупликации",
            0.5,
            0.95,
            0.65,
            0.05,
            key="proc_thresh",
            help=(
                "Минимальная уверенность модели для признания записей дублями. "
                "По умолчанию 0.65 — оптимально для обученной модели."
            ),
        )

    # Load data
    if uploaded:
        try:
            # dtype=str prevents pandas from parsing OKVED codes as float (45.20 → 45.2 → 45.02)
            df_input = pd.read_csv(uploaded, dtype=str)
        except Exception:
            uploaded.seek(0)
            df_input = pd.read_csv(uploaded, dtype=str, on_bad_lines="skip")
            st.warning(
                "⚠️ Некоторые строки пропущены из-за ошибок формата CSV "
                "(возможно, незакавыченные запятые в названиях)"
            )
        # Strip whitespace from all string columns
        df_input = df_input.apply(lambda col: col.str.strip() if col.dtype == object else col)
        # Rename columns to API-expected field names (handles Russian headers and FSTEC exports)
        df_input = df_input.rename(
            columns={
                # OKVED / universal
                "Код": "code",
                "Каноническое название": "name",
                "Уверенность": "confidence",
                # FSTEC BDU Russian column names
                "Идентификатор": "bdu_id",
                "Наименование": "name",
                "Описание": "description",
                "Уровень опасности": "severity",
                "Идентификатор CVE": "cve_ids_raw",
                "Оценка CVSS": "cvss_score_raw",
                "Дата публикации": "published_at_raw",
                "Дата обновления": "updated_at_raw",
            }
        )
        st.success(f"✅ Загружено {len(df_input)} записей из файла")
    else:
        df_input = pd.DataFrame(
            [
                {"code": "62.01", "name": "Разработка компьютерного программного обеспечения"},
                {"code": "62.01", "name": "разраб. компьютерного программного обеспечения"},
                {"code": "62.1", "name": "разраб. компьютерного ПО"},
                {"code": "62.01", "name": "РАЗРАБОТКА КОМПЬЮТЕРНОГО ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ"},
                {"code": "62.02", "name": "деят. консультативная в обл. компьютерных технологий"},
                {"code": "62.02", "name": "деят. консультативная в обл. компьютерных технологий"},
                {"code": "47.91", "name": "Торговля розничная через интернет"},
                {"code": "47.91", "name": "торговля розн. через инт."},
                {"code": "47.91", "name": "ТОРГОВЛЯ РОЗНИЧНАЯ ЧЕРЕЗ ИНТЕРНЕТ"},
                {
                    "code": "63.11",
                    "name": "Деятельность по обработке данных и размещению информации",
                },
                {"code": "63.11", "name": "деят. по обработке данных и размещению информации"},
                {"code": "41.20", "name": "Строительство жилых и нежилых зданий"},
                {"code": "41.20", "name": "стр-во жилых и нежилых зданий"},
                {"code": "85.11", "name": "Образование дошкольное"},
                {"code": "85.11", "name": "ОБРАЗОВАНИЕ ДОШКОЛЬНОЕ"},
                {
                    "code": "72.19",
                    "name": "Научные исследования и разраб. в области технических наук",
                },
                {"code": "72.19", "name": "науч. исслед. и разраб. в обл. техн. наук"},
                {"code": "49.10", "name": "Перевозки железнодорожные пассажирские"},
                {"code": "49.10", "name": "перевозки ж.-д. пассажирские"},
                {"code": "69.10", "name": "Деятельность в области права"},
            ]
        )
        st.info(
            f"📋 Используется встроенный пример: {len(df_input)} записей с дублями и аббревиатурами"
        )

    with st.expander("👁️ Входные данные"):
        st.dataframe(df_input, use_container_width=True, hide_index=True)

    if st.button("🚀 Обработать", type="primary", use_container_width=True):
        records = df_input.fillna("").to_dict("records")

        with st.spinner("Очистка, нормализация и дедупликация..."):
            try:
                r = httpx.post(
                    f"{API_BASE}/records/process",
                    headers=HEADERS,
                    json={
                        "source": source,
                        "record_type": rec_type,
                        "threshold": threshold,
                        "records": records,
                    },
                    timeout=60,
                )
                if r.status_code != 200:
                    st.error(f"Ошибка {r.status_code}: {r.text}")
                    st.stop()
                result = r.json()
            except Exception as e:
                st.error(f"Не удалось подключиться к API: {e}")
                st.stop()

        # ── Метрики ───────────────────────────────────────────────────────────
        st.success("✅ Обработка завершена!")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📥 Входных записей", result["total_input"])
        c2.metric("📤 После обработки", result["total_output"])
        c3.metric("🗑️ Дублей убрано", result["duplicates_removed"])
        total_in = result["total_input"]
        dedup_pct = result["duplicates_removed"] / total_in if total_in else 0
        c4.metric("📉 Убрано дублей", f"{dedup_pct:.0%}")

        # ── Результирующая таблица ─────────────────────────────────────────────
        st.subheader("📋 Нормализованный справочник")
        rows = []
        for rec in result["records"]:
            name = rec.get("canonical_name", "")
            name = name[:1].upper() + name[1:] if name else name
            payload = rec.get("normalized_payload") or {}
            row = {"Код": rec.get("canonical_code") or "—", "Каноническое название": name}
            if payload.get("description"):
                row["Описание"] = payload["description"]
            if payload.get("severity"):
                row["Уровень опасности"] = payload["severity"]
            if payload.get("published_at"):
                row["Дата публикации"] = payload["published_at"]
            if payload.get("section"):
                row["Раздел"] = payload["section"]
            if payload.get("parent_code"):
                row["Родительский код"] = payload["parent_code"]
            row["Уверенность"] = f"{rec.get('confidence', 0):.0%}"
            rows.append(row)
        df_result = pd.DataFrame(rows)
        st.dataframe(df_result, use_container_width=True, hide_index=True, height=400)

        # ── Скачать результат ─────────────────────────────────────────────────
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_out = df_result.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Скачать с уверенностью",
                csv_out,
                "normalized_result.csv",
                "text/csv",
            )
        with col_dl2:
            csv_simple = df_result.drop(columns=["Уверенность"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Скачать без уверенности",
                csv_simple,
                "normalized_result_clean.csv",
                "text/csv",
            )

        with st.expander("🔍 Полный JSON ответа"):
            st.json(result)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Нормализация одной записи
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("✨ Нормализация одной записи")
    st.markdown("Введите «грязную» запись — система вернёт очищенный канонический вид.")

    col1, col2 = st.columns(2)
    with col1:
        n_type = st.selectbox("Тип справочника", ["okved", "fstec"], key="norm_type")
        n_source = st.text_input("Источник", value="demo", key="norm_source")
    with col2:
        if n_type == "okved":
            n_code = st.text_input("Код ОКВЭД", value="62.1")
            n_name = st.text_input("Наименование", value="разраб. компьютерного ПО")
            payload = {"code": n_code, "name": n_name}
        else:
            n_id = st.text_input("ID уязвимости", value="BDU:2024-01234")
            n_name = st.text_input("Наименование", value="Уязвимость в OpenSSL")
            n_sev = st.selectbox("Критичность", ["Высокий", "Средний", "Низкий", "Критический"])
            payload = {"id": n_id, "name": n_name, "severity": n_sev}

    if st.button("✨ Нормализовать", type="primary"):
        with st.spinner("Обработка..."):
            try:
                r = httpx.post(
                    f"{API_BASE}/records/normalize",
                    headers=HEADERS,
                    json={"source": n_source, "record_type": n_type, "payload": payload},
                    timeout=10,
                )
                if r.status_code == 200:
                    data = r.json()["result"]
                    st.success("✅ Готово!")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Канонический код", data.get("canonical_code") or "—")
                    c2.metric("Уверенность", f"{data.get('confidence', 0):.0%}")
                    c3.metric("Тип", data.get("record_type", "—"))
                    st.markdown("**Каноническое наименование:**")
                    st.info(f"**{data.get('canonical_name', '—')}**")
                    with st.expander("Полный JSON"):
                        st.json(data)
                else:
                    st.error(f"Ошибка {r.status_code}: {r.text}")
            except Exception as e:
                st.error(f"Ошибка: {e}")

    st.divider()
    st.subheader("Примеры для теста")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Код": "62.1",
                    "Грязное название": "разраб. компьютерного ПО",
                    "Ожидаем": "разработка компьютерного ПО → код 62.01",
                },
                {
                    "Код": "47.91",
                    "Грязное название": "торговля розн. через инт.",
                    "Ожидаем": "торговля розничная через интернет",
                },
                {
                    "Код": "41.20",
                    "Грязное название": "стр-во жилых и нежилых зданий",
                    "Ожидаем": "строительство жилых и нежилых зданий",
                },
                {
                    "Код": "49.10",
                    "Грязное название": "перевозки ж.-д. пассажирские",
                    "Ожидаем": "перевозки железнодорожные пассажирские",
                },
                {
                    "Код": "62.02",
                    "Грязное название": "деят. консультативная в обл. компьютерных технологий",
                    "Ожидаем": "деятельность консультативная в области компьютерных технологий",
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — Обучение модели
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("🎓 Обучение классификатора дублей")
    st.markdown("""
    Загрузите CSV с размеченными парами — система обучит **GradientBoostingClassifier**
    и сохранит модель. После обучения все запросы `/process` будут использовать её.
    """)

    col1, col2 = st.columns([2, 1])
    with col1:
        train_file = st.file_uploader(
            "CSV с размеченными парами",
            type=["csv"],
            key="train_upload",
            help=(
                "Колонки: left_code, left_name, left_description, "
                "right_code, right_name, right_description, label (1=дубль, 0=не дубль)"
            ),
        )
    with col2:
        st.markdown("**Формат CSV:**")
        st.code(
            "left_code, left_name, left_description,\n"
            "right_code, right_name, right_description,\n"
            "label (1/0)",
            language="text",
        )

    if train_file:
        df_train = pd.read_csv(train_file)
        total = len(df_train)
        dupes = int(df_train["label"].sum()) if "label" in df_train.columns else 0
        st.info(
            f"📊 Загружено: **{total}** пар | дублей: **{dupes}** | не-дублей: **{total - dupes}**"
        )
        with st.expander("Предпросмотр данных"):
            st.dataframe(df_train.head(10), use_container_width=True, hide_index=True)

        if st.button("🎓 Обучить модель", type="primary"):
            with st.spinner("Обучение GradientBoosting (5-fold CV)..."):
                train_file.seek(0)
                try:
                    r = httpx.post(
                        f"{API_BASE}/train/",
                        headers=HEADERS,
                        files={"file": (train_file.name, train_file.read(), "text/csv")},
                        timeout=60,
                    )
                    if r.status_code == 200:
                        metrics = r.json()
                        st.success("✅ Модель обучена!")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Выборка", f"{metrics['n_samples']} пар")
                        c2.metric("F1 (средн.)", f"{metrics['f1_mean']:.1%}")
                        c3.metric("F1 (std)", f"±{metrics['f1_std']:.1%}")
                        st.info(f"💾 Модель сохранена: `{metrics['model_path']}`")
                    else:
                        st.error(f"Ошибка {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    else:
        st.markdown("---")
        st.markdown(
            "📁 Готовый файл для обучения: `data/training/combined_train_pairs.csv` "
            "(106 пар, F1=99.2%)"
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — О проекте
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("📖 О проекте")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
### Модуль автоматической нормализации НСИ

**Курсовая работа**
Дисциплина: «Методы и технологии программирования»
Вариант 17

---
### Что делает модуль

| Этап | Описание |
|------|----------|
| 🧹 Очистка | Unicode NFC, пробелы, аббревиатуры, регистр |
| 📐 Нормализация | Коды ОКВЭД, severity, даты, CVE ID |
| 🔍 Дедупликация | ML-классификатор + кластеризация |
| 📦 Унификация | Единая схема для ОКВЭД-2 и ФСТЭК БДУ |

---
### Поддерживаемые справочники
- **ОКВЭД-2** — коды видов экономической деятельности (ФНС)
- **ФСТЭК БДУ** — база данных угроз и уязвимостей
        """)

    with col2:
        st.markdown("""
### ML-пайплайн дедупликации

```
Входные записи (N штук)
        │
┌───────▼────────┐
│   Блокировка   │  CodePrefix + SortedNeighborhood
│   O(N·W)       │  W=5 (вместо O(N²))
└───────┬────────┘
        │ кандидаты
┌───────▼────────┐
│   8 признаков  │  Jaro-Winkler, token_sort,
│   rapidfuzz    │  token_set, Levenshtein,
└───────┬────────┘  code_exact, code_prefix...
        │
┌───────▼────────┐
│ GradientBoost  │  200 деревьев, 5-fold CV
│ F1 = 97.8%     │  или эвристика если не обучен
└───────┬────────┘
        │
┌───────▼────────┐
│  Кластеризация │  networkx connected components
│  + канонизация │  elect_canonical по скорингу
└───────┬────────┘
        │
   Нормализованные
   уникальные записи
```
        """)

    st.divider()
    col3, col4, col5 = st.columns(3)
    col3.metric("Тестов", "154", "все зелёные ✅")
    col4.metric("F1 классификатора", "97.8%", "после обучения")
    col5.metric("Коммитов", "23+", "semantic commits")

    st.markdown(
        "**🔗 [GitHub репозиторий](https://github.com/BrakS268/NSI-normalizer-MTP-CourseWork-Chuev-Maxim)**"
    )
