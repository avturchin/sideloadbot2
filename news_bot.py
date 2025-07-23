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
import hashlib

def check_environment():
    """Проверяет рабочую среду и права доступа"""
    print("🔍 === ДИАГНОСТИКА СРЕДЫ ВЫПОЛНЕНИЯ ===")
    
    # Проверяем текущую директорию
    current_dir = os.getcwd()
    print(f"📂 Текущая директория: {current_dir}")
    
    # Проверяем права на запись
    try:
        test_file = "test_write_permissions.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Права на запись в текущую директорию: ДА")
    except Exception as e:
        print(f"❌ Права на запись в текущую директорию: НЕТ - {e}")
        return False
    
    # Проверяем содержимое текущей директории
    try:
        files = os.listdir('.')
        print(f"📋 Файлы в текущей директории ({len(files)} шт.):")
        for f in sorted(files)[:10]:  # Показываем первые 10
            if os.path.isfile(f):
                size = os.path.getsize(f)
                print(f"   📄 {f} ({size} байт)")
            else:
                print(f"   📁 {f}/")
        if len(files) > 10:
            print(f"   ... и ещё {len(files) - 10} файлов/папок")
    except Exception as e:
        print(f"❌ Ошибка чтения директории: {e}")
    
    # Проверяем наличие папки commentary
    commentary_exists = os.path.exists('commentary')
    print(f"📁 Папка commentary существует: {commentary_exists}")
    
    if commentary_exists:
        try:
            commentary_files = os.listdir('commentary')
            print(f"📋 Файлов в commentary: {len(commentary_files)}")
            for f in sorted(commentary_files)[:5]:
                size = os.path.getsize(os.path.join('commentary', f))
                print(f"   📄 {f} ({size} байт)")
        except Exception as e:
            print(f"❌ Ошибка чтения папки commentary: {e}")
    
    # Проверяем наличие processed_news.json
    processed_exists = os.path.exists('processed_news.json')
    print(f"📄 Файл processed_news.json существует: {processed_exists}")
    
    if processed_exists:
        try:
            size = os.path.getsize('processed_news.json')
            print(f"📊 Размер processed_news.json: {size} байт")
        except Exception as e:
            print(f"❌ Ошибка чтения processed_news.json: {e}")
    
    print("🔍 === КОНЕЦ ДИАГНОСТИКИ ===\n")
    return True

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

def ensure_directory_exists(directory):
    """Принудительно создаёт директорию с проверками"""
    print(f"📁 Проверяем директорию: {directory}")
    
    abs_path = os.path.abspath(directory)
    print(f"📂 Абсолютный путь: {abs_path}")
    
    if os.path.exists(directory):
        if os.path.isdir(directory):
            print(f"✅ Директория {directory} уже существует")
            return True
        else:
            print(f"❌ {directory} существует, но это не директория!")
            return False
    
    try:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Директория {directory} создана")
        
        # Проверяем что директория действительно создалась
        if os.path.exists(directory) and os.path.isdir(directory):
            print(f"✅ Проверка: директория {directory} доступна")
            
            # Проверяем права на запись в директорию
            test_file = os.path.join(directory, 'test_write.tmp')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                print(f"✅ Права на запись в {directory}: ДА")
                return True
            except Exception as write_e:
                print(f"❌ Права на запись в {directory}: НЕТ - {write_e}")
                return False
        else:
            print(f"❌ Директория {directory} не была создана!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка создания директории {directory}: {e}")
        traceback.print_exc()
        return False

