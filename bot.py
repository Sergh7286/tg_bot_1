import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "state": "awaiting_player_count"
    }
    keyboard = [[InlineKeyboardButton("Выбрать количество игроков", callback_data="choose_players")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Нажмите кнопку ниже, чтобы выбрать количество игроков.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in user_data:
        user_data[user_id] = {"state": "awaiting_player_count"}

    data = user_data[user_id]

    if query.data == "choose_players":
        data["state"] = "awaiting_player_count"
        await query.edit_message_text("Введите количество игроков (число):")

    elif query.data == "remove_command":
        if data.get("state") != "showing_result":
            await query.answer("Сначала завершите ввод данных.")
            return
        removed_any = False
        for name in data["names"]:
            assigned = data["assigned_teams"].get(name, [])
            removed = data["removed_teams"].get(name, [])
            not_removed = [cmd for cmd in assigned if cmd not in removed]
            if not_removed:
                cmd_to_remove = random.choice(not_removed)
                removed.append(cmd_to_remove)
                data["removed_teams"][name] = removed
                removed_any = True
        if not removed_any:
            await query.answer("Все команды уже удалены.")
            return

        text = format_result(data)
        keyboard = [
            [InlineKeyboardButton("Удалить команду", callback_data="remove_command")],
            [InlineKeyboardButton("В начало", callback_data="restart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data == "restart":
        user_data[user_id] = {"state": "awaiting_player_count"}
        keyboard = [[InlineKeyboardButton("Выбрать количество игроков", callback_data="choose_players")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Вернулись в начало. Нажмите кнопку ниже, чтобы выбрать количество игроков.", reply_markup=reply_markup)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_data:
        await update.message.reply_text("Пожалуйста, начните с /start")
        return

    data = user_data[user_id]

    if data.get("state") == "awaiting_player_count":
        if not text.isdigit() or int(text) < 1:
            await update.message.reply_text("Введите корректное число игроков (больше 0).")
            return
        data["player_count"] = int(text)
        data["names"] = []
        data["state"] = "awaiting_names"
        await update.message.reply_text(f"Введите имена {data['player_count']} игроков, по одному имени на сообщение:")

    elif data.get("state") == "awaiting_names":
        name_lower = text.lower()
        if name_lower == "петух":
            await update.message.reply_text("Саня ПЕС")
            user_data[user_id] = {"state": "awaiting_player_count"}
            await update.message.reply_text("Начинаем сначала. Введите количество игроков (число):")
            return

        if len(data["names"]) < data["player_count"]:
            if name_lower in ["саня", "саша"]:
                display_name = "ПЕС 🐶🐕"
            else:
                display_name = text
            data["names"].append(display_name)
            if len(data["names"]) == data["player_count"]:
                data["state"] = "awaiting_teams_count"
                await update.message.reply_text("Введите количество команд на каждого игрока (число):")
            else:
                await update.message.reply_text(f"Введите имя игрока №{len(data['names'])+1}:")
        else:
            await update.message.reply_text("Вы уже ввели все имена.")

    elif data.get("state") == "awaiting_teams_count":
        if not text.isdigit() or int(text) < 1:
            await update.message.reply_text("Введите корректное число команд на игрока (больше 0).")
            return
        data["teams_per_player"] = int(text)
        data["teams"] = []
        data["state"] = "awaiting_teams"
        await update.message.reply_text(f"Введите {data['teams_per_player'] * data['player_count']} команд, по одной на сообщение:")

    elif data.get("state") == "awaiting_teams":
        data["teams"].append(text)
        expected = data["teams_per_player"] * data["player_count"]
        if len(data["teams"]) < expected:
            await update.message.reply_text(f"Введите команду №{len(data['teams'])+1}:")
        else:
            random.shuffle(data["teams"])
            assigned = {}
            idx = 0
            for name in data["names"]:
                assigned[name] = data["teams"][idx:idx+data["teams_per_player"]]
                idx += data["teams_per_player"]
            data["assigned_teams"] = assigned
            data["removed_teams"] = {name: [] for name in data["names"]}
            data["state"] = "showing_result"
            text = format_result(data)
            keyboard = [
                [InlineKeyboardButton("Удалить команду", callback_data="remove_command")],
                [InlineKeyboardButton("В начало", callback_data="restart")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)

    else:
        await update.message.reply_text("Неизвестное состояние. Введите /start чтобы начать заново.")

def format_result(data):
    lines = []
    for name in data["names"]:
        assigned = data["assigned_teams"].get(name, [])
        removed = data["removed_teams"].get(name, [])
        parts = []
        for cmd in assigned:
            if cmd in removed:
                parts.append(f"({cmd} - удалена)")
            else:
                parts.append(cmd)
        lines.append(f"{name}: {', '.join(parts)}")
    return "\n".join(lines)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    TOKEN = "8038319230:AAFX0CnfUIPUztntVmVenoVbqFz8dyYDGqo"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот запущен")
    app.run_polling()