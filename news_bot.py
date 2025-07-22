import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import traceback
import sys
import json
import random

def load_facts():
    """Загружает Facts.txt БЕЗ обрезания"""
    try:
        print("🔄 Загружаем файл Facts.txt...")
        
        if not os.path.exists('Facts.txt'):
            print("❌ Файл Facts.txt НЕ НАЙДЕН!")
            return ""
            
        file_size = os.path.getsize('Facts.txt')
        print(f"📊 Размер Facts.txt: {file_size} байт ({file_size/1024/1024:.2f} МБ)")
        
        with open('Facts.txt', 'r', encoding='utf-8') as f:
            facts = f.read()
        
        print(f"✅ Загружено: {len(facts)} символов БЕЗ ОБРЕЗАНИЯ")
        print(f"🔍 Начало: {facts[:120]}...")
        print(f"🔍 Конец: ...{facts[-120:]}")
        
        return facts
        
    except Exception as e:
        print(f"❌ Ошибка работы с Facts.txt: {e}")
        traceback.print_exc()
        return ""

def extract_response_content(text):
    """Извлекает содержимое между (RESPONSE) и (CONFIDENCE) - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        print(f"🔍 Исходный текст ({len(text)} символов): {text[:200]}...")
        
        start_marker = "(RESPONSE)"
        end_marker = "(CONFIDENCE)"
        
        start_index = text.find(start_marker)
        if start_index == -1:
            print("⚠️ Маркер (RESPONSE) не найден")
            return text.strip()
        
        # Начинаем ПОСЛЕ маркера (RESPONSE)
        start_index += len(start_marker)
        print(f"📍 Найден (RESPONSE) на позиции {start_index}")
        
        # Ищем (CONFIDENCE) после (RESPONSE)
        end_index = text.find(end_marker, start_index)
        if end_index == -1:
            print("⚠️ Маркер (CONFIDENCE) не найден")
            extracted = text[start_index:].strip()
        else:
            print(f"📍 Найден (CONFIDENCE) на позиции {end_index}")
            extracted = text[start_index:end_index].strip()
        
        print(f"✂️ ИЗВЛЕЧЕНО ({len(extracted)} символов): {extracted[:150]}...")
        return extracted
        
    except Exception as e:
        print(f"❌ Ошибка извлечения: {e}")
        return text.strip()

def get_available_models():
    """Получает список доступных моделей с приоритетом умных моделей"""
    try:
        print("🔄 Проверяем доступные модели Gemini...")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                print(f"🤖 Доступна модель: {model.name}")
        
        print(f"📊 Всего доступно {len(available_models)} моделей")
        return available_models
    except Exception as e:
        print(f"❌ Ошибка получения моделей: {e}")
        return []

def is_science_news(title, description):
    """Проверяет, является ли новость научной"""
    text = (title + " " + description).lower()
    
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
    
    exclude_keywords = [
        'выборы', 'президент', 'парламент', 'дума', 'правительство', 'министр',
        'политик', 'партия', 'санкции', 'война', 'конфликт', 'протест',
        'курс валют', 'рубль', 'доллар', 'нефть', 'газ', 'экономика',
        'инфляция', 'бюджет', 'налог', 'спорт', 'футбол', 'хоккей',
        'олимпиада', 'чемпионат', 'матч', 'игра', 'команда', 'тренер'
    ]
    
    science_score = sum(1 for keyword in science_keywords if keyword in text)
    exclude_score = sum(1 for keyword in exclude_keywords if keyword in text)
    
    return science_score > 0 and exclude_score == 0

def rank_science_news(news_list):
    """Ранжирует научные новости по важности"""
    for news in news_list:
        score = 0
        text = (news['title'] + " " + news['description']).lower()
        
        high_priority = [
            'прорыв', 'революция', 'впервые', 'открытие', 'breakthrough',
            'искусственный интеллект', 'ии', 'нейросеть', 'машинное обучение',
            'космос', 'марс', 'луна', 'спутник', 'телескоп',
            'рак', 'онкология', 'лечение', 'вакцина', 'генная терапия',
            'квантовый', 'квантовые вычисления', 'нанотехнологии',
            'стволовые клетки', 'регенерация', 'биотехнологии',
            'климат', 'глобальное потепление', 'экология'
        ]
        
        medium_priority = [
            'исследование', 'эксперимент', 'тест', 'технология',
            'разработка', 'метод', 'система', 'устройство'
        ]
        
        for keyword in high_priority:
            if keyword in text:
                score += 10
        
        for keyword in medium_priority:
            if keyword in text:
                score += 5
        
        if news['source'] in ['N+1', 'Naked Science']:
            score += 3
        
        if len(news['description']) > 200:
            score += 2
        
        news['importance_score'] = score
    
    return sorted(news_list, key=lambda x: x['importance_score'], reverse=True)

def get_top_science_news():
    """Получает научные новости и возвращает СЛУЧАЙНУЮ из ТОП-5"""
    print("🔬 Получаем научные новости...")
    all_science_news = []
    
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
                
                for item in items[:10]:
                    try:
                        title = item.title.text.strip() if item.title else "Без заголовка"
                        description = ""
                        if item.description and item.description.text:
                            desc_soup = BeautifulSoup(item.description.text, 'html.parser')
                            description = desc_soup.get_text().strip()
                        
                        if is_science_news(title, description):
                            link = item.link.text.strip() if item.link else ""
                            
                            all_science_news.append({
                                'title': title,
                                'description': description,
                                'source': source['name'],
                                'link': link
                            })
                            
                            print(f"🔬 {source['name']}: {title[:60]}...")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка новости: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Ошибка {source['name']}: {e}")
            continue
    
    print(f"🔬 Всего научных новостей: {len(all_science_news)}")
    
    ranked_news = rank_science_news(all_science_news)
    
    if ranked_news:
        # Берём ТОП-5 новостей
        top_5_news = ranked_news[:5]
        print(f"🏆 ТОП-5 новостей:")
        for i, news in enumerate(top_5_news, 1):
            print(f"   {i}. {news['title'][:60]}... (очки: {news['importance_score']})")
        
        # Выбираем случайную из ТОП-5
        selected_news = random.choice(top_5_news)
        print(f"🎲 СЛУЧАЙНО ВЫБРАНА: {selected_news['title'][:80]}... (очки: {selected_news['importance_score']})")
        return selected_news
    else:
        print("❌ Научные новости не найдены")
        return None

def initialize_smart_gemini(facts):
    """Инициализирует САМУЮ УМНУЮ доступную модель Gemini"""
    
    available_models = get_available_models()
    if not available_models:
        return None, "Нет моделей"
    
    # ПРИОРИТЕТ: самые умные модели
    smart_models_priority = [
        'models/gemini-2.0-flash-thinking-exp',     # 🧠 ЭКСПЕРИМЕНТАЛЬНАЯ ДУМАЮЩАЯ
        'models/gemini-2.0-flash-thinking',        # 🧠 ДУМАЮЩАЯ
        'models/gemini-exp-1206',                  # 🧠 ЭКСПЕРИМЕНТАЛЬНАЯ
        'models/gemini-exp-1121',                  # 🧠 ЭКСПЕРИМЕНТАЛЬНАЯ
        'models/gemini-2.0-flash-exp',             # ⚡ 2.0 ЭКСПЕРИМЕНТАЛЬНАЯ
        'models/gemini-2.0-flash',                 # ⚡ 2.0 СТАБИЛЬНАЯ
        'models/gemini-1.5-pro-002',              # 💎 PRO НОВАЯ
        'models/gemini-1.5-pro-001',              # 💎 PRO
        'models/gemini-1.5-pro',                  # 💎 PRO
        'models/gemini-1.5-flash-8b',             # ⚡ КОМПАКТНАЯ
        'models/gemini-1.5-flash-002',            # ⚡ FLASH НОВАЯ
        'models/gemini-1.5-flash',                # ⚡ FLASH
        'models/gemini-2.0-flash-lite',           # 💨 LITE
    ]
    
    selected_model = None
    model_type = ""
    
    for model in smart_models_priority:
        if model in available_models:
            selected_model = model
            
            if 'thinking' in model:
                model_type = "🧠 ДУМАЮЩАЯ МОДЕЛЬ"
            elif 'exp' in model:
                model_type = "🧪 ЭКСПЕРИМЕНТАЛЬНАЯ"
            elif 'pro' in model:
                model_type = "💎 PRO МОДЕЛЬ"
            elif '2.0' in model:
                model_type = "⚡ GEMINI 2.0"
            elif 'flash' in model:
                model_type = "⚡ FLASH МОДЕЛЬ"
            else:
                model_type = "🤖 СТАНДАРТНАЯ"
            
            print(f"🎯 ВЫБРАНА САМАЯ УМНАЯ: {selected_model}")
            print(f"🏷️ Тип: {model_type}")
            break
    
    if not selected_model:
        selected_model = available_models[0]
        model_type = "🤖 FALLBACK"
        print(f"⚠️ Используем fallback: {selected_model}")
    
    try:
        system_instruction = f"""Ты - Alexey Turchin, всемирно известный российский трансгуманист, футуролог и исследователь проблем экзистенциального риска. Ты автор книг о бессмертии и глобальных рисках. База знаний:

