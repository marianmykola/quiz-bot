import json
import os
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Загружаем вопросы
with open("russian_trivia_150_questions.json", encoding="utf-8") as f:
    QUESTIONS = json.load(f)["quiz"]

user_data = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    selected_questions = random.sample(QUESTIONS, 10)

    user_data[user_id] = {
        "score": 0,
        "current_q": 0,
        "questions": selected_questions
    }

    await send_question(update, context)

# Отправка вопроса
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data or "questions" not in user_data[user_id]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="ℹ️ Пожалуйста, начните игру с команды /start"
        )
        return

    data = user_data[user_id]
    q_index = data["current_q"]

    if q_index >= len(data["questions"]):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🏁 Викторина окончена!\n🎯 Ваш результат: {data['score']} из {len(data['questions'])}"
        )
        return

    question = data["questions"][q_index]
    options = question["options"].copy()
    random.shuffle(options)

    # сохраняем перемешанные варианты
    data["questions"][q_index]["shuffled_options"] = options

    keyboard = [
        [InlineKeyboardButton(f"🔘 {opt}", callback_data=str(i))]
        for i, opt in enumerate(options)
    ]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"❓ Вопрос {q_index + 1} из {len(data['questions'])}:\n\n<b>{question['question']}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# Обработка ответов
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = user_data.get(user_id)
    if not data:
        await query.edit_message_text("ℹ️ Пожалуйста, начните игру с команды /start")
        return

    q_index = data["current_q"]
    if q_index >= len(data["questions"]):
        await query.edit_message_text(
            f"🏁 Викторина окончена!\n🎯 Ваш результат: {data['score']} из {len(data['questions'])}"
        )
        return

    question = data["questions"][q_index]
    shuffled = data["questions"][q_index]["shuffled_options"]
    selected_index = int(query.data)
    selected = shuffled[selected_index]
    correct = question["answer"]

    if selected == correct:
        data["score"] += 1
        response = "✅ Правильно!"
    else:
        response = f"❌ Неправильно.\n✔️ Правильный ответ: <b>{correct}</b>"

    data["current_q"] += 1

    if data["current_q"] >= len(data["questions"]):
        keyboard = [[InlineKeyboardButton("🔄 Сыграть снова", callback_data="restart")]]
        await query.edit_message_text(
            f"{response}\n\n🏁 Викторина окончена!\n🎯 Ваш результат: {data['score']} из {len(data['questions'])}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(response, parse_mode="HTML")
        await send_question(update, context)

# Обработка рестарта
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    selected_questions = random.sample(QUESTIONS, 10)

    user_data[user_id] = {
        "score": 0,
        "current_q": 0,
        "questions": selected_questions
    }

    await query.edit_message_text("🔄 Игра перезапущена!")
    await send_question(update, context)

# Запуск бота
async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # example: https://your-app.up.railway.app
    PORT = int(os.getenv("PORT", 8080))

    app = ApplicationBuilder().token(TOKEN).build()

    # Register handlers here
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    app.add_handler(CallbackQueryHandler(handle_answer))

    # Set webhook (important!)
    await app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    print("🔗 Бот запущен с использованием webhook...")

    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook"
    )

if __name__ == "__main__":
    asyncio.run(main())
