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
        
        # ОГРАНИЧЕНИЕ для Flash-Lite: 30,000 символов
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

def is_science_news(title, description):
    """Проверяет, является ли новость научной"""
    text = (title + " " + description).lower()
    
    # Научные ключевые слова
    science_keywords = [
        'исследование', 'ученые', 'открытие', 'эксперимент', 'научный',
        'технология', 'разработка', 'инновация', 'лаборатория', 'университет',
        'институт', 'наука', 'биология', 'физика', 'химия', 'медицина',
        'космос', 'астрономия', 'генетика', 'днк', 'белок', 'вирус',
        'лечение', 'терапия', 'вакцина', 'препарат', 'клинический',
        'нейроны', 'мозг', 'когнитивный', 'искусственный интеллект', 'ии',
        'машинное обучение', 'алгоритм', 'робот', 'квантовый',
        'материал', 'нанотехнологии', 'биотехнологии', 'генная инженерия',
        'стволовые клетки', 'рак', 'онкология', 'диагностика',
        'микробиология', 'экология', 'климат', 'окружающая среда',
        'энергия', 'солнечный', 'ветряной', 'батарея', 'аккумулятор',
        'спутник', 'зонд', 'марс', 'луна', 'планета', 'галактика',
        'telescope', 'research', 'study', 'discovery', 'experiment'
    ]
    
    # Исключающие слова (политика, экономика, спорт)
    exclude_keywords = [
        'выборы', 'президент', 'парламент', 'дума', 'правительство', 'министр',
        'политик', 'партия', 'санкции', 'война', 'конфликт', 'протест',
        'курс валют', 'рубль', 'доллар', 'нефть', 'газ', 'экономика',
        'инфляция', 'бюджет', 'налог', 'спорт', 'футбол', 'хоккей',
        'олимпиада', 'чемпионат', 'матч', 'игра', 'команда', 'тренер'
    ]
    
    # Проверяем наличие научных слов
    science_score = sum(1 for keyword in science_keywords if keyword in text)
    
    # Проверяем наличие исключающих слов
    exclude_score = sum(1 for keyword in exclude_keywords if keyword in text)
    
    # Если есть научные слова и нет политических/экономических
    return science_score > 0 and exclude_score == 0

def get_science_news():
    """Получает только научные новости"""
    print("🔬 Получаем НАУЧНЫЕ новости...")
    science_news = []
    
    sources = [
        {
            'url': 'https://naked-science.ru/feed', 
            'name': 'Naked Science'
        },
        {
            'url': 'https://nplus1.ru/rss', 
            'name': 'N+1'
        },
        {
            'url': 'https://hi-news.ru/feed', 
            'name': 'Hi-News'
        },
        {
            'url': 'https://www.popmech.ru/rss/', 
            'name': 'PopMech'
        },
        {
            'url': 'https://lenta.ru/rss/news/science', 
            'name': 'Lenta.ru Наука'
        },
        {
            'url': 'https://ria.ru/export/rss2/archive/index.xml', 
            'name': 'РИА Новости'
        }
    ]
    
    for source in sources:
        try:
            print(f"🔬 Анализируем {source['name']}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(source['url'], timeout=15, headers=headers)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                print(f"📰 Найдено {len(items)} новостей, фильтруем научные...")
                
                source_science_count = 0
                for item in items:
                    try:
                        title = item.title.text.strip() if item.title else "Без заголовка"
                        description = ""
                        if item.description and item.description.text:
                            desc_soup = BeautifulSoup(item.description.text, 'html.parser')
                            description = desc_soup.get_text().strip()
                        
                        # ФИЛЬТРАЦИЯ: только научные новости
                        if is_science_news(title, description):
                            link = item.link.text.strip() if item.link else ""
                            
                            science_news.append({
                                'title': title,
                                'description': description,
                                'source': source['name'],
                                'link': link
                            })
                            
                            source_science_count += 1
                            print(f"🔬 {source['name']}: {title[:80]}...")
                            
                            # Ограничиваем количество с каждого источника
                            if source_science_count >= 5:
                                break
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка новости: {e}")
                        continue
                
                print(f"✅ {source['name']}: {source_science_count} научных новостей")
                        
        except Exception as e:
            print(f"❌ Ошибка {source['name']}: {e}")
            continue
    
    print(f"🔬 ИТОГО: {len(science_news)} научных новостей")
    return science_news

def initialize_science_flash_lite(facts):
    """Инициализирует Gemini 2.0 Flash-Lite для анализа науки"""
    
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
                print(f"🔬 ВЫБРАНА FLASH-LITE для науки: {selected_model}")
            else:
                print(f"⚡ Выбрана запасная для науки: {selected_model}")
            break
    
    if not selected_model:
        selected_model = available_models[0]
        print(f"⚠️ Используем для науки: {selected_model}")
    
    try:
        # Системные инструкции для научного анализа
        system_instruction = f"""Ты специализированный аналитик НАУЧНЫХ новостей. База знаний:

{facts}

Анализируй ТОЛЬКО научные открытия, исследования, технологии и инновации. 
Фокусируйся на: медицине, биологии, физике, химии, космосе, ИИ, робототехнике, экологии.
Игнорируй политику, экономику, спорт.

Пиши профессионально, но доступно."""

        print(f"🔬 Создаем научный Flash-Lite ({len(system_instruction)} символов)...")
        
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction
        )
        
        # Настройки для Lite
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=200,
        )
        
        print("🔬 Тестируем научный Flash-Lite...")
        test_response = model.generate_content(
            "Готов анализировать научные новости?",
            generation_config=generation_config
        )
        
        if test_response and test_response.text:
            print(f"✅ Научный Flash-Lite готов: {test_response.text}")
            return model, test_response.text
        else:
            print("❌ Научный Flash-Lite: пустой ответ")
            return None, "Пустой ответ"
            
    except Exception as e:
        print(f"❌ Ошибка научного Flash-Lite: {e}")
        
        # Fallback
        try:
            print("🔬 Научный Flash-Lite fallback...")
            simple_system = "Ты аналитик научных новостей. Анализируй открытия, исследования, технологии."
            
            model = genai.GenerativeModel(
                model_name=selected_model,
                system_instruction=simple_system
            )
            
            test_response = model.generate_content(
                "Готов анализировать науку?",
                generation_config=generation_config
            )
            
            if test_response and test_response.text:
                print(f"✅ Научный Flash-Lite fallback: {test_response.text}")
                return model, test_response.text
                
        except Exception as e2:
            print(f"❌ Научный Flash-Lite fallback: {e2}")
        
        return None, str(e)

