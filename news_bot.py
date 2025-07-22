import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import traceback
import sys
import json

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
    """Извлекает содержимое между (RESPONSE) и (CONFIDENCE)"""
    try:
        # Ищем начало (RESPONSE)
        start_marker = "(RESPONSE)"
        end_marker = "(CONFIDENCE)"
        
        start_index = text.find(start_marker)
        if start_index == -1:
            print("⚠️ Маркер (RESPONSE) не найден, возвращаем полный текст")
            return text.strip()
        
        # Начинаем после маркера (RESPONSE)
        start_index += len(start_marker)
        
        # Ищем конец (CONFIDENCE)
        end_index = text.find(end_marker, start_index)
        if end_index == -1:
            print("⚠️ Маркер (CONFIDENCE) не найден, берем текст до конца")
            extracted = text[start_index:].strip()
        else:
            extracted = text[start_index:end_index].strip()
        
        print(f"✂️ Извлечено содержимое между маркерами ({len(extracted)} символов)")
        return extracted
        
    except Exception as e:
        print(f"❌ Ошибка извлечения содержимого: {e}")
        return text.strip()

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

def rank_science_news(news_list):
    """Ранжирует научные новости по важности"""
    for news in news_list:
        score = 0
        text = (news['title'] + " " + news['description']).lower()
        
        # Высокоприоритетные темы
        high_priority = [
            'прорыв', 'революция', 'впервые', 'открытие', 'breakthrough',
            'искусственный интеллект', 'ии', 'нейросеть', 'машинное обучение',
            'космос', 'марс', 'луна', 'спутник', 'телескоп',
            'рак', 'онкология', 'лечение', 'вакцина', 'генная терапия',
            'квантовый', 'квантовые вычисления', 'нанотехнологии',
            'стволовые клетки', 'регенерация', 'биотехнологии',
            'климат', 'глобальное потепление', 'экология'
        ]
        
        # Средний приоритет
        medium_priority = [
            'исследование', 'эксперимент', 'тест', 'технология',
            'разработка', 'метод', 'система', 'устройство'
        ]
        
        # Бонусы за ключевые слова
        for keyword in high_priority:
            if keyword in text:
                score += 10
        
        for keyword in medium_priority:
            if keyword in text:
                score += 5
        
        # Бонус за свежесть (если источник авторитетный)
        if news['source'] in ['N+1', 'Naked Science']:
            score += 3
        
        # Бонус за длину описания (более подробные новости)
        if len(news['description']) > 200:
            score += 2
        
        news['importance_score'] = score
    
    # Сортируем по важности
    return sorted(news_list, key=lambda x: x['importance_score'], reverse=True)

def get_top_science_news():
    """Получает ТОП-3 научные новости"""
    print("🔬 Получаем ТОП-3 научные новости...")
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
                
                for item in items[:10]:  # Берём только первые 10 для анализа
                    try:
                        title = item.title.text.strip() if item.title else "Без заголовка"
                        description = ""
                        if item.description and item.description.text:
                            desc_soup = BeautifulSoup(item.description.text, 'html.parser')
                            description = desc_soup.get_text().strip()
                        
                        # ФИЛЬТРАЦИЯ: только научные новости
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
    
    # Ранжируем по важности
    ranked_news = rank_science_news(all_science_news)
    
    # Берём ТОП-3
    top_3_news = ranked_news[:3]
    
    print(f"🏆 ТОП-3 научные новости:")
    for i, news in enumerate(top_3_news, 1):
        print(f"   {i}. {news['title'][:80]}... (очки: {news['importance_score']})")
    
    return top_3_news

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

Пиши профессионально, но доступно.

ВАЖНО: Всегда начинай ответ с (RESPONSE) и заканчивай (CONFIDENCE)."""

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
            # Извлекаем содержимое между маркерами
            extracted_response = extract_response_content(test_response.text)
            print(f"✅ Научный Flash-Lite готов: {extracted_response}")
            return model, extracted_response
        else:
            print("❌ Научный Flash-Lite: пустой ответ")
            return None, "Пустой ответ"
            
    except Exception as e:
        print(f"❌ Ошибка научного Flash-Lite: {e}")
        
        # Fallback
        try:
            print("🔬 Научный Flash-Lite fallback...")
            simple_system = "Ты аналитик научных новостей. Анализируй открытия, исследования, технологии. Всегда начинай ответ с (RESPONSE) и заканчивай (CONFIDENCE)."
            
            model = genai.GenerativeModel(
                model_name=selected_model,
                system_instruction=simple_system
            )
            
            test_response = model.generate_content(
                "Готов анализировать науку?",
                generation_config=generation_config
            )
            
            if test_response and test_response.text:
                extracted_response = extract_response_content(test_response.text)
                print(f"✅ Научный Flash-Lite fallback: {extracted_response}")
                return model, extracted_response
                
        except Exception as e2:
            print(f"❌ Научный Flash-Lite fallback: {e2}")
        
        return None, str(e)

def generate_science_commentary(model, top_3_news):
    """Генерирует научный анализ ТОП-3 новостей через Flash-Lite"""
    if not model or not top_3_news:
        return None, None
    
    print("🔬 Flash-Lite анализирует ТОП-3 научные новости...")
    
    # Формируем список ТОП-3 научных новостей
    news_text = "🏆 ТОП-3 НАУЧНЫЕ НОВОСТИ:\n\n"
    for i, item in enumerate(top_3_news, 1):
        news_text += f"🥇 {i}. {item['title']}\n"
        if item['description']:
            news_text += f"📋 {item['description']}\n"
        news_text += f"📰 Источник: {item['source']}\n"
        news_text += f"🎯 Важность: {item['importance_score']} очков\n\n"
    
    # Специализированный научный промпт для ТОП-3
    analysis_prompt = f"""{news_text}

