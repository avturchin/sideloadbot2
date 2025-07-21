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
        
        # Проверяем права на запись
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
    """Загружает базу фактов из файла"""
    try:
        print("🔄 Загружаем файл Facts.txt...")
        if not os.path.exists('Facts.txt'):
            print("⚠️ Файл Facts.txt не найден, создаем базовую версию...")
            default_facts = """
Это базовая информация для анализа российских новостей:

ЭКОНОМИКА:
- Россия экспортирует нефть, газ, зерно
- Рубль зависит от цен на энергоресурсы  
- Санкции влияют на торговлю и финансы

ПОЛИТИКА:
- Федеративное устройство с 85 субъектами
- Президентская республика
- Государственная Дума и Совет Федерации

ОБЩЕСТВО:
- Население около 146 млн человек
- Многонациональная страна
- Развитая система образования и здравоохранения

МЕЖДУНАРОДНЫЕ ОТНОШЕНИЯ:
- Член ООН, БРИКС, ШОС, ЕАЭС
- Отношения с Китаем, Индией, странами Африки
- Сложные отношения с Западом
            """
            with open('Facts.txt', 'w', encoding='utf-8') as f:
                f.write(default_facts.strip())
            print("✅ Создан базовый файл Facts.txt")
            return default_facts.strip()
            
        with open('Facts.txt', 'r', encoding='utf-8') as f:
            facts = f.read()
        
        # Ограничиваем размер фактов до разумного лимита
        if len(facts) > 50000:
            print(f"⚠️ Facts.txt слишком большой ({len(facts)} символов), обрезаем до 50000")
            facts = facts[:50000] + "\n[...файл обрезан из-за размера...]"
        
        print(f"✅ Загружена база фактов ({len(facts)} символов)")
        return facts
        
    except Exception as e:
        print(f"❌ Ошибка работы с Facts.txt: {e}")
        return "Базовые знания для анализа новостей."

def get_available_models():
    """Получает список доступных моделей Gemini"""
    try:
        print("🔄 Проверяем доступные модели Gemini...")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                print(f"✅ Доступная модель: {model.name}")
        
        return available_models
    except Exception as e:
        print(f"❌ Ошибка получения списка моделей: {e}")
        return []

def get_news():
    """Получает последние новости с новостных сайтов"""
    print("🔄 Начинаем получение новостей...")
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
            
            response = requests.get(source['url'], timeout=15, headers=headers)
            print(f"✅ Ответ получен от {source['name']} (статус: {response.status_code})")
            
            if response.status_code != 200:
                print(f"⚠️ Неожиданный статус код от {source['name']}: {response.status_code}")
                continue
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'xml')
            
            items = soup.find_all('item')
            print(f"📰 Найдено {len(items)} новостей на {source['name']}")
            
            if not items:
                print(f"⚠️ Не найдено новостей в RSS {source['name']}")
                continue
            
            for j, item in enumerate(items[:3], 1):
                try:
                    title = item.title.text.strip() if item.title and item.title.text else "Без заголовка"
                    description = item.description.text.strip() if item.description and item.description.text else ""
                    link = item.link.text.strip() if item.link and item.link.text else ""
                    pub_date = item.pubDate.text.strip() if item.pubDate and item.pubDate.text else ""
                    
                    print(f"   📝 [{j}/3] {title[:60]}...")
                    
                    # Очищаем от HTML тегов в описании
                    if description:
                        desc_soup = BeautifulSoup(description, 'html.parser')
                        description = desc_soup.get_text().strip()[:300]  # Ограничиваем размер
                    
                    news_items.append({
                        'title': title[:200],  # Ограничиваем размер заголовка
                        'description': description,
                        'link': link,
                        'source': source['name'],
                        'pub_date': pub_date
                    })
                    
                except Exception as e:
                    print(f"❌ Ошибка обработки новости {j} с {source['name']}: {e}")
                    continue
                
        except Exception as e:
            print(f"❌ Ошибка получения новостей с {source['name']}: {e}")
            continue
    
    print(f"✅ Всего получено {len(news_items)} новостей")
    
    if not news_items:
        print("⚠️ Не удалось получить новости, создаем тестовые...")
        news_items = [
            {
                'title': 'Тестовая новость 1',
                'description': 'Описание тестовой новости для проверки работы системы',
                'link': 'https://example.com',
                'source': 'Тест',
                'pub_date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
            }
        ]
    
    return news_items

