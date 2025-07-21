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
    """Загружает Facts.txt полностью (Flash лучше с большими контекстами)"""
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
        print(f"🔍 Начало: {facts[:100]}...")
        print(f"🔍 Конец: ...{facts[-100:]}")
        
        return facts
        
    except Exception as e:
        print(f"❌ Ошибка работы с Facts.txt: {e}")
        traceback.print_exc()
        return ""

def get_available_models():
    """Получает список доступных моделей с приоритетом Flash"""
    try:
        print("🔄 Проверяем доступные модели...")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                if 'flash' in model.name.lower():
                    print(f"⚡ Flash модель: {model.name}")
                elif 'gemini-2' in model.name:
                    print(f"🎯 Gemini 2.x: {model.name}")
                else:
                    print(f"✅ Модель: {model.name}")
        
        return available_models
    except Exception as e:
        print(f"❌ Ошибка получения моделей: {e}")
        return []

def get_news():
    """Получает новости"""
    print("🔄 Получаем новости...")
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
                
                for item in items[:6]:  # 6 новостей с каждого источника
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
    
    print(f"✅ Получено {len(news_items)} новостей")
    return news_items

def initialize_gemini_flash(facts):
    """Инициализирует Gemini 2.5 Flash с полными фактами"""
    
    available_models = get_available_models()
    if not available_models:
        return None, "Нет моделей"
    
    # ПРИОРИТЕТ: Gemini 2.5 Flash (лучше для больших контекстов)
    preferred_models = [
        'models/gemini-2.5-flash',
        'models/gemini-2.5-flash-002', 
        'models/gemini-2.5-flash-001',
        'models/gemini-2.0-flash',
        'models/gemini-1.5-flash',
        'models/gemini-2.5-pro'  # Запасной вариант
    ]
    
    selected_model = None
    for model in preferred_models:
        if model in available_models:
            selected_model = model
            print(f"⚡ ВЫБРАНА FLASH МОДЕЛЬ: {selected_model}")
            break
    
    if not selected_model:
        selected_model = available_models[0]
        print(f"⚠️ Используем доступную модель: {selected_model}")
    
    try:
        model = genai.GenerativeModel(selected_model)
        
        # Настройки для Flash (более агрессивные)
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=500,  # Больше для Flash
        )
        
        print(f"🔄 Инициализация Flash с {len(facts)} символами...")
        
        # Простая инициализация для Flash
        init_prompt = f"Изучи данную информацию и подготовься к анализу новостей:\n\n{facts}\n\nОтветь: готов к работе."
        
        response = model.generate_content(
            init_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"✅ Flash инициализирован: {response.text[:100]}...")
            return model, response.text
        else:
            print("❌ Пустой ответ от Flash")
            return None, "Пустой ответ"
            
    except Exception as e:
        print(f"❌ Ошибка Flash инициализации: {e}")
        
        # Если Flash не работает с полным размером, пробуем с ограничением
        if "token" in str(e).lower() or "max" in str(e).lower():
            print("🔄 Flash: пробуем с ограниченным размером...")
            try:
                limited_facts = facts[:100000]  # 100K символов для Flash
                limited_prompt = f"Информация:\n{limited_facts}\n\nГотов анализировать новости?"
                
                response = model.generate_content(limited_prompt, generation_config=generation_config)
                if response and response.text:
                    print(f"✅ Flash с ограничением: {response.text}")
                    return model, response.text
            except Exception as e2:
                print(f"❌ Flash ограниченный тоже не работает: {e2}")
        
        return None, str(e)

def generate_commentary(model, news_items):
    """Генерирует комментарий через Flash"""
    if not model or not news_items:
        return None, None
    
    print("🔄 Flash генерирует анализ новостей...")
    
    # Полный список новостей для Flash
    news_text = ""
    for i, item in enumerate(news_items, 1):
        news_text += f"{i}. {item['title']}\n"
        if item['description']:
            news_text += f"   {item['description']}\n"
        news_text += f"   Источник: {item['source']}\n"
        if item['link']:
            news_text += f"   Ссылка: {item['link']}\n"
        news_text += "\n"
    
    # Развернутый промпт для Flash
    analysis_prompt = f"""Проанализируй следующие новости используя изученную информацию:

{news_text}

Напиши развернутый аналитический обзор со следующей структурой:

## ОСНОВНЫЕ ТЕНДЕНЦИИ
## КОНТЕКСТ И ПРИЧИНЫ  
## ВОЗМОЖНЫЕ ПОСЛЕДСТВИЯ
## ВЫВОДЫ И ПРОГНОЗ

Используй знания из изученной информации для глубокого анализа."""
    
    try:
        # Более агрессивные настройки для Flash
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            max_output_tokens=3000,  # Большой вывод для Flash
        )
        
        print(f"⚡ Flash анализирует ({len(analysis_prompt)} символов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"✅ Flash анализ готов ({len(response.text)} символов)")
            return response.text, analysis_prompt
        else:
            return "Flash: ошибка генерации", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка Flash анализа: {e}")
        return f"Flash ошибка: {e}", analysis_prompt

def save_commentary(commentary, news_items, init_response, prompt):
    """Сохраняет результаты Flash анализа"""
    if not ensure_directory_exists('commentary'):
        return False
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond}"
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        main_filename = f'commentary/flash_news_analysis_{timestamp}.md'
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Анализ новостей Gemini 2.5 Flash - {date_formatted}\n\n")
            f.write(f"*Анализ выполнен моделью Gemini 2.5 Flash*\n\n")
            f.write("---\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## Источники новостей:\n\n")
            
            for i, item in enumerate(news_items, 1):
                f.write(f"### {i}. {item['title']}\n")
                if item['description']:
                    f.write(f"{item['description']}\n\n")
                f.write(f"**Источник:** {item['source']}\n")
                if item['link']:
                    f.write(f"**Ссылка:** {item['link']}\n")
                f.write("\n---\n\n")
        
        stats_filename = f'commentary/flash_stats_{timestamp}.txt'
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== GEMINI 2.5 FLASH СТАТИСТИКА ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write(f"Модель: Gemini 2.5 Flash\n")
            f.write(f"Новостей обработано: {len(news_items)}\n")
            f.write(f"Длина анализа: {len(commentary)} символов\n")
            f.write(f"ID: {timestamp}\n")
        
        print(f"⚡ Flash результат сохранён: {timestamp}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения Flash: {e}")
        return False

def main():
    try:
        print("⚡ === ЗАПУСК GEMINI 2.5 FLASH АНАЛИЗАТОРА ===")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ Нет API ключа")
            return False
        
        genai.configure(api_key=api_key)
        
        # Загружаем полные факты для Flash
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        # Инициализация Flash
        model, init_response = initialize_gemini_flash(facts)
        if not model:
            print("❌ Flash не инициализирован")
            return False
        
        time.sleep(2)
        
        # Новости
        news_items = get_news()
        if not news_items:
            print("❌ Нет новостей")
            return False
        
        time.sleep(1)
        
        # Flash анализ
        commentary, prompt = generate_commentary(model, news_items)
        if not commentary:
            print("❌ Flash не создал анализ")
            return False
        
        # Сохранение Flash результатов
        return save_commentary(commentary, news_items, init_response, prompt)
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА FLASH: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
