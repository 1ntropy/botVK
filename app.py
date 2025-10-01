from flask import Flask, request
import requests
import os
import sys

app = Flask(__name__)

# Загружаем переменные окружения
VK_TOKEN = os.getenv("VK_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")

# Проверка обязательных переменных
required_vars = {
    "VK_TOKEN": VK_TOKEN,
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "CONFIRMATION_TOKEN": CONFIRMATION_TOKEN,
}

for name, value in required_vars.items():
    if not value:
        print(f"❌ ОШИБКА: Не задана переменная окружения {name}", file=sys.stderr)
    else:
        print(f"✅ {name} загружен (длина: {len(value)})", file=sys.stderr)

def get_openrouter_response(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        print(f"📩 Отправляю запрос в OpenRouter (Mistral): {prompt[:50]}...", file=sys.stderr)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        answer = result['choices'][0]['message']['content']
        print(f"🤖 Получен ответ от Mistral: {answer[:60]}...", file=sys.stderr)
        return answer
    except Exception as e:
        error_msg = f"Ошибка OpenRouter: {e}"
        print(f"❌ {error_msg}", file=sys.stderr)
        return error_msg

@app.route('/vk', methods=['POST'])
def vk_bot():
    try:
        data = request.get_json()
        if data is None:
            print("❌ Получен пустой или не-JSON запрос", file=sys.stderr)
            return "ok", 400

        print(f"📥 Получен запрос от ВК: type={data.get('type')}", file=sys.stderr)

        if data.get('type') == 'confirmation':
            print(f"✅ Возвращаем строку подтверждения: {CONFIRMATION_TOKEN}", file=sys.stderr)
            return CONFIRMATION_TOKEN

        if data.get('type') == 'message_new':
            try:
                user_id = data['object']['message']['from_id']
                text = data['object']['message']['text']
                print(f"💬 Сообщение от пользователя {user_id}: {text}", file=sys.stderr)
            except KeyError:
                print("❌ Неверный формат сообщения от ВК", file=sys.stderr)
                return "ok"

            ai_response = get_openrouter_response(text)

            # Отправка в ВК
            requests.post(
                "https://api.vk.com/method/messages.send",
                data={
                    "user_id": user_id,
                    "message": ai_response,
                    "random_id": 0,
                    "access_token": VK_TOKEN,
                    "v": "5.131"
                },
                timeout=10
            )
            print(f"📤 Ответ отправлен пользователю {user_id}", file=sys.stderr)

        return "ok"

    except Exception as e:
        print(f"🔥 Критическая ошибка: {e}", file=sys.stderr)
        return "ok"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Запуск сервера на порту {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port)