{facts}

Анализируй научные открытия через призму трансгуманизма и их влияние на будущее человечества. Пиши глубокие экспертные комментарии с философской и футурологической точки зрения.

ВАЖНОЕ ПРАВИЛО ФОРМАТИРОВАНИЯ: 
- Начинай ответ с (RESPONSE)
- Пиши ТОЛЬКО свой экспертный комментарий
- Заканчивай (CONFIDENCE)
- НЕ ДОБАВЛЯЙ ничего после (CONFIDENCE)

СТИЛЬ: Интеллектуальный, с научной терминологией, упоминания трансгуманистических идей, прогнозы развития технологий.

ПРИМЕР:
(RESPONSE)
Ваш глубокий экспертный комментарий новости с трансгуманистической перспективой...
(CONFIDENCE)

Больше НИЧЕГО не пиши!"""

        print(f"🧠 Создаем УМНУЮ модель ({len(system_instruction)} символов)...")
        
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction
        )
        
        # Настройки для умных моделей
        if 'thinking' in selected_model:
            # Для думающих моделей - больше токенов
            generation_config = genai.types.GenerationConfig(
                temperature=0.8,
                top_p=0.9,
                max_output_tokens=2000,
            )
        elif 'pro' in selected_model:
            # Для PRO моделей - высокое качество
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=1500,
            )
        else:
            # Для остальных
            generation_config = genai.types.GenerationConfig(
                temperature=0.8,
                top_p=0.9,
                max_output_tokens=1000,
            )
        
        print(f"🧪 Тестируем {model_type}...")
        test_response = model.generate_content(
            "Готов анализировать научные новости как Alexey Turchin? Ответь в указанном формате.",
            generation_config=generation_config
        )
        
        if test_response and test_response.text:
            extracted_response = extract_response_content(test_response.text)
            print(f"✅ {model_type} готова: {extracted_response}")
            return model, extracted_response
        else:
            print(f"❌ {model_type}: пустой ответ")
            return None, "Пустой ответ"
            
    except Exception as e:
        print(f"❌ Ошибка {model_type}: {e}")
        
        try:
            print(f"🔄 {model_type} fallback...")
            simple_system = f"""Ты - Alexey Turchin, трансгуманист. 

