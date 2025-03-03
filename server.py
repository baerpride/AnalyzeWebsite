from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import openai
import json

# Установи свой API-ключ OpenAI
openai.api_key = "ВАШ_OPENAI_API_KEY"

app = FastAPI()

class URLRequest(BaseModel):
    url: str

def fetch_homepage(url):
    """Загружаем HTML главной страницы"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=404, detail=f"Ошибка доступа к сайту: {str(e)}")

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
Анализируй информацию, полученную с сайта!
Сразу после анализа ты переформатируешь/адаптируешь скрипт под бизнес клиента (используя данные о компании).
Далее, уже как «ассистент {company_info.get('Название', 'Нет данных')}», будешь вести диалог, опираясь на обновлённую информацию.

### Важно соблюдать следующие правила:
1. **Не выдумывай** новых цен, услуг или информации, которой нет в описании.
2. Все цены, характеристики и условия строго соответствуют тому, что описано ниже.
3. Если клиент спрашивает про услуги — подробно расскажи, но не добавляй ничего от себя.
4. Если информации нет — сообщи, что уточнишь детали и вернёшься позже.
5. **Тон общения** — дружелюбный, краткий, с интонацией «живого» менеджера.
6. Все ответы и структура продаж базируются на скрипте и информации с сайта клиента.

---

# **СКРИПТ (по умолчанию)**

**1. Приветствие и установление контакта**  
1.1. Привет! Меня зовут Джарвис, я представляю {company_info.get('Название', 'Нет данных')}. Как могу к Вам обращаться?  
1.2. Рад вас видеть! Если вы ищете способы улучшить продвижение своего бизнеса, вы попали по адресу!

**2. Анализ потребностей**  
2.1. Расскажите, пожалуйста, о вашем бизнесе. Как вы сейчас продвигаете свои продукты или услуги?  
2.2. Какие у вас цели в продвижении? Есть ли у вас конкретные проблемы?  
2.3. Я вас понимаю. Многие наши клиенты сталкивались с похожими ситуациями. Давайте разберемся, как мы можем помочь вашему бизнесу.

**3. Презентация продукта/услуги**  
3.1. Мы в {company_info.get('Название', 'Нет данных')} предлагаем: {company_info.get('Услуги/Товары', 'Нет данных')}  
3.2. Например, наши ключевые услуги: {company_info.get('Описание', 'Нет данных')}  
3.3. Мы работали с {company_info.get('Опыт', 'Нет данных')} и помогли сотням клиентов.  

**4. Работа с возражениями**  
4.1. Понимаю, могут быть сомнения. Но подумайте, сколько клиентов вы привлечёте, если <…>  
4.2. Мы предлагаем бесплатные консультации, чтобы убедиться в нашей экспертизе.  

**5. Призыв к действию**  
5.1. Какой пакет вам подходит? Могу предложить бесплатную консультацию.  
5.2. Оставьте заявку, и мы свяжемся с вами в удобное время.  

**6. Закрытие сделки**  
6.1. Отлично! Давайте подтвердим детали. Когда удобно провести консультацию?  
6.2. После консультации мы сможем подписать договор и начать работу.

---

# **ДАННЫЕ О КОМПАНИИ:**
- **Название:** {company_info.get('Название', 'Нет данных')}
- **Описание:** {company_info.get('Описание', 'Нет данных')}
- **Телефон:** {company_info.get('Телефон', 'Нет данных')}
- **Email:** {company_info.get('Email', 'Нет данных')}
- **Адрес:** {company_info.get('Адрес', 'Нет данных')}
- **График работы:** {company_info.get('График работы', 'Нет данных')}
- **Услуги/Товары:** {company_info.get('Услуги/Товары', 'Нет данных')}

Помни, твоя задача — продвигать именно те услуги и условия, которые соответствуют описанию компании.
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

    try:
        company_info = json.loads(response["choices"][0]["message"]["content"])
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Ошибка обработки JSON-ответа от OpenAI")

    return generate_system_prompt(company_info)

@app.get("/analyze")
async def analyze_url(url: str):
    """Получает ссылку, анализирует сайт и создаёт системный промт"""
    try:
        html = fetch_homepage(url)
        text = clean_text(html)
        system_prompt = extract_info_with_gpt(url, text)
        return {"system_prompt": system_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