def initialize_gemini_with_facts(facts):
    """Инициализирует Gemini с базой фактов"""
    
    print("🔄 Получаем список доступных моделей...")
    available_models = get_available_models()
    
    if not available_models:
        print("❌ Не найдено доступных моделей")
        return None, "Нет доступных моделей"
    
    # Пробуем разные модели по приоритету
    model_priorities = [
        'models/gemini-1.5-flash',
        'models/gemini-1.5-pro', 
        'models/gemini-1.0-pro',
        'models/gemini-pro'
    ]
    
    selected_model = None
    for preferred_model in model_priorities:
        if preferred_model in available_models:
            selected_model = preferred_model
            break
    
    if not selected_model:
        selected_model = available_models[0]  # Берем первую доступную
    
    print(f"🔄 Используем модель: {selected_model}")
    
    # Сокращаем факты если они слишком длинные
    max_facts_length = 10000  # Максимум 10к символов для фактов
    if len(facts) > max_facts_length:
        facts = facts[:max_facts_length] + "\n[...обрезано...]"
    
    print("🔄 Подготавливаем промпт для инициализации...")
    initialization_prompt = f"""
Ты - российский журналист-аналитик. Изучи эту базу фактов:

{facts}

Используй эти факты для анализа текущих событий. Подтверди готовность одним предложением.
"""
    
    try:
        print("🔄 Создаем модель Gemini...")
        model = genai.GenerativeModel(selected_model)
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=300,  # Сокращаем для инициализации
        )
        
        print("🔄 Отправляем запрос инициализации к Gemini API...")
        print(f"📊 Размер промпта: {len(initialization_prompt)} символов")
        
        response = model.generate_content(
            initialization_prompt,
            generation_config=generation_config
        )
        
        if not response or not response.text:
            print("❌ Пустой ответ от Gemini при инициализации")
            return None, "Ошибка инициализации: пустой ответ"
        
        print("✅ Получен ответ от Gemini на инициализацию")
        print(f"📝 Длина ответа: {len(response.text)} символов")
        print(f"🔍 Ответ: {response.text[:200]}...")
        
        return model, response.text
        
    except Exception as e:
        print(f"❌ Ошибка инициализации Gemini: {e}")
        traceback.print_exc()
        return None, f"Ошибка инициализации: {e}"

def generate_commentary(model, news_items, facts):
    """Генерирует комментарий к новостям через Gemini"""
    if not news_items or not model:
        print("❌ Нет новостей или модели для генерации комментария")
        return None, None
        
    print("🔄 Формируем промпт для анализа новостей...")
    
    # Формируем список новостей для промпта (ограничиваем размер)
    news_text = ""
    for i, item in enumerate(news_items[:5], 1):  # Максимум 5 новостей
        news_text += f"{i}. {item['title']}\n"
        if item['description']:
            news_text += f"   {item['description'][:200]}...\n"  # Ограничиваем описание
        news_text += f"   Источник: {item['source']}\n\n"
    
    news_analysis_prompt = f"""
Проанализируй эти новости и напиши краткий комментарий (400-500 слов):

{news_text}

Включи:
1. Главные тенденции
2. Контекст событий  
3. Анализ причин
4. Возможные последствия

Пиши на русском языке, структурированно.
"""
    
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=1000,  # Ограничиваем размер ответа
        )
        
        print("🔄 Отправляем запрос анализа новостей к Gemini API...")
        print(f"📊 Размер промпта: {len(news_analysis_prompt)} символов")
        
        response = model.generate_content(
            news_analysis_prompt,
            generation_config=generation_config
        )
        
        if not response or not response.text:
            print("❌ Пустой ответ от Gemini при анализе")
            return "Не удалось сгенерировать анализ новостей.", news_analysis_prompt
        
        print("✅ Получен ответ от Gemini с анализом")
        print(f"📝 Длина анализа: {len(response.text)} символов")
        print(f"🔍 Начало анализа: {response.text[:150]}...")
        
        return response.text, news_analysis_prompt
        
    except Exception as e:
        print(f"❌ Ошибка генерации комментария: {e}")
        traceback.print_exc()
        return f"Ошибка генерации: {e}", news_analysis_prompt