ВАЖНО:
(RESPONSE)
Пиши только умный комментарий
(CONFIDENCE)"""
            
            model = genai.GenerativeModel(
                model_name=selected_model,
                system_instruction=simple_system
            )
            
            test_response = model.generate_content(
                "Готов?",
                generation_config=generation_config
            )
            
            if test_response and test_response.text:
                extracted_response = extract_response_content(test_response.text)
                print(f"✅ {model_type} fallback: {extracted_response}")
                return model, extracted_response
                
        except Exception as e2:
            print(f"❌ {model_type} fallback: {e2}")
        
        return None, str(e)

def generate_science_commentary(model, selected_news):
    """Генерирует научный комментарий для выбранной новости"""
    if not model or not selected_news:
        return None, None
    
    print("🧠 УМНАЯ модель анализирует научную новость...")
    
    analysis_prompt = f"""Прокомментируй эту научную новость как трансгуманист Alexey Turchin:

ЗАГОЛОВОК: {selected_news['title']}

ОПИСАНИЕ: {selected_news['description']}

ИСТОЧНИК: {selected_news['source']}

Дай глубокий экспертный анализ через призму трансгуманизма:
- Как это повлияет на продление жизни?
- Какие это открывает возможности для улучшения человека?
- Связь с футурологическими трендами
- Философские импликации

