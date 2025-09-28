from flask import Flask, request
import requests
import os
import sys

app = Flask(__name__)

# Загружаем переменные окружения
VK_TOKEN = os.getenv("VK_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")

# Проверка обязательных переменных (для отладки)
required_vars = {
    "VK_TOKEN": VK_TOKEN,
    "YANDEX_API_KEY": YANDEX_API_KEY,
    "FOLDER_ID": FOLDER_ID,
    "CONFIRMATION_TOKEN": CONFIRMATION_TOKEN,
}

for name, value in required_vars.items():
    if not value:
        print(f"❌ ОШИБКА: Не задана переменная окружения {name}", file=sys.stderr)
    else:
        print(f"✅ {name} загружен (длина: {len(value)})", file=sys.stderr)

def get_yandex_gpt_response(prompt: str) -> str:
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {"role": "user", "text": prompt}
        ]
    }

    try:
        print(f"📩 Отправляю запрос в Yandex GPT: {prompt[:50]}...", file=sys.stderr)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        answer = result['result']['alternatives'][0]['message']['text']
        print(f"🤖 Получен ответ от ИИ: {answer[:60]}...", file=sys.stderr)
        return answer
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка сети или API: {e}"
        print(f"❌ {error_msg}", file=sys.stderr)
        return error_msg
    except KeyError as e:
        error_msg = f"Неожиданный формат ответа от Yandex GPT: {e}"
        print(f"❌ {error_msg}", file=sys.stderr)
        return error_msg
    except Exception as e:
        error_msg = f"Неизвестная ошибка: {e}"
        print(f"❌ {error_msg}", file=sys.stderr)
        return error_msg

@app.route('/vk', methods=['POST'])
def vk_bot():
     # Получаем сырое тело запроса для отладки
    raw_data = request.get_data(as_text=True)
    print(f"📥 Raw request body: {raw_data}", file=sys.stderr)

    try:
        data = request.get_json()
    except Exception as e:
        print(f"❌ Не удалось распарсить JSON: {e}", file=sys.stderr)
        return "ok", 400

    if not data:
        print("❌ Пустой JSON", file=sys.stderr)
        return "ok", 400

    # Обработка подтверждения
    if data.get('type') == 'confirmation':
        print(f"✅ Подтверждение: возвращаем '{CONFIRMATION_TOKEN}'", file=sys.stderr)
        # Важно: возвращаем ТОЛЬКО строку, без JSON, без лишних символов
        return CONFIRMATION_TOKEN

    # Обработка сообщений
    if data.get('type') == 'message_new':
        print("📩 Обработка сообщения...", file=sys.stderr)
        # ... (оставь твой код для ответа ИИ)

    return "ok"

    except Exception as e:
        print(f"🔥 Критическая ошибка в обработчике: {e}", file=sys.stderr)
        return "ok"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Запуск сервера на порту {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port)

