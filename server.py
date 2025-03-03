import json

def extract_info_with_gpt(site_url, clean_text):
    """Анализирует сайт и создаёт системный промт"""
    prompt = f"""
Ты — AI, который анализирует сайты компаний.
Вот текст с главной страницы {site_url}:

\"\"\"{clean_text}\"\"\"

Извлеки информацию в JSON-формате:
{{
  "Название": "...",
  "Описание": "...",
  "Телефон": "...",
  "Email": "...",
  "Адрес": "...",
  "График работы": "...",
  "Услуги/Товары": "..."
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.0,
        )
        
        # Извлекаем текст из OpenAI ответа
        raw_response = response.choices[0].message.content.strip()

        # Пытаемся разобрать JSON
        company_info = json.loads(raw_response)

        return generate_system_prompt(company_info)

    except json.JSONDecodeError:
        print("🔴 Ошибка парсинга JSON-ответа от OpenAI!")
        raise HTTPException(status_code=500, detail="Ошибка обработки данных от OpenAI")

    except Exception as e:
        print(f"🔴 Ошибка в OpenAI API: {e}")
        raise HTTPException(status_code=500, detail="Ошибка запроса к OpenAI API")
