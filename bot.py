import os
import telebot
import requests
from config import TOKEN
from validators import normalize_kz_phone
import database as db

os.makedirs("files", exist_ok=True)

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

def query_ai_sales_manager(user_text: str) -> str:
    products = db.get_active_products()
    products_str = ", ".join([f"{p['name']} ({p['price_kzt']} ₸)" for p in products])
    
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {
                "role": "system", 
                "content": f"Ты вежливый продавец Apple магазина в Астане. Рекомендуй: {products_str}."
            },
            {"role": "user", "content": user_text}
        ],
        "model": "openai"
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200 and res.text.strip():
            return res.text.strip()
        return "Консультант сейчас занят, задайте вопрос через минуту."
    except Exception:
        return "Сервис ИИ временно недоступен."

@bot.message_handler(commands=["start"])
def handle_start(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🍏 Каталог", "🛒 Моя корзина", "📦 Оформить заказ")
    
    user_name = message.from_user.first_name or "Клиент"
    welcome_text = (
        f"Здравствуйте, {user_name}!\n"
        "Добро пожаловать в магазин Apple Store Astana.\n\n"
        "Команды:\n"
        "• /catalog — каталог товаров\n"
        "• /buy <товар> — добавить в корзину\n"
        "• /order — оформить заказ\n"
        "• /phone <номер> — сохранить телефон\n"
        "• /stats — профиль\n\n"
        "Либо отправьте фото чека или напишите вопрос — ответит ИИ!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)

@bot.message_handler(commands=["catalog"])
def handle_catalog(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    products = db.get_active_products()
    lines = ["🍏 **Прайс-лист товаров:**\n"]
    for p in products:
        price_fmt = f"{p['price_kzt']:,}".replace(",", " ")
        lines.append(f"• **{p['name']}** — {price_fmt} ₸ (Остаток: {p['stock']} шт.)")
    lines.append("\nДля добавления в корзину введите:\n`/buy iPhone 16 Pro`")
    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

@bot.message_handler(commands=["buy"])
def handle_buy(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    try:
        item_name = message.text.split(maxsplit=1)[1].strip()
        if db.add_product_to_cart(message.chat.id, item_name):
            bot.send_message(message.chat.id, f"✅ Товар **{item_name}** добавлен в корзину!", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"❌ Товар «{item_name}» не найден. Проверьте /catalog.")
    except IndexError:
        bot.send_message(message.chat.id, "⚠️ Укажите товар: `/buy iPhone 16`", parse_mode="Markdown")

@bot.message_handler(commands=["order"])
def handle_order(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    cart = db.get_user_cart(message.chat.id)
    if not cart:
        bot.send_message(message.chat.id, "🛒 Корзина пуста. Добавьте товары через /buy.")
        return

    order_id = db.create_order_from_cart(message.chat.id)
    total = sum(i["subtotal"] for i in cart)
    total_fmt = f"{total:,}".replace(",", " ")

    msg = (
        f"🧾 **Заказ #{order_id} сформирован!**\n"
        f"Сумма: **{total_fmt} ₸**\n\n"
        "Отправьте фото квитанции об оплате в чат или укажите телефон: `/phone +77011234567`."
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(commands=["phone"])
def handle_phone(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    try:
        raw_phone = message.text.split(maxsplit=1)[1]
        valid_phone = normalize_kz_phone(raw_phone)
        if valid_phone:
            db.save_user_phone(message.chat.id, valid_phone)
            bot.send_message(message.chat.id, f"✅ Телефон сохранён: `{valid_phone}`", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Неверный номер. Пример: `+7 701 123 4567` или `87011234567`.", parse_mode="Markdown")
    except IndexError:
        bot.send_message(message.chat.id, "⚠️ Использование: `/phone +77011234567`", parse_mode="Markdown")

@bot.message_handler(commands=["stats"])
def handle_stats(message):
    stats = db.get_user_stats(message.chat.id)
    msg = (
        f"👤 Клиент: {stats['name']}\n"
        f"📞 Телефон: {stats['phone']}\n"
        f"📊 Запросов: {stats['interactions']}\n"
        f"🛒 В корзине: {stats['cart_items']} шт."
    )
    bot.send_message(message.chat.id, msg)

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    try:
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)

        local_path = f"files/receipt_{message.chat.id}_{message.message_id}.jpg"
        with open(local_path, "wb") as f:
            f.write(downloaded)

        order_id = db.attach_receipt_to_latest_order(message.chat.id, local_path)
        if order_id:
            bot.send_message(message.chat.id, f"🧾 Чек к заказу **#{order_id}** принят на проверку менеджером!", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "Фото сохранено. Чтобы привязать к оплате, сначала создайте заказ через /order.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.message_handler(content_types=["text"])
def handle_text(message):
    db.register_user(message.chat.id, message.from_user.first_name or "Клиент")
    text = message.text.strip()

    if text == "🍏 Каталог":
        handle_catalog(message)
    elif text == "🛒 Моя корзина":
        cart = db.get_user_cart(message.chat.id)
        if not cart:
            bot.send_message(message.chat.id, "Корзина пуста.")
            return
        total = sum(i["subtotal"] for i in cart)
        total_fmt = f"{total:,}".replace(",", " ")
        items = "\n".join([f"• {i['name']} x{i['quantity']} — {i['subtotal']:,} ₸".replace(",", " ") for i in cart])
        bot.send_message(message.chat.id, f"🛒 **Корзина:**\n{items}\n\n**Итого:** {total_fmt} ₸\n\nОформить: /order", parse_mode="Markdown")
    elif text == "📦 Оформить заказ":
        handle_order(message)
    else:
        bot.send_chat_action(message.chat.id, "typing")
        reply = query_ai_sales_manager(text)
        bot.send_message(message.chat.id, reply)

print("🚀 БОТ УСПЕШНО ЗАПУЩЕН! ЖДУ СООБЩЕНИЙ В TELEGRAM...")
bot.infinity_polling()