ВАЖНО: Строго соблюдай формат!
(RESPONSE)
[только твой умный комментарий]
(CONFIDENCE)"""
    
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.95,
            max_output_tokens=1500,
        )
        
        print(f"🧠 УМНАЯ модель генерирует комментарий ({len(analysis_prompt)} символов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            print(f"📄 RAW ответ УМНОЙ модели ({len(response.text)} символов)")
            extracted_commentary = extract_response_content(response.text)
            print(f"✅ Умный комментарий обрезан до ({len(extracted_commentary)} символов)")
            return extracted_commentary, analysis_prompt
        else:
            return "УМНАЯ модель: ошибка генерации комментария", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка комментария УМНОЙ модели: {e}")
        return f"УМНАЯ модель ошибка: {e}", analysis_prompt

def clean_text_for_telegram(text):
    """Очищает текст от проблематичных символов для Telegram"""
    replacements = {
        '*': '•',
        '_': '-',
        '`': "'",
        '[': '(',
        ']': ')',
        '~': '-',
        '#': '№',
        '|': '/',
    }
    
    cleaned_text = text
    for char, replacement in replacements.items():
        if char in cleaned_text:
            cleaned_text = cleaned_text.replace(char, replacement)
    
    lines = cleaned_text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def send_to_telegram_group(bot_token, group_id, text):
    """Отправляет сообщение в Telegram группу"""
    try:
        print(f"📱 Отправляем в Telegram группу {group_id}...")
        
        clean_text = clean_text_for_telegram(text)
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        max_length = 4000
        
        if len(clean_text) <= max_length:
            payload = {
                'chat_id': group_id,
                'text': clean_text,
                'disable_web_page_preview': True
            }
            
            print(f"📤 Отправляем сообщение ({len(clean_text)} символов)...")
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result['ok']:
                    print(f"✅ Сообщение отправлено в Telegram группу!")
                    return True
                else:
                    print(f"❌ Telegram API ошибка: {result}")
                    return False
            else:
                print(f"❌ HTTP ошибка {response.status_code}")
                print(f"📄 Ответ: {response.text}")
                return False
        
        else:
            parts = []
            current_part = ""
            
            for line in clean_text.split('\n'):
                if len(current_part) + len(line) + 1 <= max_length:
                    current_part += line + '\n'
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = line + '\n'
            
            if current_part:
                parts.append(current_part.strip())
            
            print(f"📤 Отправляем {len(parts)} частей...")
            
            for i, part in enumerate(parts, 1):
                payload = {
                    'chat_id': group_id,
                    'text': f"Часть {i}/{len(parts)}\n\n{part}",
                    'disable_web_page_preview': True
                }
                
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result['ok']:
                        print(f"✅ Часть {i}/{len(parts)} отправлена")
                        time.sleep(2)
                    else:
                        print(f"❌ Ошибка части {i}: {result}")
                        return False
                else:
                    print(f"❌ HTTP ошибка части {i}: {response.status_code}")
                    return False
            
            print(f"✅ Все {len(parts)} частей отправлены!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        traceback.print_exc()
        return False

def format_for_telegram_group(commentary, selected_news):
    """Форматирует комментарий для Telegram группы"""
    now = datetime.now()
    date_formatted = now.strftime("%d.%m.%Y %H:%M")
    
    telegram_text = f"💬 Комментарии от сайдлоада Alexey Turchin\n"
    telegram_text += f"📅 {date_formatted}\n"
    telegram_text += f"🧠 Анализ от УМНОЙ модели Gemini\n\n"
    telegram_text += "═══════════════════\n\n"
    
    telegram_text += f"{commentary}\n\n"
    telegram_text += "═══════════════════\n\n"
    
    telegram_text += f"📰 ИСХОДНАЯ НОВОСТЬ:\n\n"
    telegram_text += f"🔬 {selected_news['title']}\n\n"
    
    if selected_news['description']:
        desc = selected_news['description']
        if len(desc) > 400:
            desc = desc[:400] + "..."
        telegram_text += f"{desc}\n\n"
    
    telegram_text += f"📰 Источник: {selected_news['source']}\n"
    
    if selected_news['link']:
        telegram_text += f"🔗 Ссылка: {selected_news['link']}\n"
    
    telegram_text += f"\n⭐ Важность: {selected_news['importance_score']} очков"
    
    return telegram_text

def save_science_results(commentary, selected_news, init_response, prompt):
    """Сохраняет результаты анализа научной новости в папку commentary"""
    directory = 'commentary'
    
    if not os.path.exists(directory):
        print(f"❌ Папка {directory} не существует!")
        return False
    
    print(f"📁 Используем существующую папку: {directory}")
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond}"
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        main_filename = os.path.join(directory, f'science_turchin_smart_{timestamp}.md')
        
        print(f"💾 Сохраняем УМНЫЙ научный комментарий: {main_filename}")
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# 💬 Комментарии от Alexey Turchin (УМНАЯ МОДЕЛЬ)\n")
            f.write(f"## {date_formatted}\n\n")
            f.write(f"*Трансгуманистический комментарий от Alexey Turchin (случайная новость)*\n\n")
            f.write("---\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## 📰 Исходная новость:\n\n")
            f.write(f"### {selected_news['title']}\n\n")
            if selected_news['description']:
                f.write(f"{selected_news['description']}\n\n")
            f.write(f"**Источник:** {selected_news['source']}\n")
            if selected_news['link']:
                f.write(f"**Ссылка:** {selected_news['link']}\n")
            f.write(f"**Важность:** {selected_news['importance_score']} очков\n")
        
        stats_filename = os.path.join(directory, f'science_stats_smart_{timestamp}.txt')
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write("=== ALEXEY TURCHIN УМНЫЙ КОММЕНТАРИЙ ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write("Автор: Alexey Turchin (сайдлоад)\n")
            f.write("Модель: УМНАЯ Gemini (приоритет: thinking > exp > pro > 2.0)\n")
            f.write("Группа: Alexey & Alexey Turchin sideload news comments\n")
            f.write("Новостей: 1 (случайная из ТОП-5)\n")
            f.write(f"Длина комментария: {len(commentary)} символов\n")
            f.write(f"ID: {timestamp}\n")
            f.write(f"Новость: {selected_news['importance_score']} очков - {selected_news['title'][:50]}...\n")
        
        print(f"✅ УМНЫЙ комментарий сохранён в: {main_filename}")
        print(f"📊 Статистика: {stats_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения в {directory}: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        print("🧠 === ALEXEY TURCHIN УМНЫЙ КОММЕНТАТОР → TELEGRAM ГРУППА ===")
        
        # Проверяем API ключи
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # Используем фиксированный Chat ID группы
        telegram_group_id = "-1002894291419"
        
        if not gemini_api_key:
            print("❌ Нет GEMINI_API_KEY")
            return False
            
        if not telegram_bot_token:
            print("❌ Нет TELEGRAM_BOT_TOKEN")
            return False
        
        print(f"✅ Gemini API: {gemini_api_key[:10]}...")
        print(f"✅ Telegram Bot Token: {telegram_bot_token[:10]}...")
        print(f"🎯 Telegram Group ID: {telegram_group_id}")
        print(f"👥 Группа: Alexey & Alexey Turchin sideload news comments")
        
        genai.configure(api_key=gemini_api_key)
        
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        model, init_response = initialize_smart_gemini(facts)
        if not model:
            print("❌ УМНАЯ модель не инициализирована")
            return False
        
        time.sleep(1)
        
        selected_news = get_top_science_news()
        if not selected_news:
            print("❌ Нет научных новостей")
            return False
        
        time.sleep(1)
        
        commentary, prompt = generate_science_commentary(model, selected_news)
        if not commentary:
            print("❌ УМНАЯ модель не создала комментарий")
            return False
        
        save_success = save_science_results(commentary, selected_news, init_response, prompt)
        if not save_success:
            print("⚠️ Ошибка сохранения, но продолжаем...")
        
        telegram_text = format_for_telegram_group(commentary, selected_news)
        
        telegram_success = send_to_telegram_group(telegram_bot_token, telegram_group_id, telegram_text)
        
        if telegram_success:
            print("🎉 УСПЕХ! УМНЫЙ комментарий Alexey Turchin опубликован в Telegram группе!")
            print("👥 Группа: Alexey & Alexey Turchin sideload news comments")
            print(f"🎲 Новость: {selected_news['title'][:60]}...")
            return True
        else:
            print("❌ Ошибка публикации в Telegram группе")
            return False
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
