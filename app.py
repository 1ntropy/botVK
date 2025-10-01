from flask import Flask, request
import requests
import os
import sys

app = Flask(__name__)

# Загружаем переменные окружения
VK_TOKEN = os.getenv("VK_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")

# Проверка обязательных переменных
required_vars = {
    "VK_TOKEN": VK_TOKEN,
    "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
    "CONFIRMATION_TOKEN": CONFIRMATION_TOKEN,
}

for name, value in required_vars.items():
    if not value:
        print(f"❌ ОШИБКА: Не задана переменная окружения {name}", file=sys.stderr)
    else:
        print(f"✅ {name} загружен (длина: {len(value)})", file=sys.stderr)

def get_deepseek_response(prompt: str) -> str:
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        print(f"📩 Отправляю запрос в DeepSeek: {prompt[:50]}...", file=sys.stderr)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        answer = result['choices'][0]['message']['content']
        print(f"🤖 Получен ответ от DeepSeek: {answer[:60]}...", file=sys.stderr)
        return answer
    except Exception as e:
        error_msg = f"Ошибка при обращении к DeepSeek: {e}"
        print(f"❌ {error_msg}", file=sys.stderr)
        return error_msg

@app.route('/vk', methods=['POST'])
def vk_bot():
    try:
        # Получаем JSON
        data = request.get_json()
        if data is None:
            print("❌ Получен пустой или не-JSON запрос", file=sys.stderr)
            return "ok", 400

        print(f"📥 Получен запрос от ВК: type={data.get('type')}", file=sys.stderr)

        # Подтверждение сервера
        if data.get('type') == 'confirmation':
            print(f"✅ Возвращаем строку подтверждения: {CONFIRMATION_TOKEN}", file=sys.stderr)
            return CONFIRMATION_TOKEN  # ← просто строка!

        # Обработка сообщения
        if data.get('type') == 'message_new':
            try:
                user_id = data['object']['message']['from_id']
                text = data['object']['message']['text']
                print(f"💬 Сообщение от пользователя {user_id}: {text}", file=sys.stderr)
            except KeyError:
                print("❌ Неверный формат сообщения от ВК", file=sys.stderr)
                return "ok"

            # ИСПРАВЛЕНО: вызываем DeepSeek, а не Yandex
            ai_response = get_deepseek_response(text)

            # Отправляем ответ в ВК
            vk_send_url = "https://api.vk.com/method/messages.send"
            vk_data = {
                "user_id": user_id,
                "message": ai_response,
                "random_id": 0,
                "access_token": VK_TOKEN,
                "v": "5.131"
            }

            try:
                vk_resp = requests.post(vk_send_url, data=vk_data, timeout=10)
                vk_resp.raise_for_status()
                print(f"📤 Ответ отправлен пользователю {user_id}", file=sys.stderr)
            except Exception as e:
                print(f"❌ Не удалось отправить ответ в ВК: {e}", file=sys.stderr)

        return "ok"

    except Exception as e:
        print(f"🔥 Критическая ошибка в обработчике: {e}", file=sys.stderr)
        return "ok"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Запуск сервера на порту {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port)
