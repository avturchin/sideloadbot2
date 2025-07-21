import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time

# Настройка Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

def load_facts():
    """Загружает базу фактов из файла"""
    try:
        print("🔄 Загружаем файл Facts.txt...")
        with open('Facts.txt', 'r', encoding='utf-8') as f:
            facts = f.read()
        print(f"✅ Загружена база фактов ({len(facts)} символов)")
        return facts
    except FileNotFoundError:
        print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Файл Facts.txt не найден")
        return "Базовые факты для анализа новостей не загружены."
    except Exception as e:
        print(f"❌ Ошибка загрузки Facts.txt: {e}")
        return "Ошибка загрузки базы фактов."

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
            response = requests.get(source['url'], timeout=15)
            print(f"✅ Ответ получен от {source['name']} (статус: {response.status_code})")
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'xml')
            
            items = soup.find_all('item')
            print(f"📰 Найдено {len(items)} новостей на {source['name']}")
            
            for j, item in enumerate(items[:3], 1):
                title = item.title.text if item.title else ""
                description = item.description.text if item.description else ""
                link = item.link.text if item.link else ""
                pub_date = item.pubDate.text if item.pubDate else ""
                
                print(f"   📝 [{j}/3] {title[:50]}...")
                
                # Очищаем от HTML тегов в описании
                if description:
                    desc_soup = BeautifulSoup(description, 'html.parser')
                    description = desc_soup.get_text()
                
                news_items.append({
                    'title': title,
                    'description': description[:300],
                    'link': link,
                    'source': source['name'],
                    'pub_date': pub_date
                })
                
        except Exception as e:
            print(f"❌ Ошибка получения новостей с {source['name']}: {e}")
            continue
    
    print(f"✅ Всего получено {len(news_items)} новостей")
    return news_items

def initialize_gemini_with_facts(facts):
    """Инициализирует Gemini с базой фактов"""
    
    print("🔄 Подготавливаем промпт для инициализации...")
    initialization_prompt = f"""
Ты - опытный российский журналист-аналитик. Изучи следующую базу фактов и используй её для анализа текущих событий:

{facts}

Эти факты помогут тебе:
- Давать контекст происходящим событиям
- Анализировать причины и следствия
- Делать обоснованные прогнозы
- Объяснять связи между событиями

Подтверди, что ты изучил эту информацию и готов анализировать новости.
"""
    
    try:
        print("🔄 Создаем модель Gemini...")
        model = genai.GenerativeModel('gemini-pro')
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=500,
        )
        
        print("🔄 Отправляем запрос инициализации к Gemini API...")
        print(f"📊 Размер промпта: {len(initialization_prompt)} символов")
        
        response = model.generate_content(
            initialization_prompt,
            generation_config=generation_config
        )
        
        print("✅ Получен ответ от Gemini на инициализацию")
        print(f"📝 Длина ответа: {len(response.text)} символов")
        
        return model, response.text
        
    except Exception as e:
        print(f"❌ Ошибка инициализации Gemini: {e}")
        return None, None

