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

def estimate_tokens(text):
    """Примерная оценка токенов (1 токен ≈ 3-4 символа для русского)"""
    return len(text) // 3

def extract_response_content(text):
    """Извлекает содержимое между (RESPONSE) и (CONFIDENCE)"""
    try:
        print(f"🔍 Исходный текст ({len(text)} символов): {text[:200]}...")
        
        start_marker = "(RESPONSE)"
        end_marker = "(CONFIDENCE)"
        
        start_index = text.find(start_marker)
        if start_index == -1:
            print("⚠️ Маркер (RESPONSE) не найден")
            return text.strip()
        
        start_index += len(start_marker)
        print(f"📍 Найден (RESPONSE) на позиции {start_index}")
        
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
    """Получает список доступных моделей с приоритетом Gemini 2.0 Flash"""
    try:
        print("🔄 Проверяем доступные модели Gemini...")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                if '2.0' in model.name and 'flash' in model.name.lower():
                    print(f"⚡ GEMINI 2.0 FLASH: {model.name}")
                elif 'flash' in model.name.lower():
                    print(f"⚡ FLASH: {model.name}")
                elif 'pro' in model.name.lower():
                    print(f"💎 PRO: {model.name}")
                else:
                    print(f"🤖 Модель: {model.name}")
        
        print(f"📊 Всего доступно {len(available_models)} моделей")
        return available_models
    except Exception as e:
        print(f"❌ Ошибка получения моделей: {e}")
        return []

def is_science_news(title, description):
    """Проверяет, является ли новость научной (русские и английские ключевые слова)"""
    text = (title + " " + description).lower()
    
    science_keywords = [
        # Русские ключевые слова
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
        # Английские ключевые слова
        'research', 'study', 'discovery', 'experiment', 'scientific', 'science',
        'technology', 'development', 'innovation', 'laboratory', 'university',
        'institute', 'biology', 'physics', 'chemistry', 'medicine', 'medical',
        'space', 'astronomy', 'genetics', 'dna', 'protein', 'virus',
        'treatment', 'therapy', 'vaccine', 'drug', 'clinical', 'trial',
        'neurons', 'brain', 'cognitive', 'artificial intelligence', 'ai',
        'machine learning', 'algorithm', 'robot', 'quantum',
        'material', 'nanotechnology', 'biotechnology', 'genetic engineering',
        'stem cells', 'cancer', 'oncology', 'diagnosis', 'diagnostic',
        'microbiology', 'ecology', 'climate', 'environment', 'environmental',
        'energy', 'solar', 'wind', 'battery', 'renewable',
        'satellite', 'probe', 'mars', 'moon', 'planet', 'galaxy',
        'telescope', 'breakthrough', 'novel', 'findings', 'journal',
        'published', 'peer-reviewed', 'researchers', 'scientists'
    ]
    
    exclude_keywords = [
        # Русские исключения
        'выборы', 'президент', 'парламент', 'дума', 'правительство', 'министр',
        'политик', 'партия', 'санкции', 'война', 'конфликт', 'протест',
        'курс валют', 'рубль', 'доллар', 'нефть', 'газ', 'экономика',
        'инфляция', 'бюджет', 'налог', 'спорт', 'футбол', 'хоккей',
        'олимпиада', 'чемпионат', 'матч', 'игра', 'команда', 'тренер',
        # Английские исключения
        'election', 'president', 'parliament', 'government', 'minister',
        'politician', 'party', 'sanctions', 'war', 'conflict', 'protest',
        'currency', 'dollar', 'oil', 'gas', 'economy', 'economic',
        'inflation', 'budget', 'tax', 'sport', 'football', 'soccer',
        'olympics', 'championship', 'match', 'game', 'team', 'coach',
        'celebrity', 'entertainment', 'movie', 'music', 'fashion'
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
            # Русские высокоприоритетные
            'прорыв', 'революция', 'впервые', 'открытие', 'breakthrough',
            'искусственный интеллект', 'ии', 'нейросеть', 'машинное обучение',
            'космос', 'марс', 'луна', 'спутник', 'телескоп',
            'рак', 'онкология', 'лечение', 'вакцина', 'генная терапия',
            'квантовый', 'квантовые вычисления', 'нанотехнологии',
            'стволовые клетки', 'регенерация', 'биотехнологии',
            'климат', 'глобальное потепление', 'экология',
            # Английские высокоприоритетные
            'breakthrough', 'revolutionary', 'first time', 'discovery',
            'artificial intelligence', 'ai', 'neural network', 'machine learning',
            'space', 'mars', 'moon', 'satellite', 'telescope',
            'cancer', 'oncology', 'treatment', 'vaccine', 'gene therapy',
            'quantum', 'quantum computing', 'nanotechnology',
            'stem cells', 'regeneration', 'biotechnology',
            'climate change', 'global warming', 'ecology',
            'crispr', 'genome editing', 'immunotherapy', 'precision medicine'
        ]
        
        medium_priority = [
            # Русские среднеприоритетные
            'исследование', 'эксперимент', 'тест', 'технология',
            'разработка', 'метод', 'система', 'устройство',
            # Английские среднеприоритетные
            'research', 'study', 'experiment', 'test', 'technology',
            'development', 'method', 'system', 'device', 'trial',
            'findings', 'results', 'analysis', 'investigation'
        ]
        
        for keyword in high_priority:
            if keyword in text:
                score += 10
        
        for keyword in medium_priority:
            if keyword in text:
                score += 5
        
        # Бонусы за источники
        if news['source'] in ['N+1', 'Naked Science', 'Nature', 'Science', 'ScienceDaily']:
            score += 5
        elif news['source'] in ['MIT Technology Review', 'New Scientist', 'Scientific American']:
            score += 4
        elif news['source'] in ['BBC Science', 'CNN Health', 'Reuters Science']:
            score += 3
        
        if len(news['description']) > 200:
            score += 2
        
        news['importance_score'] = score
    
    return sorted(news_list, key=lambda x: x['importance_score'], reverse=True)

