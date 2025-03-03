from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import openai

# Установи свой OpenAI API ключ
client = openai.OpenAI(api_key="ВАШ_OPENAI_API_KEY")

app = FastAPI()

class URLRequest(BaseModel):
    url: str

def fetch_homepage(url):
    """Загружает HTML главной страницы"""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def clean_text(html):
    """Удаляет HTML-код, оставляя только текст"""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    return " ".join(lines[:2000])  # Ограничение текста

def generate_system_prompt(company_info):
    """Создаёт кастомный системный промт для ассистента"""
    return f"""
Анализируй информацию, полученную с сайта!
Сразу после анализа ты переформатируешь/адаптируешь скрипт под бизнес клиента (используя данные о компании). 
Далее, уже как «ассистент {company_info.get('Название', 'Нет данных')}», будешь вести диалог, опираясь на обновлённую информацию.

Важно соблюдать следующие **ограничения и правила**:

1. **Не выдумывай** новых цен, услуг или информации, которой нет в описании.  
2. Все упомянутые цены, характеристики и условия строго соответствуют тому, что описано ниже — если в описании их нет, сообщай, что нужно уточнить.  
3. Если пользователь спрашивает о чём-то, что не отражено в твоём описании, отвечай, что уточнишь детали и вернёшься позже.  
4. **Тон** общения — дружелюбный, краткий, с интонацией «живого» менеджера. Иногда допускаются лёгкие опечатки.  
5. Говори «как человек», но старайся быть понятным, не забывая про «скрипт».  

### О компании:
- **Название:** {company_info.get('Название', 'Нет данных')}
- **Описание:** {company_info.get('Описание', 'Нет данных')}
- **Контакты:** {company_info.get('Телефон', 'Нет данных')} | {company_info.get('Email', 'Нет данных')}
- **Адрес:** {company_info.get('Адрес', 'Нет данных')}
- **График работы:** {company_info.get('График работы', 'Нет данных')}
- **Основные услуги:** {company_info.get('Услуги/Товары', 'Нет данных')}
"""

def extract_info_with_gpt(site_url, clean_text):
    """Анализирует сайт и создаёт системный промт"""
    prompt = f"""
Ты — AI, который анализирует сайты компаний.
Вот текст с главной страницы {site_url}:

\"\"\"{clean_text}\"\"\"

Извлеки информацию:
Название: ...
Описание: ...
Телефон: ...
Email: ...
Адрес: ...
График работы: ...
Услуги/Товары: ...

Верни данные в JSON-формате.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.0,
    )

    company_info = eval(response.choices[0].message.content)
    return generate_system_prompt(company_info)

@app.post("/process")
async def process_url(request: URLRequest):
    """Получает ссылку, анализирует сайт и создаёт системный промт"""
    try:
        print(f"🔹 Обрабатываем сайт: {request.url}")

        html = fetch_homepage(request.url)
        print("✅ Страница загружена")

        text = clean_text(html)
        print("✅ Текст очищен")

        system_prompt = extract_info_with_gpt(request.url, text)
        print("✅ GPT-анализ завершён")

        return {"system_prompt": system_prompt}
    except Exception as e:
        print(f"🔴 Ошибка обработки {request.url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze")
async def analyze_url(url: str):
    """Анализирует сайт через GET-запрос"""
    try:
        print(f"🔹 GET-запрос на анализ: {url}")

        html = fetch_homepage(url)
        print("✅ Страница загружена")

        text = clean_text(html)
        print("✅ Текст очищен")

        system_prompt = extract_info_with_gpt(url, text)
        print("✅ GPT-анализ завершён")

        return {"system_prompt": system_prompt}
    except Exception as e:
        print(f"🔴 Ошибка обработки {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