def generate_commentary(model, news_items, facts):
    """Генерирует комментарий к новостям через Gemini"""
    if not news_items or not model:
        print("❌ Нет новостей или модели для генерации комментария")
        return None, None
        
    print("🔄 Формируем промпт для анализа новостей...")
    
    # Формируем список новостей для промпта
    news_text = ""
    for i, item in enumerate(news_items, 1):
        news_text += f"{i}. {item['title']}\n"
        if item['description']:
            news_text += f"   {item['description']}\n"
        news_text += f"   Источник: {item['source']}\n\n"
    
    news_analysis_prompt = f"""
Теперь проанализируй эти текущие новости, используя изученную базу фактов:

{news_text}

Напиши аналитический комментарий (400-500 слов), который включает:

1. ГЛАВНЫЕ ТРЕНДЫ: Какие основные тенденции видны в новостях?
2. КОНТЕКСТ: Как эти события связаны с известными фактами и предыдущими событиями?
3. АНАЛИЗ ПРИЧИН: Почему происходят эти события?
4. ПРОГНОЗ: Какие могут быть последствия?
5. СВЯЗИ: Как события влияют друг на друга?

Пиши профессионально, объективно, опираясь на факты. Структурируй ответ с подзаголовками.
"""
    
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=1200,
        )
        
        print("🔄 Отправляем запрос анализа новостей к Gemini API...")
        print(f"📊 Размер промпта: {len(news_analysis_prompt)} символов")
        
        response = model.generate_content(
            news_analysis_prompt,
            generation_config=generation_config
        )
        
        print("✅ Получен ответ от Gemini с анализом")
        print(f"📝 Длина анализа: {len(response.text)} символов")
        
        # Проверяем на блокировку контента
        if response.candidates[0].finish_reason.name == "SAFETY":
            print("⚠️ Контент заблокирован системой безопасности")
            return "Комментарий не может быть сгенерирован из-за ограничений безопасности.", None
        
        return response.text, news_analysis_prompt
        
    except Exception as e:
        print(f"❌ Ошибка генерации комментария: {e}")
        return None, None

def save_commentary(commentary, news_items, initialization_response, news_prompt):
    """Сохраняет комментарий в файл"""
    print("🔄 Сохраняем результаты...")
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    date_formatted = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Создаем папку если её нет
    os.makedirs('commentary', exist_ok=True)
    
    # Сохраняем основной комментарий
    main_filename = f'commentary/news_commentary_{timestamp}.md'
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
    
    print(f"✅ Основной комментарий сохранен: {main_filename}")
    
    # Сохраняем отдельный файл с полным диалогом
    dialog_filename = f'commentary/full_dialog_{timestamp}.md'
    with open(dialog_filename, 'w', encoding='utf-8') as f:
        f.write(f"# Полный диалог с Gemini - {date_formatted}\n\n")
        f.write("## 1. Инициализация с базой фактов\n\n")
        f.write("**Ответ Gemini на инициализацию:**\n")
        f.write(f"{initialization_response}\n\n")
        f.write("---\n\n")
        f.write("## 2. Запрос на анализ новостей\n\n")
        f.write("**Отправленный промпт:**\n")
        f.write(f"```\n{news_prompt}\n```\n\n")
        f.write("**Ответ Gemini:**\n")
        f.write(f"{commentary}\n\n")
    
    print(f"✅ Полный диалог сохранен: {dialog_filename}")

def main():
    print("🚀 === ЗАПУСК БОТА КОММЕНТАРИЕВ НОВОСТЕЙ ===")
    print(f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    
    # Проверяем API ключ
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ ОШИБКА: Не найден GEMINI_API_KEY в переменных окружения")
        return
    
    print(f"✅ API ключ найден (длина: {len(api_key)} символов)")
    
    # Загружаем базу фактов
    facts = load_facts()
    
    # Инициализируем Gemini с фактами
    model, initialization_response = initialize_gemini_with_facts(facts)
    if not model:
        print("❌ Не удалось инициализировать Gemini")
        return
    
    # Небольшая пауза между запросами
    print("⏳ Пауза 3 секунды между запросами...")
    time.sleep(3)
    
    # Получаем новости
    news_items = get_news()
    
    if not news_items:
        print("❌ Не удалось получить новости")
        return
    
    # Пауза перед вторым запросом
    print("⏳ Пауза 2 секунды перед анализом...")
    time.sleep(2)
    
    # Генерируем анализ
    commentary, news_prompt = generate_commentary(model, news_items, facts)
    
    if commentary:
        save_commentary(commentary, news_items, initialization_response, news_prompt)
        print("🎉 ВСЕ ГОТОВО! Анализ успешно сгенерирован и сохранен!")
    else:
        print("❌ Не удалось сгенерировать комментарий")

if __name__ == "__main__":
    main()
