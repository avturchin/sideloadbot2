import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import traceback
import sys

def ensure_directory_exists(directory):
    """Создает папку если её нет"""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Папка {directory} создана")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания папки {directory}: {e}")
        return False

def load_facts():
    """Загружает Facts.txt с ограничением для Flash-Lite"""
    try:
        print("🔄 Загружаем файл Facts.txt...")
        
        if not os.path.exists('Facts.txt'):
            print("❌ Файл Facts.txt НЕ НАЙДЕН!")
            return ""
            
        file_size = os.path.getsize('Facts.txt')
        print(f"📊 Размер Facts.txt: {file_size} байт ({file_size/1024/1024:.2f} МБ)")
        
        with open('Facts.txt', 'r', encoding='utf-8') as f:
            facts = f.read()
        
        print(f"✅ Загружено: {len(facts)} символов")
        
        # ОГРАНИЧЕНИЕ для Flash-Lite: 30,000 символов (более консервативно)
        MAX_FACTS_SIZE = 30000
        
        if len(facts) > MAX_FACTS_SIZE:
            print(f"⚠️ Файл слишком большой ({len(facts)} символов)")
            print(f"🔪 Обрезаем до {MAX_FACTS_SIZE} символов для Flash-Lite")
            
            # Умное обрезание
            truncated = facts[:MAX_FACTS_SIZE]
            
            # Ищем последнюю точку
            search_start = max(MAX_FACTS_SIZE - 1500, 0)
            last_dot = truncated.rfind('. ', search_start)
            if last_dot > search_start:
                facts = truncated[:last_dot + 2]
            else:
                # Ищем последний абзац
                last_paragraph = truncated.rfind('\n\n', search_start)
                if last_paragraph > search_start:
                    facts = truncated[:last_paragraph + 2]
                else:
                    facts = truncated
            
            print(f"✂️ Итоговый размер: {len(facts)} символов")
        
        print(f"🔍 Начало: {facts[:120]}...")
        print(f"🔍 Конец: ...{facts[-120:]}")
        
        return facts
        
    except Exception as e:
        print(f"❌ Ошибка работы с Facts.txt: {e}")
        traceback.print_exc()
        return ""

def get_available_models():
    """Получает список доступных моделей с приоритетом Flash-Lite"""
    try:
        print("🔄 Проверяем доступные модели Flash-Lite...")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                if 'flash-lite' in model.name.lower():
                    print(f"💨 Flash-Lite: {model.name}")
                elif 'flash' in model.name.lower() and '2.0' in model.name:
                    print(f"⚡ Gemini 2.0 Flash: {model.name}")
                elif 'flash' in model.name.lower():
                    print(f"⚡ Flash: {model.name}")
        
        return available_models
    except Exception as e:
        print(f"❌ Ошибка получения моделей: {e}")
        return []

def get_news():
    """Получает новости оптимизированно для Flash-Lite"""
    print("🔄 Получаем новости для Flash-Lite...")
    news_items = []
    
    sources = [
        {'url': 'https://lenta.ru/rss/news', 'name': 'Lenta.ru'},
        {'url': 'https://ria.ru/export/rss2/archive/index.xml', 'name': 'РИА Новости'}
    ]
    
    for source in sources:
        try:
            print(f"🔄 Получаем с {source['name']}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(source['url'], timeout=15, headers=headers)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                print(f"📰 Найдено {len(items)} новостей")
                
                for item in items[:6]:  # Умеренное количество для Lite
                    try:
                        title = item.title.text.strip() if item.title else "Без заголовка"
                        description = ""
                        if item.description and item.description.text:
                            desc_soup = BeautifulSoup(item.description.text, 'html.parser')
                            description = desc_soup.get_text().strip()
                        
                        link = item.link.text.strip() if item.link else ""
                        
                        news_items.append({
                            'title': title,
                            'description': description,
                            'source': source['name'],
                            'link': link
                        })
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка новости: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Ошибка {source['name']}: {e}")
            continue
    
    print(f"✅ Получено {len(news_items)} новостей для Flash-Lite")
    return news_items

def initialize_flash_lite(facts):
    """Инициализирует Gemini 2.0 Flash-Lite"""
    
    available_models = get_available_models()
    if not available_models:
        return None, "Нет моделей"
    
    # ПРИОРИТЕТ: Gemini 2.0 Flash-Lite
    preferred_models = [
        'models/gemini-2.0-flash-lite',
        'models/gemini-2.0-flash-lite-exp',
        'models/gemini-2.0-flash',
        'models/gemini-1.5-flash'
    ]
    
    selected_model = None
    for model in preferred_models:
        if model in available_models:
            selected_model = model
            if 'lite' in model:
                print(f"💨 ВЫБРАНА FLASH-LITE: {selected_model}")
            else:
                print(f"⚡ Выбрана запасная: {selected_model}")
            break
    
    if not selected_model:
        selected_model = available_models[0]
        print(f"⚠️ Используем: {selected_model}")
    
    try:
        # Системные инструкции для Flash-Lite (короткие)
        system_instruction = f"""Ты аналитик новостей. База знаний:

{facts}

Анализируй новости кратко и точно."""

        print(f"🔄 Создаем Flash-Lite с системными инструкциями ({len(system_instruction)} символов)...")
        
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction
        )
        
        # Консервативные настройки для Lite
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=200,  # Небольшой для теста
        )
        
        print("🔄 Тестируем Flash-Lite...")
        test_response = model.generate_content(
            "Готов анализировать новости?",
            generation_config=generation_config
        )
        
        if test_response and test_response.text:
            print(f"✅ Flash-Lite готов: {test_response.text}")
            return model, test_response.text
        else:
            print("❌ Flash-Lite: пустой ответ")
            return None, "Пустой ответ"
            
    except Exception as e:
        print(f"❌ Ошибка Flash-Lite: {e}")
        
        # Fallback: без фактов
        try:
            print("🔄 Flash-Lite fallback без фактов...")
            simple_system = "Ты аналитик новостей. Анализируй кратко и профессионально."
            
            model = genai.GenerativeModel(
                model_name=selected_model,
                system_instruction=simple_system
            )
            
            test_response = model.generate_content(
                "Готов анализировать?",
                generation_config=generation_config
            )
            
            if test_response and test_response.text:
                print(f"✅ Flash-Lite fallback: {test_response.text}")
                return model, test_response.text
                
        except Exception as e2:
            print(f"❌ Flash-Lite fallback: {e2}")
        
        return None, str(e)