def load_processed_news():
    """Загружает список уже обработанных новостей"""
    processed_file = 'processed_news.json'
    
    print(f"📚 Проверяем файл обработанных новостей: {processed_file}")
    print(f"📂 Абсолютный путь: {os.path.abspath(processed_file)}")
    
    if not os.path.exists(processed_file):
        print(f"📝 Файл {processed_file} не найден, создаём новый пустой список...")
        empty_data = {}
        try:
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, ensure_ascii=False, indent=2)
            
            # Проверяем что файл действительно создался
            if os.path.exists(processed_file):
                file_size = os.path.getsize(processed_file)
                print(f"✅ Создан пустой файл {processed_file} ({file_size} байт)")
                return empty_data
            else:
                print(f"❌ Файл {processed_file} не был создан!")
                return {}
                
        except Exception as e:
            print(f"❌ Ошибка создания {processed_file}: {e}")
            traceback.print_exc()
            return {}
    
    try:
        file_size = os.path.getsize(processed_file)
        print(f"📊 Размер файла {processed_file}: {file_size} байт")
        
        with open(processed_file, 'r', encoding='utf-8') as f:
            processed = json.load(f)
        print(f"📚 Загружено {len(processed)} обработанных новостей из {processed_file}")
        
        # Показываем последние 3 обработанные новости
        if processed:
            sorted_news = sorted(processed.items(), key=lambda x: x[1]['date'], reverse=True)[:3]
            print("🔍 Последние обработанные новости:")
            for hash_id, info in sorted_news:
                print(f"   • {info['date']} - {info['source']} - {info['title'][:50]}...")
        
        return processed
    except Exception as e:
        print(f"❌ Ошибка загрузки {processed_file}: {e}")
        traceback.print_exc()
        print("📝 Создаём новый пустой список...")
        return {}

def save_processed_news(processed_news):
    """Сохраняет список обработанных новостей с максимальной диагностикой"""
    processed_file = 'processed_news.json'
    abs_path = os.path.abspath(processed_file)
    
    print(f"💾 === СОХРАНЕНИЕ {processed_file} ===")
    print(f"📂 Абсолютный путь: {abs_path}")
    print(f"📊 Количество записей: {len(processed_news)}")
    
    try:
        # Создаём резервную копию если файл существует
        if os.path.exists(processed_file):
            backup_file = f"{processed_file}.backup"
            try:
                with open(processed_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                print(f"📋 Создана резервная копия: {backup_file}")
            except Exception as backup_e:
                print(f"⚠️ Не удалось создать резервную копию: {backup_e}")
        
        # Сохраняем основной файл
        print(f"💾 Записываем данные в {processed_file}...")
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed_news, f, ensure_ascii=False, indent=2)
        print(f"✅ Данные записаны в файл")
        
        # Принудительная синхронизация диска (ИСПРАВЛЕНО)
        try:
            if hasattr(os, 'sync'):
                os.sync()
                print(f"💾 Синхронизация диска выполнена")
        except Exception as sync_e:
            print(f"⚠️ Синхронизация диска не удалась: {sync_e}")
        
        # Детальная проверка созданного файла
        if os.path.exists(processed_file):
            file_size = os.path.getsize(processed_file)
            print(f"✅ Файл {processed_file} существует ({file_size} байт)")
            
            # Проверяем содержимое
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    check_data = json.load(f)
                print(f"✅ Проверка содержимого: {len(check_data)} записей")
                
                # Показываем последнюю запись
                if check_data:
                    last_key = list(check_data.keys())[-1]
                    last_entry = check_data[last_key]
                    print(f"🔍 Последняя запись: {last_entry['date']} - {last_entry['title'][:30]}...")
                
                print(f"🎉 ФАЙЛ {processed_file} УСПЕШНО СОХРАНЁН!")
                return True
                
            except Exception as check_e:
                print(f"❌ Ошибка проверки содержимого: {check_e}")
                return False
        else:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл {processed_file} НЕ СУЩЕСТВУЕТ после записи!")
            
            # Дополнительная диагностика
            current_files = os.listdir('.')
            print(f"📋 Файлы в текущей директории после записи:")
            for f in sorted(current_files):
                if f.endswith('.json'):
                    size = os.path.getsize(f) if os.path.exists(f) else 0
                    print(f"   📄 {f} ({size} байт)")
            
            return False
            
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА сохранения {processed_file}: {e}")
        traceback.print_exc()
        return False

def generate_news_hash(title, description):
    """Генерирует уникальный хеш для новости на основе заголовка и описания"""
    # Нормализуем текст: убираем лишние пробелы, приводим к нижнему регистру
    normalized_title = ' '.join(title.lower().strip().split())
    normalized_desc = ' '.join(description.lower().strip().split())
    
    # Создаём хеш из заголовка и первых 500 символов описания
    content = normalized_title + "|" + normalized_desc[:500]
    
    # Генерируем SHA256 хеш
    news_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    print(f"🔍 Хеш для новости: {news_hash}")
    print(f"   📰 Заголовок: {title[:50]}...")
    
    return news_hash

