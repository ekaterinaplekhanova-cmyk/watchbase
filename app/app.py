import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from generator import generate_package, generate_texts_from_card
from utils import save_result

st.set_page_config(page_title="316.watch Content Generator", layout="wide")

st.title("Генератор контента для 316.watch")
st.markdown(
    "Введите артикул и бренд часов. Система подготовит карточку характеристик, "
    "описание модели и пост для Telegram через локальную модель Ollama."
)

with st.form("content_form"):
    col1, col2 = st.columns(2)
    with col1:
        articul = st.text_input(
            "Артикул",
            value=st.session_state.get("last_result", {}).get("articul", ""),
            placeholder="M2639W1A0U-0001",
        )
    with col2:
        brand = st.text_input(
            "Бренд",
            value=st.session_state.get("last_result", {}).get("brand", ""),
            placeholder="Tudor",
        )

    uploaded_image = st.file_uploader(
        "Или загрузите фото часов (поиск по изображению)",
        type=["jpg", "jpeg", "png", "webp"],
    )

    card_only = st.checkbox(
        "⚡ Только карточка (быстрый режим — без описания модели и Telegram)",
        value=False,
        help="В 3–4 раза быстрее. Генерирует только таблицу характеристик.",
    )

    submitted = st.form_submit_button("Сгенерировать пакет контента")

# Кнопка сброса кэша и истории генерации.
if st.button("🧹 Очистить кэш и историю"):
    for key in ("last_result", "last_card"):
        st.session_state.pop(key, None)
    # Удаляем также файловые кэши поиска, рендера и карточек.
    try:
        from generator import CARD_CACHE_PATH
        from search import RENDER_CACHE_PATH, SEARCH_CACHE_PATH

        for p in (SEARCH_CACHE_PATH, CARD_CACHE_PATH, RENDER_CACHE_PATH):
            if p.exists():
                p.unlink()
    except Exception as e:
        st.error(f"Не удалось удалить файловый кэш: {e}")
    st.success("История и файловые кэши очищены. Можно сгенерировать заново.")
    st.rerun()

image_path = None
if uploaded_image is not None:
    suffix = "." + uploaded_image.name.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_image.getvalue())
        image_path = tmp.name


def _render_card(result):
    """Отрисовывает таблицу карточки и информацию об источнике."""
    card = result.get("card", {})

    st.subheader("Таблица характеристик")
    if not card:
        st.warning("Карточка пустая — источник не вернул характеристик.")
        return

    characteristics = {
        "Артикул": card.get("articul", ""),
        "Бренд": card.get("brand", ""),
        "Название": card.get("name", ""),
        "Коллекция": card.get("collection", ""),
        "Механизм": card.get("mechanism", ""),
        "Калибр": card.get("caliber", ""),
        "Камни": card.get("jewels", ""),
        "Запас хода": card.get("power_reserve", ""),
        "Полуколебания": card.get("frequency", ""),
        "Автоподзавод": card.get("auto_winding", ""),
        "Доп. функции": ", ".join(card.get("additional_functions", [])) if isinstance(card.get("additional_functions"), list) else card.get("additional_functions", ""),
        "Материал корпуса": card.get("case_material", ""),
        "Материал браслета/ремня": card.get("bracelet_strap_material", ""),
        "Стекло": card.get("glass", ""),
        "Цвет циферблата": card.get("dial_color", ""),
        "Водозащита": card.get("water_resistance", ""),
        "Диаметр": card.get("diameter", ""),
        "Толщина": card.get("thickness", ""),
        "Страна": card.get("country", ""),
        "URL источника": result.get("source_url", ""),
        "Уровень доверия источника": result.get("source_tier", ""),
        "Статус проверки": result.get("confidence_status", ""),
    }
    st.table(characteristics)

    confidence = result.get("confidence_status", "")
    tier = result.get("source_tier", "")
    if confidence == "manual_check_required":
        st.warning("Не удалось найти достоверные характеристики. Требуется ручная проверка.")
    elif confidence == "partial":
        if tier in ("official", "authorized"):
            st.info("Данные получены из официального или авторизованного источника.")
        elif tier == "reputable":
            st.info("Данные получены из авторитетного источника. Рекомендуется проверить ключевые параметры перед публикацией.")
        else:
            st.info("Данные получены из открытых источников. Рекомендуется проверить ключевые параметры перед публикацией.")

    if result.get("image_search_error"):
        st.error(f"Ошибка поиска по изображению: {result['image_search_error']}")

    # Показываем, какие поля были дополнены из локального справочника калибров.
    ref_fields = card.get("reference_supplemented")
    if ref_fields:
        labels = {
            "jewels": "камни",
            "frequency": "полуколебания",
            "power_reserve": "запас хода",
        }
        st.caption(
            f"⚠️ {', '.join(labels.get(f, f) for f in ref_fields)} подставлены из справочника по калибру «{card.get('caliber', '')}», "
            "поскольку источник по модели не содержит их."
        )