def save_commentary(commentary, news_items, initialization_response, news_prompt):
    """Сохраняет комментарий в файл"""
    print("🔄 Сохраняем результаты...")
    
    # Убедимся что папка существует
    if not ensure_directory_exists('commentary'):
        print("❌ Не удалось создать папку commentary")
        return False
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    date_formatted = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    try:
        # Сохраняем основной комментарий
        main_filename = f'commentary/news_commentary_{timestamp}.md'
        print(f"🔄 Сохраняем основной файл: {main_filename}")
        
        with open(main_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Комментарий к новостям - {date_formatted}\n\n")
            f.write(f"{commentary}\n\n")
            f.write("---\n\n")
            f.write("## Проанализированные новости:\n\n")
            
            for i, item in enumerate(news_items, 1):
                f.write(f"**{i}. {item['title']}**\n")
                if item['description']:
                    f.write(f"{item['description']}\n")
                f.write(f"*Источник: {item['source']}*\n")
                if item['link']:
                    f.write(f"[Читать полностью]({item['link']})\n")
                f.write("\n")
        
        # Проверяем что файл создался
        if os.path.exists(main_filename):
            file_size = os.path.getsize(main_filename)
            print(f"✅ Основной комментарий сохранен: {main_filename} ({file_size} байт)")
        else:
            print(f"❌ Ошибка: файл {main_filename} не создался")
            return False
        
        # Создаем также краткий файл со статистикой
        stats_filename = f'commentary/stats_{timestamp}.txt'
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"Статистика обработки новостей - {date_formatted}\n")
            f.write(f"Обработано новостей: {len(news_items)}\n")
            f.write(f"Длина комментария: {len(commentary)} символов\n")
            f.write(f"Время создания: {timestamp}\n")
            
            sources = set(item['source'] for item in news_items)
            f.write(f"Источники: {', '.join(sources)}\n")
        
        print(f"✅ Файл статистики сохранен: {stats_filename}")
        
        # Финальная проверка папки
        files = os.listdir('commentary')
        print(f"✅ В папке commentary создано {len(files)} файлов:")
        for file in files:
            file_path = os.path.join('commentary', file)
            size = os.path.getsize(file_path)
            print(f"   📄 {file} ({size} байт)")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения файлов: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        print("🚀 === ЗАПУСК БОТА КОММЕНТАРИЕВ НОВОСТЕЙ ===")
        print(f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"📁 Рабочая папка: {os.getcwd()}")
        
        # Проверяем API ключ
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ ОШИБКА: Не найден GEMINI_API_KEY в переменных окружения")
            return False
        
        print(f"✅ API ключ найден (длина: {len(api_key)} символов)")
        
        # Настраиваем Gemini
        genai.configure(api_key=api_key)
        
        # Загружаем базу фактов
        facts = load_facts()
        
        # Инициализируем Gemini с фактами
        model, initialization_response = initialize_gemini_with_facts(facts)
        if not model:
            print("❌ Не удалось инициализировать Gemini")
            return False
        
        # Небольшая пауза между запросами
        print("⏳ Пауза 3 секунды между запросами...")
        time.sleep(3)
        
        # Получаем новости
        news_items = get_news()
        
        if not news_items:
            print("❌ Не удалось получить новости")
            return False
        
        # Пауза перед вторым запросом
        print("⏳ Пауза 2 секунды перед анализом...")
        time.sleep(2)
        
        # Генерируем анализ
        commentary, news_prompt = generate_commentary(model, news_items, facts)
        
        if not commentary:
            print("❌ Не удалось сгенерировать комментарий")
            return False
        
        # Сохраняем результаты
        if save_commentary(commentary, news_items, initialization_response, news_prompt):
            print("🎉 ВСЕ ГОТОВО! Анализ успешно сгенерирован и сохранен!")
            return True
        else:
            print("❌ Ошибка сохранения результатов")
            return False
            
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в main(): {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    success = main()
    print("=" * 60)
    
    if success:
        print("✅ СКРИПТ ЗАВЕРШИЛСЯ УСПЕШНО!")
        
        # Финальная проверка
        if os.path.exists('commentary') and os.listdir('commentary'):
            print("✅ Подтверждено: файлы созданы в папке commentary/")
            files = os.listdir('commentary')
            print(f"📊 Всего файлов: {len(files)}")
            for file in files:
                size = os.path.getsize(os.path.join('commentary', file))
                print(f"   📄 {file} ({size} байт)")
        else:
            print("❌ ВНИМАНИЕ: Папка commentary пуста или не создана!")
            sys.exit(1)
            
    else:
        print("❌ СКРИПТ ЗАВЕРШИЛСЯ С ОШИБКОЙ!")
        sys.exit(1)