def is_news_already_processed(news, processed_news):
    """Проверяет, была ли новость уже обработана"""
    news_hash = generate_news_hash(news['title'], news['description'])
    
    if news_hash in processed_news:
        processed_info = processed_news[news_hash]
        print(f"🔄 НАЙДЕН ДУБЛИКАТ! Новость УЖЕ ОБРАБОТАНА:")
        print(f"   📰 Заголовок: {news['title'][:60]}...")
        print(f"   📅 Дата обработки: {processed_info['date']}")
        print(f"   🌍 Источник: {processed_info['source']}")
        print(f"   🔑 Хеш: {news_hash}")
        return True
    
    print(f"✅ Новость НЕ обрабатывалась ранее (хеш: {news_hash})")
    return False

def add_news_to_processed(news, processed_news, commentary_length):
    """Добавляет новость в список обработанных"""
    news_hash = generate_news_hash(news['title'], news['description'])
    
    processed_news[news_hash] = {
        'title': news['title'][:100] + "..." if len(news['title']) > 100 else news['title'],
        'source': news['source'],
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'importance_score': news['importance_score'],
        'commentary_length': commentary_length,
        'hash': news_hash,
        'full_title': news['title']  # Сохраняем полный заголовок
    }
    
    print(f"✅ Новость добавлена в обработанные:")
    print(f"   🔑 Хеш: {news_hash}")
    print(f"   📰 Заголовок: {news['title'][:60]}...")
    print(f"   🌍 Источник: {news['source']}")
    
    return processed_news

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
    """Получает научные новости и возвращает СЛУЧАЙНУЮ из ТОП-5 НЕОБРАБОТАННЫХ"""
    print("🔬 Получаем научные новости...")
    all_science_news = []
    
    # Загружаем список обработанных новостей В НАЧАЛЕ
    processed_news = load_processed_news()
    print(f"📚 Загружен список из {len(processed_news)} обработанных новостей")
    
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
    
    total_found = 0
    total_duplicates = 0
    
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
                            
                            total_found += 1
                            
                            # ОБЯЗАТЕЛЬНАЯ проверка на дубликаты
                            if not is_news_already_processed(news_item, processed_news):
                                # Ограничиваем размер новости
                                news_item = limit_news_content(news_item)
                                all_science_news.append(news_item)
                                print(f"✅ НОВАЯ: {source['name']}: {title[:60]}...")
                            else:
                                total_duplicates += 1
                                print(f"⏩ ДУБЛИКАТ: {source['name']}: {title[:60]}...")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка новости: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Ошибка {source['name']}: {e}")
            continue
    
    print(f"📊 СТАТИСТИКА:")
    print(f"   🔬 Всего найдено научных новостей: {total_found}")
    print(f"   ⏩ Дубликатов пропущено: {total_duplicates}")
    print(f"   ✅ НОВЫХ новостей: {len(all_science_news)}")
    
    if not all_science_news:
        print("❌ ВСЕ НОВОСТИ УЖЕ БЫЛИ ОБРАБОТАНЫ!")
        return None
    
    ranked_news = rank_science_news(all_science_news)
    
    if ranked_news:
        top_5_news = ranked_news[:5]
        print(f"🏆 ТОП-5 НОВЫХ новостей:")
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

def create_safe_filename(title, source, timestamp):
    """Создаёт безопасное имя файла из заголовка новости"""
    # Убираем опасные символы и ограничиваем длину
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = ' '.join(safe_title.split())  # Убираем двойные пробелы
    
    # Ограничиваем длину заголовка
    if len(safe_title) > 50:
        safe_title = safe_title[:50].rsplit(' ', 1)[0]  # Обрезаем по словам
    
    # Заменяем пробелы на подчёркивания
    safe_title = safe_title.replace(' ', '_')
    
    # Убираем спецсимволы из источника
    safe_source = "".join(c for c in source if c.isalnum() or c in ('-', '_')).strip()
    
    # Создаём финальное имя файла
    filename = f"{timestamp}_{safe_source}_{safe_title}"
    
    # Убираем двойные подчёркивания
    filename = '_'.join(filter(None, filename.split('_')))
    
    return filename

