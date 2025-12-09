import asyncio
import re
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI, APIError
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time


from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

# ----------------- Ключи ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise Exception("❗️Отсутствуют TELEGRAM_TOKEN или OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------- FSM -----------------
class Form(StatesGroup):
    LANGUAGE = State()
    LINK = State()
    MANUAL_PRICE = State()
    MANUAL_RATING_REVIEWS = State()
    MANUAL_DESCRIPTION = State()
    MANUAL_SELLER = State()
    MANUAL_PHOTO = State()

# ----------------- Тексты на разных языках -----------------
LANG_TEXT = {
    "Русский язык": {
        "greeting": "👋 Привет! Я — SAFEX, ИИ-детектор подделок и подозрительных товаров. Отправь ссылку на товар.",
        "analyzing": "🔍 Анализирую товар, подожди...",
        "manual_price": "💲 Укажи цену товара:",
        "manual_rating": "⭐ Введи рейтинг и отзывы товара:",
        "manual_description": "🔍 Введи подозрительные слова из описания (если есть):",
        "manual_seller": "🏪 Введи продавца или магазин:",
        "manual_photo": "📸 Прикрепи фото товара (или пропусти):"
    },
    "Қаз яз": {
        "greeting": "👋 Сәлем! Мен — SAFEX, жалған немесе күдікті тауарларды анықтайтын ИИ. Тауарға сілтеме жіберіңіз.",
        "analyzing": "🔍 Тауарды талдап жатырмын, күте тұрыңыз...",
        "manual_price": "💲 Тауардың бағасын көрсетіңіз:",
        "manual_rating": "⭐ Баға мен пікірлерді енгізіңіз:",
        "manual_description": "🔍 Сипаттамадан күдікті сөздерді енгізіңіз:",
        "manual_seller": "🏪 Сатушыны немесе дүкенді енгізіңіз:",
        "manual_photo": "📸 Тауардың суретін тіркеңіз (немесе өткізіп жіберіңіз):"
    },
    "English": {
        "greeting": "👋 Hi! I'm SAFEX, an AI detector for counterfeit and suspicious products. Send a product link.",
        "analyzing": "🔍 Analyzing the product, please wait...",
        "manual_price": "💲 Enter the product price:",
        "manual_rating": "⭐ Enter the rating and reviews:",
        "manual_description": "🔍 Enter suspicious words from description (if any):",
        "manual_seller": "🏪 Enter the seller or store:",
        "manual_photo": "📸 Attach a product photo (or skip):"
    }
}

# ----------------- Парсинг через Selenium -----------------
def parse_product_selenium(link: str):
    options = Options()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(link)
        time.sleep(3)  # ждём JS
        title = driver.title
        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, '[class*=price], [class*=cost]')
            price = price_elem.text
        except:
            price = "Неизвестно"
        try:
            reviews_elements = driver.find_elements(By.CSS_SELECTOR, '[class*=review-text], [class*=review-body]')
            reviews = " ".join([r.text for r in reviews_elements[:5]])
        except:
            reviews = ""
        return {
            "title": title,
            "price": price,
            "rating_reviews": reviews,
            "description": "Неизвестно",
            "seller": "Неизвестно"
        }
    except Exception as e:
        print(f"Selenium error: {e}")
        return None
    finally:
        driver.quit()

# ----------------- FSM Start -----------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Русский язык"), types.KeyboardButton(text="Қаз яз"), types.KeyboardButton(text="English")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Выберите язык / Select language:", reply_markup=keyboard)
    await state.set_state(Form.LANGUAGE)

@dp.message(Form.LANGUAGE)
async def language_choice(message: types.Message, state: FSMContext):
    await state.update_data(language=message.text)
    texts = LANG_TEXT.get(message.text, LANG_TEXT["Русский язык"])
    await message.answer(texts["greeting"], reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.LINK)

# ----------------- Обработка ссылки -----------------
@dp.message(Form.LINK)
async def get_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if not re.match(r"https?://", link):
        await message.answer("⚠️ Отправь корректную ссылку, начиная с http:// или https://")
        return
    await state.update_data(link=link)
    data = parse_product_selenium(link)
    if data:
        await state.update_data(**data)
        await analyze_product(message, state)
    else:
        await message.answer("⚠️ Не удалось получить данные автоматически. Заполни вручную.")
        await state.set_state(Form.MANUAL_PRICE)

