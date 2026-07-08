import json
import re
import ollama

DEFAULT_MODEL = "qwen2.5:14b"


def call_ollama(prompt, model=DEFAULT_MODEL, temperature=0.3, max_tokens=2000):
    """Отправляет промпт в локальную модель Ollama и возвращает текст ответа."""
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": "Ты — помощник для интернет-магазина премиальных часов 316.watch. Пиши по-русски, точно, без пафоса. Не выдумывай факты."},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )
        return response["message"]["content"]
    except Exception as e:
        return f"[Ошибка Ollama: {e}]"


def extract_json(text):
    """Пытается извлечь JSON из ответа модели."""
    # Ищем JSON в ```json ... ```
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    # Ищем первые фигурные скобки
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1)

    return text
