from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import openai

openai.api_key = "ВАШ_OPENAI_API_KEY"

app = FastAPI()

class URLRequest(BaseModel):
    url: str

def fetch_homepage(url):
    """Загружаем HTML главной страницы"""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def clean_text(html):
    """Удаляем код, оставляем текст"""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    return " ".join(lines[:2000])  # Ограничиваем размер

def generate_system_prompt(company_info):
    """Создаёт кастомный системный промт для ассистента"""
    return f"""
Ты — виртуальный ассистент компании **{company_info.get('Название', 'Нет данных')}**.  
Твоя задача — помогать клиентам, предоставляя информацию о бизнесе.  
Ты работаешь как профессиональный менеджер поддержки.  

### О компании:
- **Описание:** {company_info.get('Описание', 'Нет данных')}
- **Контакты:** {company_info.get('Телефон', 'Нет данных')} | {company_info.get('Email', 'Нет данных')}
- **Адрес:** {company_info.get('Адрес', 'Нет данных')}
- **График работы:** {company_info.get('График работы', 'Нет данных')}
- **Основные услуги:** {company_info.get('Услуги/Товары', 'Нет данных')}

### Как ты должен отвечать:
- Веди себя как сотрудник компании.
- Используй тёплый, но профессиональный стиль общения.
- Если клиент спрашивает про услуги — подробно расскажи.
- Если информации нет — напиши "Я уточню этот вопрос и скоро вернусь с ответом!".
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

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.0,
    )

    company_info = eval(response["choices"][0]["message"]["content"])
    return generate_system_prompt(company_info)

@app.post("/process")
async def process_url(request: URLRequest):
    """Получает ссылку, анализирует сайт и создаёт системный промт"""
    try:
        html = fetch_homepage(request.url)
        text = clean_text(html)
        system_prompt = extract_info_with_gpt(request.url, text)
        return {"system_prompt": system_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