def save_science_results(commentary, selected_news, init_response, prompt):
    """Сохраняет результаты анализа научной новости в папку commentary с максимальной диагностикой"""
    directory = 'commentary'
    
    print(f"💾 === СОХРАНЕНИЕ ФАЙЛОВ В {directory} ===")
    
    # Принудительное создание директории
    if not ensure_directory_exists(directory):
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать директорию {directory}")
        return False
    
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    date_formatted = now.strftime("%d.%m.%Y %H:%M:%S")
    
    try:
        # Создаём безопасное имя файла
        safe_filename = create_safe_filename(selected_news['title'], selected_news['source'], timestamp)
        
        print(f"📝 Базовое имя файла: {safe_filename}")
        
        # Определяем пути к файлам
        main_filename = os.path.join(directory, f'{safe_filename}_turchin_flash20.md')
        txt_filename = os.path.join(directory, f'{safe_filename}_turchin_flash20.txt')
        stats_filename = os.path.join(directory, f'{safe_filename}_stats.txt')
        
        print(f"📄 Файлы для создания:")
        print(f"   🔗 {main_filename}")
        print(f"   🔗 {txt_filename}")
        print(f"   🔗 {stats_filename}")
        
        # Сохраняем Markdown файл
        print(f"💾 Создаём Markdown файл...")
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
        
        # Принудительная синхронизация (ИСПРАВЛЕНО)
        try:
            if hasattr(os, 'sync'):
                os.sync()
                print(f"💾 Синхронизация диска выполнена")
        except Exception as sync_e:
            print(f"⚠️ Синхронизация диска не удалась: {sync_e}")
        
        # Сохраняем простой текстовый файл
        print(f"💾 Создаём текстовый файл...")
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"КОММЕНТАРИИ ОТ ALEXEY TURCHIN (GEMINI 2.0 FLASH)\n")
            f.write(f"Дата: {date_formatted}\n")
            f.write("=" * 50 + "\n\n")
            f.write("ИСХОДНАЯ НОВОСТЬ:\n\n")
            f.write(f"Заголовок: {selected_news['title']}\n\n")
            if selected_news['description']:
                f.write(f"Описание: {selected_news['description']}\n\n")
            f.write(f"Источник: {selected_news['source']}\n")
            if selected_news['link']:
                f.write(f"Ссылка: {selected_news['link']}\n")
            f.write(f"Важность: {selected_news['importance_score']} очков\n\n")
            f.write("=" * 50 + "\n\n")
            f.write("КОММЕНТАРИЙ ALEXEY TURCHIN:\n\n")
            f.write(f"{commentary}\n\n")
            f.write("=" * 50 + "\n")
        
        # Сохраняем статистику
        print(f"💾 Создаём файл статистики...")
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
            f.write(f"Хеш новости: {generate_news_hash(selected_news['title'], selected_news['description'])}\n")
        
        # Принудительная синхронизация снова (ИСПРАВЛЕНО)
        try:
            if hasattr(os, 'sync'):
                os.sync()
                print(f"💾 Финальная синхронизация диска выполнена")
        except Exception as sync_e:
            print(f"⚠️ Финальная синхронизация диска не удалась: {sync_e}")
        
        # ДЕТАЛЬНАЯ проверка созданных файлов
        print(f"🔍 Проверяем созданные файлы...")
        created_files = []
        all_files = [main_filename, txt_filename, stats_filename]
        
        for filename in all_files:
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                created_files.append(filename)
                print(f"✅ СОЗДАН: {filename} ({file_size} байт)")
            else:
                print(f"❌ НЕ СОЗДАН: {filename}")
        
        # Дополнительная проверка содержимого директории
        try:
            dir_contents = os.listdir(directory)
            print(f"📋 Содержимое папки {directory} ({len(dir_contents)} файлов):")
            for f in sorted(dir_contents):
                if f.startswith(timestamp):
                    full_path = os.path.join(directory, f)
                    size = os.path.getsize(full_path)
                    print(f"   📄 {f} ({size} байт)")
        except Exception as dir_e:
            print(f"❌ Ошибка чтения директории {directory}: {dir_e}")
        
        if len(created_files) == 3:
            print(f"🎉 ВСЕ {len(created_files)} ФАЙЛОВ УСПЕШНО СОЗДАНЫ!")
            return True
        else:
            print(f"⚠️ СОЗДАНО ТОЛЬКО {len(created_files)} ИЗ 3 ФАЙЛОВ!")
            return False
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА сохранения в {directory}: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        print("⚡ === ALEXEY TURCHIN GEMINI 2.0 FLASH КОММЕНТАТОР → TELEGRAM ГРУППА ===")
        print("🌍 Источники: Русские + Английские научные новости")
        print("🔄 Защита от повторов: ДА")
        print("💾 Автосохранение в репозиторий: ДА")
        
        # ДИАГНОСТИКА СРЕДЫ ВЫПОЛНЕНИЯ
        if not check_environment():
            print("❌ Проблемы с рабочей средой!")
            return False
        
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
        
        # 1. ПРИНУДИТЕЛЬНО создаём необходимые директории
        if not ensure_directory_exists('commentary'):
            print("❌ Не удалось создать папку commentary")
            return False
        
        # 2. ЗАГРУЖАЕМ Facts.txt ОДИН РАЗ
        facts = load_facts()
        if not facts:
            print("❌ Нет фактов")
            return False
        
        # 3. ИНИЦИАЛИЗИРУЕМ модель ОДИН РАЗ с Facts
        model, init_response = initialize_gemini_2_0_flash_once(facts)
        if not model:
            print("❌ Gemini 2.0 Flash не инициализирован")
            return False
        
        print("⏱️ Ждем 10 секунд перед следующим запросом...")
        time.sleep(10)
        
        # 4. ПОЛУЧАЕМ НОВУЮ новость (с ОБЯЗАТЕЛЬНОЙ проверкой на повторы)
        selected_news = get_top_science_news()
        if not selected_news:
            print("❌ Нет новых научных новостей (все уже обработаны)")
            return False
        
        # 5. ГЕНЕРИРУЕМ комментарий БЕЗ повторной загрузки Facts
        commentary, prompt = generate_science_commentary(model, selected_news)
        if not commentary:
            print("❌ Gemini 2.0 Flash не создал комментарий")
            return False
        
        # 6. СОХРАНЯЕМ результаты с МАКСИМАЛЬНОЙ диагностикой
        print("💾 === НАЧИНАЕМ СОХРАНЕНИЕ ФАЙЛОВ ===")
        save_success = save_science_results(commentary, selected_news, init_response, prompt)
        if not save_success:
            print("❌ КРИТИЧЕСКАЯ ОШИБКА СОХРАНЕНИЯ ФАЙЛОВ!")
            print("⚠️ Продолжаем, но файлы могут быть не сохранены...")
        
        # 7. ДОБАВЛЯЕМ новость в список обработанных ОБЯЗАТЕЛЬНО
        print("📚 === ОБНОВЛЯЕМ СПИСОК ОБРАБОТАННЫХ НОВОСТЕЙ ===")
        processed_news = load_processed_news()
        processed_news = add_news_to_processed(selected_news, processed_news, len(commentary))
        save_success_processed = save_processed_news(processed_news)
        
        if not save_success_processed:
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось сохранить список обработанных новостей!")
            print("⚠️ Это ГАРАНТИРОВАННО приведёт к повторам в будущем!")
        
        # 8. ОТПРАВЛЯЕМ в Telegram
        telegram_text = format_for_telegram_group(commentary, selected_news)
        telegram_success = send_to_telegram_group(telegram_bot_token, telegram_group_id, telegram_text)
        
        # 9. ФИНАЛЬНАЯ ДИАГНОСТИКА
        print("\n🔍 === ФИНАЛЬНАЯ ДИАГНОСТИКА ===")
        check_environment()
        
        if telegram_success:
            print("🎉 УСПЕХ! Комментарий Alexey Turchin (Gemini 2.0 Flash) опубликован!")
            print("👥 Группа: Alexey & Alexey Turchin sideload news comments")
            print(f"🎲 Новость: {selected_news['title'][:60]}... - {selected_news['source']}")
            print(f"📊 Всего обработано новостей: {len(processed_news)}")
            print(f"🔑 Хеш обработанной новости: {generate_news_hash(selected_news['title'], selected_news['description'])}")
            print(f"💾 Файлы сохранены: {'ДА' if save_success else 'НЕТ'}")
            print(f"📚 Список обновлён: {'ДА' if save_success_processed else 'НЕТ'}")
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