def limit_news_content(news):
    """Ограничивает содержимое новости до 5000 токенов (~15000 символов)"""
    max_chars = 15000  # ~5000 токенов
    
    # Ограничиваем только описание, заголовок оставляем полным
    if len(news['description']) > max_chars:
        news['description'] = news['description'][:max_chars] + "..."
        print(f"✂️ Описание новости обрезано до {max_chars} символов")
    
    total_tokens = estimate_tokens(news['title'] + " " + news['description'])
    print(f"🔢 Примерное количество токенов в новости: {total_tokens}")
    
    return news

def get_top_science_news():
    """Получает научные новости и возвращает СЛУЧАЙНУЮ из ТОП-5"""
    print("🔬 Получаем научные новости...")
    all_science_news = []
    
    sources = [
        # Русские источники
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
        # Английские источники
        {
            'url': 'https://www.sciencedaily.com/rss/all.xml', 
            'name': 'ScienceDaily'
        },
        {
            'url': 'https://feeds.nature.com/nature/rss/current', 
            'name': 'Nature'
        },
        {
            'url': 'https://www.science.org/rss/news_current.xml', 
            'name': 'Science'
        },
        {
            'url': 'https://www.technologyreview.com/feed/', 
            'name': 'MIT Technology Review'
        },
        {
            'url': 'https://www.newscientist.com/feed/home/', 
            'name': 'New Scientist'
        },
        {
            'url': 'https://rss.cnn.com/rss/cnn_health.rss', 
            'name': 'CNN Health'
        },
        {
            'url': 'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml', 
            'name': 'BBC Science'
        },
        {
            'url': 'https://www.reuters.com/arc/outboundfeeds/rss/category/health/?outputType=xml', 
            'name': 'Reuters Science'
        },
        {
            'url': 'https://rss.sciam.com/ScientificAmerican-Global', 
            'name': 'Scientific American'
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
                            
                            news_item = {
                                'title': title,
                                'description': description,
                                'source': source['name'],
                                'link': link
                            }
                            
                            # Ограничиваем размер новости
                            news_item = limit_news_content(news_item)
                            
                            all_science_news.append(news_item)
                            
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
        top_5_news = ranked_news[:5]
        print(f"🏆 ТОП-5 новостей:")
        for i, news in enumerate(top_5_news, 1):
            print(f"   {i}. {news['title'][:60]}... (очки: {news['importance_score']}) - {news['source']}")
        
        selected_news = random.choice(top_5_news)
        print(f"🎲 СЛУЧАЙНО ВЫБРАНА: {selected_news['title'][:80]}... (очки: {selected_news['importance_score']}) - {selected_news['source']}")
        return selected_news
    else:
        print("❌ Научные новости не найдены")
        return None

def initialize_gemini_2_0_flash_once(facts):
    """Инициализирует Gemini 2.0 Flash ОДИН РАЗ с полными facts"""
    
    available_models = get_available_models()
    if not available_models:
        return None, "Нет доступных моделей"
    
    target_models = [
        'models/gemini-2.0-flash',
        'models/gemini-2.0-flash-thinking',
        'models/gemini-2.0-flash-exp',
    ]
    
    selected_model = None
    
    for model in target_models:
        if model in available_models:
            selected_model = model
            print(f"🎯 ВЫБРАНА: {selected_model}")
            print(f"🏷️ Версия: ⚡ GEMINI 2.0 FLASH")
            break
    
    if not selected_model:
        print("❌ GEMINI 2.0 FLASH НЕ НАЙДЕН в доступных моделях!")
        print(f"📋 Доступные модели: {available_models}")
        return None, "Gemini 2.0 Flash недоступен"
    
    try:
        # ПОЛНАЯ система инструкций - загружается ТОЛЬКО ОДИН РАЗ
        system_instruction = f"""Ты - Alexey Turchin, всемирно известный российский трансгуманист, футуролог и исследователь проблем экзистенциального риска. Ты автор книг о бессмертии, глобальных рисках и карте бессмертия. 

ПОЛНАЯ БАЗА ЗНАНИЙ:
{facts}

Анализируй научные открытия через призму трансгуманизма, футурологии и их влияние на продление жизни человека. Пиши глубокие экспертные комментарии с философской точки зрения.

ВАЖНЫЕ ПРАВИЛА:
- Если новость на английском языке, переведи её суть и анализируй на русском языке
- Всегда отвечай на русском языке как Alexey Turchin
- Анализируй как русские, так и международные научные открытия

ВАЖНОЕ ПРАВИЛО ФОРМАТИРОВАНИЯ: 
- Начинай ответ с (RESPONSE)
- Пиши ТОЛЬКО свой экспертный комментарий как Alexey Turchin
- Заканчивай (CONFIDENCE)
- НЕ ДОБАВЛЯЙ ничего после (CONFIDENCE)

СТИЛЬ: Интеллектуальный, с научной терминологией, упоминания трансгуманистических идей, связь с продлением жизни, прогнозы развития технологий, философские размышления."""

        system_tokens = estimate_tokens(system_instruction)
        print(f"📊 Facts загружается ОДИН РАЗ: {len(facts)} символов (~{estimate_tokens(facts)} токенов)")
        print(f"📊 System instruction: {len(system_instruction)} символов (~{system_tokens} токенов)")
        
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction
        )
        
        # Самые мягкие настройки безопасности
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=1000,
        )
        
        print(f"🧪 Тестируем Gemini 2.0 Flash с Facts...")
        test_response = model.generate_content(
            "Готов анализировать научные новости как Alexey Turchin? Ответь кратко в указанном формате.",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        if test_response and test_response.candidates:
            candidate = test_response.candidates[0]
            print(f"🔍 Finish reason: {candidate.finish_reason}")
            
            if candidate.finish_reason in [1, 2]:  # STOP или MAX_TOKENS
                if candidate.content and candidate.content.parts:
                    text = candidate.content.parts[0].text
                    extracted_response = extract_response_content(text)
                    print(f"✅ Gemini 2.0 Flash с Facts готов: {extracted_response}")
                    return model, extracted_response
                else:
                    print(f"❌ Нет текста в candidate")
                    return None, "Нет текста в ответе"
            else:
                print(f"❌ Проблема: finish_reason = {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    print(f"🔍 Safety ratings: {candidate.safety_ratings}")
                return None, f"Finish reason: {candidate.finish_reason}"
        else:
            print(f"❌ Нет candidates")
            return None, "Нет candidates в ответе"
            
    except Exception as e:
        print(f"❌ Ошибка Gemini 2.0 Flash: {e}")
        traceback.print_exc()
        return None, f"Ошибка: {e}"

def generate_science_commentary(model, selected_news):
    """Генерирует научный комментарий БЕЗ повторной загрузки facts"""
    if not model or not selected_news:
        return None, None
    
    print("⚡ Gemini 2.0 Flash анализирует научную новость...")
    
    # КРАТКИЙ промпт - БЕЗ facts, только новость
    analysis_prompt = f"""Прокомментируй эту научную новость как трансгуманист и футуролог Alexey Turchin:

ЗАГОЛОВОК: {selected_news['title']}

ОПИСАНИЕ: {selected_news['description']}

ИСТОЧНИК: {selected_news['source']}

Дай краткий но полный экспертный анализ через призму трансгуманизма:
- Как это открытие повлияет на продление жизни человека?
- Какие возможности это открывает для улучшения человека?
- Связь с трансгуманистическими трендами
- Значимость для будущего человечества

ВАЖНО: Строго соблюдай формат и ЗАВЕРШАЙ мысль! Отвечай на русском языке.
(RESPONSE)
[полный экспертный комментарий как Alexey Turchin]
(CONFIDENCE)"""
    
    prompt_tokens = estimate_tokens(analysis_prompt)
    print(f"🔢 Промпт для комментария: ~{prompt_tokens} токенов")
    
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.95,
            max_output_tokens=1200,
        )
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        print(f"⚡ Gemini 2.0 Flash генерирует комментарий (макс. {generation_config.max_output_tokens} токенов)...")
        
        response = model.generate_content(
            analysis_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        if response and response.candidates:
            candidate = response.candidates[0]
            print(f"🔍 Finish reason: {candidate.finish_reason}")
            
            if candidate.finish_reason == 1:  # STOP - полный ответ
                if candidate.content and candidate.content.parts:
                    text = candidate.content.parts[0].text
                    print(f"📄 RAW ответ Gemini 2.0 Flash ({len(text)} символов) - ПОЛНЫЙ")
                    extracted_commentary = extract_response_content(text)
                    print(f"✅ Комментарий готов ({len(extracted_commentary)} символов)")
                    return extracted_commentary, analysis_prompt
                else:
                    return "Нет текста в ответе", analysis_prompt
                    
            elif candidate.finish_reason == 2:  # MAX_TOKENS - обрезанный ответ
                if candidate.content and candidate.content.parts:
                    text = candidate.content.parts[0].text
                    print(f"⚠️ RAW ответ Gemini 2.0 Flash ({len(text)} символов) - ОБРЕЗАН по лимиту токенов")
                    extracted_commentary = extract_response_content(text)
                    
                    # Пытаемся дополнить обрезанный ответ
                    if not extracted_commentary.endswith('.') and not extracted_commentary.endswith('!'):
                        print(f"🔧 Пытаемся дополнить обрезанный ответ...")
                        
                        continuation_prompt = f"""Продолжи и ЗАВЕРШИ этот комментарий Alexey Turchin:

{extracted_commentary}

Дополни максимум 2-3 предложения и заверши мысль. Формат:
(RESPONSE)
[продолжение и завершение]
(CONFIDENCE)"""

                        continuation_config = genai.types.GenerationConfig(
                            temperature=0.8,
                            top_p=0.95,
                            max_output_tokens=300,
                        )
                        
                        time.sleep(2)
                        
                        try:
                            continuation_response = model.generate_content(
                                continuation_prompt,
                                generation_config=continuation_config,
                                safety_settings=safety_settings
                            )
                            
                            if continuation_response and continuation_response.candidates:
                                cont_candidate = continuation_response.candidates[0]
                                if cont_candidate.finish_reason in [1, 2] and cont_candidate.content and cont_candidate.content.parts:
                                    continuation_text = cont_candidate.content.parts[0].text
                                    continuation_extracted = extract_response_content(continuation_text)
                                    
                                    # Объединяем основной ответ с продолжением
                                    full_commentary = extracted_commentary + " " + continuation_extracted
                                    print(f"🔧 Ответ дополнен! Итого: {len(full_commentary)} символов")
                                    return full_commentary, analysis_prompt
                                    
                        except Exception as cont_e:
                            print(f"⚠️ Не удалось дополнить ответ: {cont_e}")
                    
                    # Если дополнение не сработало, возвращаем как есть
                    print(f"⚠️ Комментарий может быть неполным ({len(extracted_commentary)} символов)")
                    return extracted_commentary + "...", analysis_prompt
                else:
                    return "Нет текста в обрезанном ответе", analysis_prompt
            else:
                print(f"❌ Finish reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    print(f"🔍 Safety ratings: {candidate.safety_ratings}")
                return f"Проблема {candidate.finish_reason}", analysis_prompt
        else:
            return "Нет candidates", analysis_prompt
            
    except Exception as e:
        print(f"❌ Ошибка комментария: {e}")
        traceback.print_exc()
        return f"Ошибка: {e}", analysis_prompt

def clean_text_for_telegram(text):
    """Очищает текст от проблематичных символов для Telegram"""
    replacements = {
        '*': '•', '_': '-', '`': "'", '[': '(', ']': ')',
        '~': '-', '#': '№', '|': '/',
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
                return False
        else:
            # Разбиваем на части если слишком длинное
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
    """Форматирует комментарий для Telegram группы - НОВОСТЬ СНАЧАЛА"""
    now = datetime.now()
    date_formatted = now.strftime("%d.%m.%Y %H:%M")
    
    telegram_text = f"💬 Комментарии от сайдлоада Alexey Turchin\n"
    telegram_text += f"📅 {date_formatted}\n"
    telegram_text += f"⚡ Анализ от Gemini 2.0 Flash\n"
    telegram_text += f"🌍 Источник: {selected_news['source']}\n\n"
    telegram_text += "═══════════════════\n\n"
    
    # 📰 НОВОСТЬ СНАЧАЛА
    telegram_text += f"📰 НАУЧНАЯ НОВОСТЬ:\n\n"
    telegram_text += f"🔬 {selected_news['title']}\n\n"
    
    if selected_news['description']:
        desc = selected_news['description']
        if len(desc) > 600:  # Увеличиваем лимит для показа новости
            desc = desc[:600] + "..."
        telegram_text += f"{desc}\n\n"
    
    telegram_text += f"📰 Источник: {selected_news['source']}\n"
    
    if selected_news['link']:
        telegram_text += f"🔗 Ссылка: {selected_news['link']}\n"
    
    telegram_text += f"⭐ Важность: {selected_news['importance_score']} очков\n\n"
    
    telegram_text += "═══════════════════\n\n"
    
    # 💬 КОММЕНТАРИЙ ALEXEY TURCHIN ПОСЛЕ НОВОСТИ
    telegram_text += f"💬 КОММЕНТАРИЙ ALEXEY TURCHIN:\n\n"
    telegram_text += f"{commentary}\n\n"
    telegram_text += "═══════════════════"
    
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
        main_filename = os.path.join(directory, f'science_turchin_flash20_{timestamp}.md')
        
        print(f"💾 Сохраняем комментарий Gemini 2.0 Flash: {main_filename}")
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# 💬 Комментарии от Alexey Turchin (Gemini 2.0 Flash)\n")
            f.write(f"## {date_formatted}\n\n")
            f.write(f"*Трансгуманистический комментарий от Alexey Turchin (случайная новость)*\n\n")
            f.write("---\n\n")
            f.write("## 📰 Исходная новость:\n\n")
            f.write(f"### {selected_news['title']}\n\n")
            if selected_news['description']:
                f.write(f"{selected_news['description']}\n\n")
            f.write(f"**Источник:** {selected_news['source']}\n")
            if selected_news['link']:
                f.write(f"**Ссылка:** {selected_news['link']}\n")
            f.write(f"**Важность:** {selected_news['importance_score']} очков\n\n")
            f.write("---\n\n")
            f.write("## 💬 Комментарий Alexey Turchin:\n\n")
            f.write(f"{commentary}\n\n")
        
        stats_filename = os.path.join(directory, f'science_stats_flash20_{timestamp}.txt')
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write("=== ALEXEY TURCHIN GEMINI 2.0 FLASH КОММЕНТАРИЙ ===\n")
            f.write(f"Время: {date_formatted}\n")
            f.write("Автор: Alexey Turchin (сайдлоад)\n")
            f.write("Модель: Gemini 2.0 Flash\n")
            f.write("Группа: Alexey & Alexey Turchin sideload news comments\n")
            f.write("Новостей: 1 (случайная из ТОП-5)\n")
            f.write(f"Длина комментария: {len(commentary)} символов\n")
            f.write(f"ID: {timestamp}\n")
            f.write(f"Новость: {selected_news['importance_score']} очков - {selected_news['title'][:50]}... - {selected_news['source']}\n")
        
        print(f"✅ Комментарий 2.0 Flash сохранён в: {main_filename}")
        print(f"📊 Статистика: {stats_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения в {directory}: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        print("⚡ === ALEXEY TURCHIN GEMINI 2.0 FLASH КОММЕНТАТОР → TELEGRAM ГРУППА ===")
        print("🌍 Источники: Русские + Английские научные новости")
        
        # Проверяем API ключи
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
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
        
        # 1. ЗАГРУЖАЕМ Facts.txt ОДИН РАЗ
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        # 2. ИНИЦИАЛИЗИРУЕМ модель ОДИН РАЗ с Facts
        model, init_response = initialize_gemini_2_0_flash_once(facts)
        if not model:
            print("❌ Gemini 2.0 Flash не инициализирован")
            return False
        
        print("⏱️ Ждем 10 секунд перед следующим запросом...")
        time.sleep(10)
        
        # 3. ПОЛУЧАЕМ новость (с ограничением размера)
        selected_news = get_top_science_news()
        if not selected_news:
            print("❌ Нет научных новостей")
            return False
        
        # 4. ГЕНЕРИРУЕМ комментарий БЕЗ повторной загрузки Facts
        commentary, prompt = generate_science_commentary(model, selected_news)
        if not commentary:
            print("❌ Gemini 2.0 Flash не создал комментарий")
            return False
        
        # 5. СОХРАНЯЕМ результаты
        save_success = save_science_results(commentary, selected_news, init_response, prompt)
        if not save_success:
            print("⚠️ Ошибка сохранения, но продолжаем...")
        
        # 6. ОТПРАВЛЯЕМ в Telegram
        telegram_text = format_for_telegram_group(commentary, selected_news)
        telegram_success = send_to_telegram_group(telegram_bot_token, telegram_group_id, telegram_text)
        
        if telegram_success:
            print("🎉 УСПЕХ! Комментарий Alexey Turchin (Gemini 2.0 Flash) опубликован!")
            print("👥 Группа: Alexey & Alexey Turchin sideload news comments")
            print(f"🎲 Новость: {selected_news['title'][:60]}... - {selected_news['source']}")
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