# ----------------- Ручной ввод -----------------
@dp.message(Form.MANUAL_PRICE)
async def manual_price_step(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    texts = LANG_TEXT.get((await state.get_data()).get("language"), LANG_TEXT["Русский язык"])
    await message.answer(texts["manual_rating"])
    await state.set_state(Form.MANUAL_RATING_REVIEWS)

@dp.message(Form.MANUAL_RATING_REVIEWS)
async def manual_rating_step(message: types.Message, state: FSMContext):
    await state.update_data(rating_reviews=message.text)
    texts = LANG_TEXT.get((await state.get_data()).get("language"), LANG_TEXT["Русский язык"])
    await message.answer(texts["manual_description"])
    await state.set_state(Form.MANUAL_DESCRIPTION)

@dp.message(Form.MANUAL_DESCRIPTION)
async def manual_description_step(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    texts = LANG_TEXT.get((await state.get_data()).get("language"), LANG_TEXT["Русский язык"])
    await message.answer(texts["manual_seller"])
    await state.set_state(Form.MANUAL_SELLER)

@dp.message(Form.MANUAL_SELLER)
async def manual_seller_step(message: types.Message, state: FSMContext):
    await state.update_data(seller=message.text)
    texts = LANG_TEXT.get((await state.get_data()).get("language"), LANG_TEXT["Русский язык"])
    await message.answer(texts["manual_photo"])
    await state.set_state(Form.MANUAL_PHOTO)

@dp.message(Form.MANUAL_PHOTO)
async def manual_photo_step(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id if message.photo else "Нет фото"
    await state.update_data(photo_file_id=photo_file_id)
    await analyze_product(message, state)

# ----------------- Анализ товара -----------------
async def analyze_product(message: types.Message, state: FSMContext):
    data = await state.get_data()
    language = data.get("language", "Русский язык")
    texts = LANG_TEXT.get(language, LANG_TEXT["Русский язык"])
    await message.answer(texts["analyzing"])

    # ----------------- Локальный расчёт риска -----------------
    risk = 0
    price = data.get("price", "")
    reviews = data.get("rating_reviews", "")
    suspicious_words = ["копия", "реплика", "не оригинал", "1:1 оригинал", "серый товар"]

    # Цена
    if price and any(char.isdigit() for char in price):
        try:
            price_val = float(re.sub(r"[^\d.]", "", price))
            if price_val < 1000:
                risk += 30
        except:
            risk += 30
    else:
        risk += 30

    # Подозрительные слова
    if any(word in reviews.lower() for word in suspicious_words):
        risk += 20

    # Отсутствие продавца
    if not data.get("seller") or data.get("seller") == "Неизвестно":
        risk += 20

    # Мало отзывов
    if reviews and len(reviews.split()) < 10:
        risk += 10

    risk = min(risk, 100)

    if risk >= 70:
        emoji = "🔴 ВЫСОКИЙ РИСК"
    elif risk >= 40:
        emoji = "🟠 СРЕДНИЙ РИСК"
    else:
        emoji = "🟢 НИЗКИЙ РИСК"

    # ----------------- GPT объяснение -----------------
    prompt = f"""
You are SAFEX — an AI system that detects counterfeit products.
Data:
- Name: {data.get('title')}
- Description: {data.get('description')}
- Price: {data.get('price')}
- Rating & Reviews: {reviews}
- Seller: {data.get('seller')}
Give short reasons and advice in {language}.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                ChatCompletionSystemMessageParam(
                    role="system",
                    content="Ты эксперт по безопасности товаров."
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=prompt
                )
            ]
        )
        gpt_reply = response.choices[0].message.content
    except Exception as e:
        gpt_reply = f"❌ Ошибка GPT: {e}"

    await message.answer(f"📊 Анализ завершён!\n🧩 Риск подделки: {emoji} ({risk}%)\n{gpt_reply}")

    # Кнопки
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔁 Проверить другой товар")],
            [types.KeyboardButton(text="📚 Узнать, как отличить подделки")],
            [types.KeyboardButton(text="📩 Отправить отзыв о боте")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Что дальше?", reply_markup=keyboard)
    await state.clear()

# ----------------- Кнопка проверить другой товар -----------------
@dp.message(F.text == "🔁 Проверить другой товар")
async def check_another(message: types.Message, state: FSMContext):
    await start_cmd(message, state)

# ----------------- Запуск бота -----------------
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