def _render_texts(result):
    """Отрисовывает описание модели и Telegram-пост, если они есть."""
    description = result.get("description_model", "")
    telegram = result.get("telegram_post", "")
    has_text = bool(description) or bool(telegram)
    if not has_text:
        return

    st.divider()
    st.subheader("Готовые тексты")
    if description:
        with st.expander("Описание модели", expanded=True):
            st.markdown(description)
            st.code(description, language="text")
    if telegram:
        with st.expander("Пост для Telegram", expanded=True):
            st.markdown(telegram)
            st.code(telegram, language="text")


if submitted:
    if not articul.strip() or not brand.strip():
        st.error("Заполните артикул и бренд.")
        st.stop()

    articul_clean = articul.strip().upper()
    brand_clean = brand.strip()

    # Если пользователь сменил артикул/бренд — сбрасываем старый результат,
    # чтобы не показывать карточку от другой модели.
    prev = st.session_state.get("last_result", {})
    if (
        prev.get("articul", "").upper() != articul_clean
        or prev.get("brand", "").lower() != brand_clean.lower()
    ):
        st.session_state.pop("last_result", None)
        st.session_state.pop("last_card", None)

    total_start = time.time()
    status = st.status("Запуск генерации...", expanded=True)

    try:
        with status:
            st.write("🔍 Поиск характеристик в источниках...")
            step_start = time.time()
            result = generate_package(
                articul_clean, brand_clean, image_path=image_path, card_only=card_only
            )
            search_seconds = time.time() - step_start
            st.write(f"✅ Поиск и LLM-обработка завершены за {search_seconds:.1f} сек")

            st.write("💾 Сохранение результатов...")
            out_dir = save_result(articul_clean, brand_clean, result)
            st.write(f"✅ Сохранено в {out_dir}")

        total_seconds = time.time() - total_start
        mode_label = "Только карточка" if card_only else "Полный пакет"
        st.success(f"{mode_label} готов. Общее время: {total_seconds:.1f} сек")
        if card_only:
            st.info("Описание модели и Telegram не сгенерированы — включён быстрый режим.")

        # Сохраняем результат в session_state для возможной догенерации
        st.session_state["last_card"] = result.get("card", {})
        st.session_state["last_result"] = result

    except Exception as e:
        status.update(label="Ошибка генерации", state="error", expanded=True)
        st.error(f"Ошибка генерации: {e}")
        import traceback
        st.code(traceback.format_exc(), language="text")
        st.stop()

# ---------------------------------------------------------------------------
# Читаем актуальное состояние из session_state ПОСЛЕ возможной генерации.
# ---------------------------------------------------------------------------
last_result = st.session_state.get("last_result")
last_card = st.session_state.get("last_card")

# ---------------------------------------------------------------------------
# Догенерация описания модели и Telegram-поста по уже созданной карточке
# ---------------------------------------------------------------------------
needs_texts = (
    last_card
    and last_result
    and last_result.get("card_only")
    and not last_result.get("description_model")
    and not last_result.get("telegram_post")
)
if needs_texts:
    st.divider()
    st.subheader("Догенерация текстов")
    st.write("Карточка уже готова. Можно сгенерировать описание модели и пост для Telegram без повторного поиска в интернете.")
    if st.button("📝 Сгенерировать описание и Telegram", type="primary"):
        try:
            with st.spinner("Генерация описания и Telegram-поста, это может занять 1–3 минуты..."):
                new_texts = generate_texts_from_card(last_card)
                last_result["description_model"] = new_texts.get("description_model", "")
                last_result["telegram_post"] = new_texts.get("telegram_post", "")
                last_result["card_only"] = False
                save_result(
                    last_result["articul"],
                    last_result["brand"],
                    last_result,
                )

            st.session_state["last_result"] = last_result
            st.session_state["last_card"] = last_result.get("card", last_card)
            st.success("Описание модели и Telegram-пост сгенерированы и сохранены.")
        except Exception as e:
            st.error(f"Ошибка генерации текстов: {e}")
            import traceback
            st.code(traceback.format_exc(), language="text")

# ---------------------------------------------------------------------------
# Отображение карточки и текстов — один раз в самом конце.
# ---------------------------------------------------------------------------
if last_result and last_card:
    _render_card(last_result)
    _render_texts(last_result)