def generate_science_commentary(model, science_news):
    """Генерирует научный анализ через Flash-Lite"""
    if not model or not science_news:
        return None, None
    
    print("🔬 Flash-Lite анализирует научные новости...")
    
    # Формируем список научных новостей
    news_text = ""
    for i, item in enumerate(science_news, 1):
        news_text += f"{i}. 🔬 {item['title']}\n"
        if item['description']:
            desc = item['description'][:250] + "..." if len(item['description']) > 250 else item['description']
            news_text += f"   {desc}\n"
        news_text += f"   ({item['source']})\n\n"
    
    # Специализированный научный промпт
    analysis_prompt = f"""Проанализируй научные новости и открытия:

{news_text}

Дай экспертный анализ:

🔬 КЛЮЧЕВЫЕ ОТКРЫТИЯ:
- Самые важные научные достижения
- Прорывные исследования

🚀 ТЕХНОЛОГИЧЕСКИЕ ТРЕНДЫ:
- Новые технологии и инновации
- Развитие в ИИ, медицине, космосе

🧬 МЕДИЦИНСКИЕ ДОСТИЖЕНИЯ:
- Новые методы лечения
- Биотехнологии и генетика

🌍 ВЛИЯНИЕ НА БУДУЩЕЕ:
- Как эти открытия изменят мир
- Практическое применение

Пиши научно, но понятно."""
    
    try:
        # Настройки для научного анализа
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            max_output_tokens=3000,  # Больше для подробного научного анализа
        )
        
        print(f"🔬 Flash-Lite генерирует научный анализ ({len(analysis_prompt)} символов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"✅ Научный анализ готов ({len(response.text)} символов)")
            return response.text, analysis_prompt
        else:
            return "Flash-Lite: ошибка генерации научного анализа", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка научного анализа Flash-Lite: {e}")
        return f"Научный Flash-Lite ошибка: {e}", analysis_prompt

def save_science_results(commentary, science_news, init_response, prompt):
    """Сохраняет результаты научного анализа"""
    if not ensure_directory_exists('science_commentary'):
        return False
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond}"
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        main_filename = f'science_commentary/science_analysis_{timestamp}.md'
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# 🔬 Анализ Научных Новостей - Gemini 2.0 Flash-Lite\n")
            f.write(f"## {date_formatted}\n\n")
            f.write(f"*Научный анализ от Gemini 2.0 Flash-Lite*\n\n")
            f.write("---\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## 🔬 Научные новости:\n\n")
            
            for i, item in enumerate(science_news, 1):
                f.write(f"### {i}. 🔬 {item['title']}\n")
                if item['description']:
                    f.write(f"{item['description']}\n\n")
                f.write(f"**Источник:** {item['source']}\n")
                if item['link']:
                    f.write(f"**Ссылка:** {item['link']}\n")
                f.write("\n---\n\n")
        
        stats_filename = f'science_commentary/science_stats_{timestamp}.txt'
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== НАУЧНЫЙ GEMINI 2.0 FLASH-LITE ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write(f"Модель: Gemini 2.0 Flash-Lite (Science)\n")
            f.write(f"Научных новостей: {len(science_news)}\n")
            f.write(f"Длина анализа: {len(commentary)} символов\n")
            f.write(f"ID: {timestamp}\n")
        
        print(f"🔬 Научный анализ сохранён: {timestamp}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения научного анализа: {e}")
        return False

def main():
    try:
        print("🔬 === GEMINI 2.0 FLASH-LITE НАУЧНЫЙ АНАЛИЗАТОР ===")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ Нет API ключа")
            return False
        
        genai.configure(api_key=api_key)
        
        # Загружаем факты
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        # Инициализация научного Flash-Lite
        model, init_response = initialize_science_flash_lite(facts)
        if not model:
            print("❌ Научный Flash-Lite не инициализирован")
            return False
        
        time.sleep(1)
        
        # Получаем ТОЛЬКО научные новости
        science_news = get_science_news()
        if not science_news:
            print("❌ Нет научных новостей")
            return False
        
        time.sleep(1)
        
        # Научный анализ Flash-Lite
        commentary, prompt = generate_science_commentary(model, science_news)
        if not commentary:
            print("❌ Flash-Lite не создал научный анализ")
            return False
        
        # Сохранение в папку science_commentary
        return save_science_results(commentary, science_news, init_response, prompt)
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА НАУЧНОГО FLASH-LITE: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