def generate_lite_commentary(model, news_items):
    """Генерирует анализ через Flash-Lite"""
    if not model or not news_items:
        return None, None
    
    print("💨 Flash-Lite анализирует новости...")
    
    # Краткий список новостей для Lite
    news_text = ""
    for i, item in enumerate(news_items, 1):
        news_text += f"{i}. {item['title']}\n"
        if item['description']:
            # Сильно ограничиваем для Lite
            desc = item['description'][:200] + "..." if len(item['description']) > 200 else item['description']
            news_text += f"   {desc}\n"
        news_text += f"   ({item['source']})\n\n"
    
    # Компактный промпт для Lite
    analysis_prompt = f"""Проанализируй новости:

{news_text}

Дай краткий анализ:
- Главные события
- Тенденции
- Выводы"""
    
    try:
        # Настройки для Flash-Lite
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            max_output_tokens=2500,  # Умеренно для Lite
        )
        
        print(f"💨 Flash-Lite генерирует ({len(analysis_prompt)} символов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"✅ Flash-Lite анализ готов ({len(response.text)} символов)")
            return response.text, analysis_prompt
        else:
            return "Flash-Lite: ошибка генерации", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка Flash-Lite анализа: {e}")
        return f"Flash-Lite ошибка: {e}", analysis_prompt

def save_lite_results(commentary, news_items, init_response, prompt):
    """Сохраняет результаты Flash-Lite"""
    if not ensure_directory_exists('commentary'):
        return False
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond}"
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        main_filename = f'commentary/flash_lite_analysis_{timestamp}.md'
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Анализ Gemini 2.0 Flash-Lite - {date_formatted}\n\n")
            f.write(f"*Быстрый анализ от Gemini 2.0 Flash-Lite*\n\n")
            f.write("---\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## Новости:\n\n")
            
            for i, item in enumerate(news_items, 1):
                f.write(f"### {i}. {item['title']}\n")
                if item['description']:
                    f.write(f"{item['description']}\n\n")
                f.write(f"**Источник:** {item['source']}\n")
                if item['link']:
                    f.write(f"**Ссылка:** {item['link']}\n")
                f.write("\n---\n\n")
        
        stats_filename = f'commentary/flash_lite_stats_{timestamp}.txt'
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== GEMINI 2.0 FLASH-LITE ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write(f"Модель: Gemini 2.0 Flash-Lite\n")
            f.write(f"Новостей: {len(news_items)}\n")
            f.write(f"Длина анализа: {len(commentary)} символов\n")
            f.write(f"ID: {timestamp}\n")
        
        print(f"💨 Flash-Lite результат сохранён: {timestamp}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения Flash-Lite: {e}")
        return False

def main():
    try:
        print("💨 === GEMINI 2.0 FLASH-LITE АНАЛИЗАТОР ===")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ Нет API ключа")
            return False
        
        genai.configure(api_key=api_key)
        
        # Загружаем факты (ограниченно для Lite)
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        # Инициализация Flash-Lite
        model, init_response = initialize_flash_lite(facts)
        if not model:
            print("❌ Flash-Lite не инициализирован")
            return False
        
        time.sleep(1)
        
        # Новости
        news_items = get_news()
        if not news_items:
            print("❌ Нет новостей")
            return False
        
        time.sleep(1)
        
        # Flash-Lite анализ
        commentary, prompt = generate_lite_commentary(model, news_items)
        if not commentary:
            print("❌ Flash-Lite не создал анализ")
            return False
        
        # Сохранение
        return save_lite_results(commentary, news_items, init_response, prompt)
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА FLASH-LITE: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
