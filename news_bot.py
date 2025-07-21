import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import traceback
import sys

def ensure_directory_exists(directory):
    """Создает папку если её нет и проверяет права доступа"""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Папка {directory} создана")
        else:
            print(f"✅ Папка {directory} уже существует")
        
        test_file = os.path.join(directory, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print(f"✅ Права на запись в {directory} проверены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания папки {directory}: {e}")
        return False

def load_facts():
    """Загружает ПОЛНУЮ базу фактов без ограничений"""
    try:
        print("🔄 Загружаем файл Facts.txt...")
        
        if not os.path.exists('Facts.txt'):
            print("❌ Файл Facts.txt НЕ НАЙДЕН!")
            return "Базовые знания отсутствуют."
            
        # Получаем размер файла
        file_size = os.path.getsize('Facts.txt')
        print(f"📊 Размер Facts.txt: {file_size} байт ({file_size/1024/1024:.2f} МБ)")
        
        # Читаем ВЕСЬ файл целиком
        with open('Facts.txt', 'r', encoding='utf-8') as f:
            facts = f.read()
        
        actual_length = len(facts)
        print(f"✅ ПОЛНАЯ база фактов загружена: {actual_length} символов")
        print(f"📊 Размер в памяти: {actual_length/1024/1024:.2f} МБ")
        
        # Показываем начало и конец для подтверждения
        print(f"🔍 Начало файла: {facts[:100]}...")
        print(f"🔍 Конец файла: ...{facts[-100:]}")
        
        # ВАЖНО: НЕ ОБРЕЗАЕМ файл, возвращаем полностью
        return facts
        
    except Exception as e:
        print(f"❌ Ошибка работы с Facts.txt: {e}")
        traceback.print_exc()
        return "Ошибка загрузки базы знаний."

def get_available_models():
    """Получает список доступных моделей Gemini"""
    try:
        print("🔄 Проверяем доступные модели Gemini...")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                if 'gemini-2.5' in model.name:
                    print(f"🎯 Доступная модель Gemini 2.5: {model.name}")
                else:
                    print(f"✅ Доступная модель: {model.name}")
        
        return available_models
    except Exception as e:
        print(f"❌ Ошибка получения списка моделей: {e}")
        return []

def get_news():
    """Получает свежие новости"""
    print("🔄 Получаем актуальные новости...")
    news_items = []
    
    sources = [
        {
            'url': 'https://lenta.ru/rss/news',
            'name': 'Lenta.ru'
        },
        {
            'url': 'https://ria.ru/export/rss2/archive/index.xml', 
            'name': 'РИА Новости'
        }
    ]
    
    for i, source in enumerate(sources, 1):
        try:
            print(f"🔄 [{i}/{len(sources)}] Получаем новости с {source['name']}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(source['url'], timeout=20, headers=headers)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                print(f"📰 Найдено {len(items)} новостей на {source['name']}")
                
                for j, item in enumerate(items[:5], 1):
                    try:
                        title = item.title.text.strip() if item.title else "Без заголовка"
                        description = ""
                        if item.description and item.description.text:
                            desc_soup = BeautifulSoup(item.description.text, 'html.parser')
                            description = desc_soup.get_text().strip()
                        
                        link = item.link.text.strip() if item.link else ""
                        pub_date = item.pubDate.text.strip() if item.pubDate else ""
                        
                        print(f"   📝 [{j}/5] {title[:50]}...")
                        
                        news_items.append({
                            'title': title,
                            'description': description,
                            'link': link,
                            'source': source['name'],
                            'pub_date': pub_date
                        })
                        
                    except Exception as e:
                        print(f"❌ Ошибка обработки новости {j}: {e}")
                        continue
                        
            else:
                print(f"⚠️ Ошибка {response.status_code} от {source['name']}")
                
        except Exception as e:
            print(f"❌ Ошибка получения новостей с {source['name']}: {e}")
            continue
    
    print(f"✅ Всего получено {len(news_items)} новостей")
    return news_items if news_items else [{'title': 'Тестовая новость', 'description': 'Тест', 'source': 'Тест', 'link': '', 'pub_date': ''}]

def initialize_gemini_with_facts(facts):
    """Инициализирует Gemini 2.5 Pro с базой фактов КАК ЕСТЬ"""
    
    available_models = get_available_models()
    if not available_models:
        return None, "Нет доступных моделей"
    
    # Приоритет Gemini 2.5 Pro
    preferred_models = [
        'models/gemini-2.5-pro',
        'models/gemini-2.5-pro-preview-06-05', 
        'models/gemini-2.5-pro-preview-05-06',
        'models/gemini-2.5-pro-preview-03-25'
    ]
    
    selected_model = None
    for model in preferred_models:
        if model in available_models:
            selected_model = model
            break
    
    if not selected_model:
        selected_model = available_models[0]
    
    print(f"🎯 Выбранная модель: {selected_model}")
    
    # Отправляем Facts.txt КАК ЕСТЬ, без дополнительных инструкций
    print(f"🔄 Инициализация с фактами ({len(facts)} символов)...")
    
    try:
        model = genai.GenerativeModel(selected_model)
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=1000,
        )
        
        print(f"🔄 Отправляем Facts.txt как есть...")
        
        # Отправляем ТОЛЬКО содержимое Facts.txt
        response = model.generate_content(
            facts,  # Только факты, никаких дополнительных инструкций
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"✅ Инициализация успешна ({len(response.text)} символов)")
            print(f"🔍 Ответ: {response.text[:200]}...")
            return model, response.text
        else:
            print("❌ Пустой ответ при инициализации")
            return None, "Пустой ответ"
            
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        traceback.print_exc()
        return None, str(e)

def generate_commentary(model, news_items):
    """Генерирует комментарий к новостям"""
    if not model or not news_items:
        return None, None
    
    print("🔄 Формируем список новостей для анализа...")
    
    news_text = ""
    for i, item in enumerate(news_items, 1):
        news_text += f"{i}. {item['title']}\n"
        if item['description']:
            news_text += f"   {item['description']}\n"
        news_text += f"   Источник: {item['source']}\n\n"
    
    # Минимальный промпт - только новости
    analysis_prompt = f"""Проанализируй эти новости:

{news_text}"""
    
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            max_output_tokens=4000,
        )
        
        print(f"🔄 Отправляем новости для анализа ({len(analysis_prompt)} символов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"✅ Анализ получен ({len(response.text)} символов)")
            return response.text, analysis_prompt
        else:
            return "Ошибка генерации анализа", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return f"Ошибка: {e}", analysis_prompt

def save_commentary(commentary, news_items, initialization_response, news_prompt):
    """Сохраняет результаты с уникальными именами файлов"""
    if not ensure_directory_exists('commentary'):
        return False
    
    # Создаем уникальную метку времени с микросекундами
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond}"
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        # Основной файл
        main_filename = f'commentary/news_commentary_{timestamp}.md'
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Анализ новостей - {date_formatted}\n\n")
            f.write(f"*Анализ выполнен моделью Gemini 2.5 Pro*\n\n")
            f.write("---\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## Проанализированные новости:\n\n")
            
            for i, item in enumerate(news_items, 1):
                f.write(f"### {i}. {item['title']}\n")
                if item['description']:
                    f.write(f"{item['description']}\n\n")
                f.write(f"**Источник:** {item['source']}\n\n")
                if item['link']:
                    f.write(f"**Ссылка:** {item['link']}\n\n")
                f.write("---\n\n")
        
        # Файл статистики
        stats_filename = f'commentary/stats_{timestamp}.txt'
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== СТАТИСТИКА АНАЛИЗА ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write(f"Модель: Gemini 2.5 Pro\n")
            f.write(f"Новостей: {len(news_items)}\n")
            f.write(f"Длина анализа: {len(commentary)} символов\n")
            f.write(f"Уникальный ID: {timestamp}\n")
        
        print(f"✅ Файлы сохранены с ID: {timestamp}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def main():
    try:
        print("🚀 === ЗАПУСК GEMINI 2.5 PRO АНАЛИЗАТОРА ===")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ Нет API ключа")
            return False
        
        genai.configure(api_key=api_key)
        
        # Загружаем ПОЛНУЮ базу фактов
        facts = load_facts()
        print(f"📊 Финальный размер базы: {len(facts)} символов")
        
        # Инициализация - отправляем Facts.txt как есть
        model, init_response = initialize_gemini_with_facts(facts)
        if not model:
            return False
        
        time.sleep(3)
        
        # Новости
        news_items = get_news()
        if not news_items:
            return False
        
        time.sleep(2)
        
        # Анализ
        commentary, prompt = generate_commentary(model, news_items)
        if not commentary:
            return False
        
        # Сохранение
        return save_commentary(commentary, news_items, init_response, prompt)
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
