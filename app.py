from flask import Flask, request
import requests
import os
import sys
import time
import random

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
    # 🔥 Улучшенный промпт для борьбы с "пробелами"
    improved_prompt = (
        "Ты — полезный ИИ-ассистент. Ответь на русском языке чётко, по делу и без лишних символов. "
        "Не отправляй пустые сообщения. Всегда пиши полный ответ. Вопрос: " + prompt
    )
    
    for attempt in range(3):  # До 3 попыток
        start_time = time.time()
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [
                {"role": "user", "content": improved_prompt}
            ],
            "temperature": 0.6,  # немного ниже для стабильности
            "max_tokens": 800
        }

        try:
            print(f"📩 Попытка {attempt + 1}: {prompt[:40]}...", file=sys.stderr)
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and result['choices']:
                answer = result['choices'][0]['message']['content']
                # Убираем пробелы и проверяем
                clean_answer = answer.strip()
                if len(clean_answer) > 2:  # Минимум 3 символа
                    duration = time.time() - start_time
                    print(f"🤖 Успешно за {duration:.2f} сек: {clean_answer[:60]}...", file=sys.stderr)
                    return clean_answer
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}", file=sys.stderr)
        
        if attempt < 2:
            time.sleep(1.5)  # Пауза перед повтором

    # Запасной ответ
    return "Извините, не удалось сформулировать ответ. Попробуйте задать вопрос иначе."

@app.route('/vk', methods=['GET', 'POST'])
def vk_bot():
    # Поддержка GET для UptimeRobot
    if request.method == 'GET':
        return "OK", 200

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

            # Небольшая задержка для стабильности
            time.sleep(0.3)

            ai_response = get_openrouter_response(text)

            # 🔒 ГАРАНТИЯ: сообщение не пустое и не слишком длинное
            if not ai_response or not ai_response.strip():
                ai_response = "Извините, я не могу сформулировать ответ. Попробуйте задать вопрос иначе."

            if len(ai_response) > 3900:
                ai_response = ai_response[:3900] + "..."

            # Генерируем уникальный random_id
            random_id = random.randint(1, 2**31 - 1)

            # Отправка в ВК
            try:
                vk_resp = requests.post(
                    "https://api.vk.com/method/messages.send",
                    data={
                        "user_id": user_id,
                        "message": ai_response,
                        "random_id": random_id,
                        "access_token": VK_TOKEN,
                        "v": "5.131"
                    },
                    timeout=10
                )
                vk_resp.raise_for_status()
                result = vk_resp.json()

                if 'error' in result:
                    error_code = result['error']['error_code']
                    error_msg = result['error']['error_msg']
                    print(f"❌ Ошибка ВК: [{error_code}] {error_msg}", file=sys.stderr)
                else:
                    msg_id = result.get('response', 'N/A')
                    print(f"✅ Сообщение доставлено пользователю {user_id} (ID: {msg_id})", file=sys.stderr)

            except Exception as e:
                print(f"❌ Ошибка отправки в ВК: {e}", file=sys.stderr)

        return "ok"

    except Exception as e:
        print(f"🔥 Критическая ошибка: {e}", file=sys.stderr)
        return "ok"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Запуск сервера на порту {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port)