Проанализируй эти ТОП-3 научные открытия и дай экспертный анализ:

🔬 КЛЮЧЕВЫЕ ОТКРЫТИЯ:
- Что самое важное в каждом открытии?
- Какие прорывы произошли?

🚀 НАУЧНАЯ ЗНАЧИМОСТЬ:
- Почему эти открытия важны для науки?
- Какие области знаний затронуты?

🧬 ПРАКТИЧЕСКОЕ ПРИМЕНЕНИЕ:
- Как это поможет людям?
- Когда можно ждать внедрения?

🌍 ВЛИЯНИЕ НА БУДУЩЕЕ:
- Как эти открытия изменят мир?
- Какие новые возможности открываются?

Пиши научно, но понятно. Фокусируйся на значимости открытий.

Обязательно начни ответ с (RESPONSE) и закончи (CONFIDENCE)."""
    
    try:
        # Настройки для научного анализа
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            max_output_tokens=2000,  # Достаточно для анализа 3 новостей
        )
        
        print(f"🔬 Flash-Lite генерирует анализ ТОП-3 ({len(analysis_prompt)} символов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            # Извлекаем содержимое между маркерами
            extracted_commentary = extract_response_content(response.text)
            print(f"✅ Анализ ТОП-3 готов ({len(extracted_commentary)} символов)")
            return extracted_commentary, analysis_prompt
        else:
            return "Flash-Lite: ошибка генерации анализа ТОП-3", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка анализа ТОП-3 Flash-Lite: {e}")
        return f"Научный Flash-Lite ошибка: {e}", analysis_prompt

def clean_text_for_telegram(text):
    """Очищает текст от проблематичных символов для Telegram"""
    # Удаляем или заменяем проблематичные символы Markdown
    problematic_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Заменяем на безопасные альтернативы
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
    
    # Удаляем лишние пробелы и переносы
    lines = cleaned_text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def send_to_telegram(bot_token, channel_id, text):
    """Отправляет сообщение в Telegram канал"""
    try:
        print(f"📱 Отправляем в Telegram канал {channel_id}...")
        
        # Очищаем текст от проблематичных символов
        clean_text = clean_text_for_telegram(text)
        
        # Telegram Bot API URL
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Разбиваем длинный текст на части (максимум 4000 символов для безопасности)
        max_length = 4000
        
        if len(clean_text) <= max_length:
            # Отправляем как одно сообщение
            payload = {
                'chat_id': channel_id,
                'text': clean_text,
                'disable_web_page_preview': True
            }
            
            print(f"📤 Отправляем сообщение ({len(clean_text)} символов)...")
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result['ok']:
                    print(f"✅ Сообщение отправлено в Telegram!")
                    return True
                else:
                    print(f"❌ Telegram API ошибка: {result}")
                    return False
            else:
                print(f"❌ HTTP ошибка {response.status_code}")
                return False
        
        else:
            # Разбиваем на части
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
            
            # Отправляем каждую часть
            for i, part in enumerate(parts, 1):
                payload = {
                    'chat_id': channel_id,
                    'text': f"Часть {i}/{len(parts)}\n\n{part}",
                    'disable_web_page_preview': True
                }
                
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result['ok']:
                        print(f"✅ Часть {i}/{len(parts)} отправлена")
                        time.sleep(2)  # Задержка между сообщениями
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

def format_for_telegram(commentary, top_3_news):
    """Форматирует анализ для Telegram (простой текст без Markdown)"""
    now = datetime.now()
    date_formatted = now.strftime("%d.%m.%Y %H:%M")
    
    # Заголовок
    telegram_text = f"🔬 ТОП-3 Научные Открытия\n"
    telegram_text += f"📅 {date_formatted}\n"
    telegram_text += f"🤖 Анализ от Gemini 2.0 Flash-Lite\n\n"
    telegram_text += "═════════════════════\n\n"
    
    # Анализ от ИИ
    telegram_text += f"📊 ЭКСПЕРТНЫЙ АНАЛИЗ:\n\n"
    telegram_text += f"{commentary}\n\n"
    telegram_text += "═════════════════════\n\n"
    
    # ТОП-3 новости
    telegram_text += f"🏆 ТОП-3 НАУЧНЫЕ НОВОСТИ:\n\n"
    
    for i, item in enumerate(top_3_news, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        telegram_text += f"{medal} {i}. {item['title']}\n"
        telegram_text += f"⭐ Важность: {item['importance_score']} очков\n\n"
        
        if item['description']:
            # Ограничиваем описание
            desc = item['description']
            if len(desc) > 300:
                desc = desc[:300] + "..."
            telegram_text += f"{desc}\n\n"
        
        telegram_text += f"📰 Источник: {item['source']}\n"
        
        if item['link']:
            telegram_text += f"🔗 Ссылка: {item['link']}\n"
        
        telegram_text += "\n───────────────────\n\n"
    
    # Подпись
    telegram_text += "🤖 Автоматический анализ научных новостей\n"
    telegram_text += "⚡ Powered by Gemini 2.0 Flash-Lite"
    
    return telegram_text

def save_science_results(commentary, top_3_news, init_response, prompt):
    """Сохраняет результаты анализа ТОП-3 научных новостей в папку commentary"""
    directory = 'commentary'  # Используем существующую папку
    
    # Проверяем существование папки
    if not os.path.exists(directory):
        print(f"❌ Папка {directory} не существует!")
        return False
    
    print(f"📁 Используем существующую папку: {directory}")
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"-{now.microsecond}"
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        main_filename = os.path.join(directory, f'science_top3_{timestamp}.md')
        
        print(f"💾 Сохраняем научный анализ: {main_filename}")
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# 🏆 ТОП-3 Научные Новости - Gemini 2.0 Flash-Lite\n")
            f.write(f"## {date_formatted}\n\n")
            f.write(f"*Анализ топ-3 научных открытий от Gemini 2.0 Flash-Lite*\n\n")
            f.write("---\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## 🏆 ТОП-3 Научные новости:\n\n")
            
            for i, item in enumerate(top_3_news, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                f.write(f"### {medal} {i}. {item['title']}\n")
                f.write(f"**Важность:** {item['importance_score']} очков\n\n")
                if item['description']:
                    f.write(f"{item['description']}\n\n")
                f.write(f"**Источник:** {item['source']}\n")
                if item['link']:
                    f.write(f"**Ссылка:** {item['link']}\n")
                f.write("\n---\n\n")
        
        stats_filename = os.path.join(directory, f'science_stats_{timestamp}.txt')
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write("=== НАУЧНЫЙ GEMINI 2.0 FLASH-LITE ТОП-3 ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write("Модель: Gemini 2.0 Flash-Lite (Science)\n")
            f.write("Научных новостей: ТОП-3\n")
            f.write(f"Длина анализа: {len(commentary)} символов\n")
            f.write(f"ID: {timestamp}\n")
            for i, item in enumerate(top_3_news, 1):
                f.write(f"Новость {i}: {item['importance_score']} очков - {item['title'][:50]}...\n")
        
        print(f"✅ ТОП-3 анализ сохранён в: {main_filename}")
        print(f"📊 Статистика: {stats_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения в {directory}: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        print("🏆 === GEMINI 2.0 FLASH-LITE ТОП-3 НАУЧНЫЙ АНАЛИЗАТОР + TELEGRAM ===")
        
        # Проверяем API ключи
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        
        if not gemini_api_key:
            print("❌ Нет GEMINI_API_KEY")
            return False
            
        if not telegram_bot_token:
            print("❌ Нет TELEGRAM_BOT_TOKEN")
            return False
            
        if not telegram_channel_id:
            print("❌ Нет TELEGRAM_CHANNEL_ID")
            return False
        
        print(f"✅ Gemini API: {gemini_api_key[:10]}...")
        print(f"✅ Telegram Bot Token: {telegram_bot_token[:10]}...")
        print(f"✅ Telegram Channel ID: {telegram_channel_id}")
        
        genai.configure(api_key=gemini_api_key)
        
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        model, init_response = initialize_science_flash_lite(facts)
        if not model:
            print("❌ Научный Flash-Lite не инициализирован")
            return False
        
        time.sleep(1)
        
        top_3_news = get_top_science_news()
        if not top_3_news:
            print("❌ Нет научных новостей для ТОП-3")
            return False
        
        time.sleep(1)
        
        commentary, prompt = generate_science_commentary(model, top_3_news)
        if not commentary:
            print("❌ Flash-Lite не создал анализ ТОП-3")
            return False
        
        save_success = save_science_results(commentary, top_3_news, init_response, prompt)
        if not save_success:
            print("⚠️ Ошибка сохранения, но продолжаем...")
        
        telegram_text = format_for_telegram(commentary, top_3_news)
        
        telegram_success = send_to_telegram(telegram_bot_token, telegram_channel_id, telegram_text)
        
        if telegram_success:
            print("🎉 УСПЕХ! Анализ опубликован в Telegram!")
            return True
        else:
            print("❌ Ошибка публикации в Telegram")
            return False
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
