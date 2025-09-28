from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Получаем токены из переменных окружения (безопасно!)
VK_TOKEN = os.getenv("VK_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")  # строка подтверждения из ВК

def get_yandex_gpt_response(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [{"role": "user", "text": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['result']['alternatives'][0]['message']['text']
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/vk', methods=['POST'])
def vk_bot():
    data = request.json

    # Подтверждение сервера
    if data.get('type') == 'confirmation':
        return CONFIRMATION_TOKEN

    # Обработка сообщения
    if data.get('type') == 'message_new':
        user_id = data['object']['message']['from_id']
        text = data['object']['message']['text']

        ai_response = get_yandex_gpt_response(text)

        # Отправка ответа в ВК
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

    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))