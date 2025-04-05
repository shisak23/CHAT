import json
import random
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

BOT_TOKEN = "7846035245:AAHvL_4fxEm-4N1TcV_8Qk86MSFQviKCwOw"
OWNER_ID = 7814078698  # Replace with your Telegram user ID
OWNER_USERNAME = "@MRSKYX0"  # Replace with your Telegram @username

USER_DATA_FILE = "users.json"
TICKET_DATA_FILE = "tickets.json"

forward_map = {}
user_ids = set()
tickets = {}

def load_data():
    global user_ids, tickets
    try:
        with open(USER_DATA_FILE, "r") as f:
            user_ids = set(json.load(f))
    except:
        user_ids = set()

    try:
        with open(TICKET_DATA_FILE, "r") as f:
            tickets = json.load(f)
    except:
        tickets = {}

def save_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(list(user_ids), f)
    with open(TICKET_DATA_FILE, "w") as f:
        json.dump(tickets, f)

def get_keyboard(is_owner=False):
    if is_owner:
        return ReplyKeyboardMarkup(
            [["📥 start", "📖 help"], ["📢 broadcast", "🎫 support"]],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            [["📥 start", "📖 help", "🎫 support", "📂 check status"]],
            resize_keyboard=True
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_owner = user.id == OWNER_ID
    keyboard = get_keyboard(is_owner)

    welcome_msg = (
        f"👋 Hello {user.first_name}!\n"
        "🤖 *Welcome to the Support Bot!*\n\n"
        "📝 Send a message or use '🎫 support' to create a ticket.\n"
        "📂 Use '📂 Check Status' to track your support request."
    )

    await update.message.reply_text(welcome_msg, reply_markup=keyboard, parse_mode="Markdown")

    if not is_owner:
        user_ids.add(user.id)
        save_data()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help Menu:*\n"
        "• 📥 start - Start the bot\n"
        "• 📖 help - Show help\n"
        "• 📢 broadcast <message> - Broadcast message to all users (owner only)\n"
        "• 🎫 support <your issue> - Create a support ticket\n"
        "• 📂 check status <ticket ID> - Get your support ticket status",
        parse_mode="Markdown"
    )

async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    if user.id == OWNER_ID:
        return

    user_ids.add(user.id)
    save_data()

    sent = await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"📩 Message from @{user.username or user.first_name} (ID: {user.id}):\n\n{message.text}"
    )
    forward_map[sent.message_id] = user.id
    await message.reply_text("✅ Your message has been sent to the owner. 📬")

async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message or update.effective_user.id != OWNER_ID:
        return

    replied_msg_id = message.reply_to_message.message_id
    original_user_id = forward_map.get(replied_msg_id)

    if original_user_id:
        await context.bot.send_message(
            chat_id=original_user_id,
            text=f"📥 *Reply from Owner:*\n\n💬 {message.text}",
            parse_mode="Markdown"
        )
        await message.reply_text("✅ Reply delivered! 🚀")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text(
            "📢 *Broadcast Usage:*\n"
            "`/broadcast Your message here`\n"
            "_It will go to all users._",
            parse_mode="Markdown"
        )
        return

    msg = "📣 *Broadcast:*\n\n" + parts[1]
    success = 0
    failed = 0

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=msg, parse_mode="Markdown")
            success += 1
        except:
            failed += 1

    await update.message.reply_text(
        f"📊 Broadcast Summary:\n✅ Sent: {success}\n❌ Failed: {failed}"
    )

async def support_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    ticket_id = str(random.randint(100000, 999999))  # ✅ 6-digit ticket ID

    tickets[ticket_id] = {
        "user_id": user.id,
        "status": "Pending"
    }
    save_data()

    caption_text = message.caption or message.text or ""
    user_info = f"🎫 *New Support Ticket*\n\n" \
                f"Ticket ID: `{ticket_id}`\n" \
                f"User: @{user.username or user.first_name} (ID: {user.id})\n" \
                f"📝 *Issue:* {caption_text}"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 In Progress", callback_data=f"inprogress_{ticket_id}"),
            InlineKeyboardButton("✅ Completed", callback_data=f"complete_{ticket_id}")
        ]
    ])

    if message.photo:
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=message.photo[-1].file_id,
            caption=user_info,
            reply_markup=buttons,
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=user_info,
            reply_markup=buttons,
            parse_mode="Markdown"
        )

    await message.reply_text(
        f"✅ Support ticket created with ID: `{ticket_id}`\n"
        f"🔍 Use 📂 Check Status to track it.\n"
        f"Support contact: @{OWNER_USERNAME}",
        parse_mode="Markdown"
    )

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    parts = text.split()
    if len(parts) < 3:
        await update.message.reply_text("❗ Usage: check status <ticket_id>")
        return

    ticket_id = parts[-1]
    ticket = tickets.get(ticket_id)

    if ticket and ticket["user_id"] == update.effective_user.id:
        await update.message.reply_text(
            f"📂 Ticket ID: `{ticket_id}`\n"
            f"🟢 Status: *{ticket['status']}*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Invalid or unauthorized Ticket ID.")

async def handle_status_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data or update.effective_user.id != OWNER_ID:
        return

    if data.startswith("inprogress_"):
        ticket_id = data.split("_")[1]
        tickets[ticket_id]["status"] = "In Progress"
        save_data()
        await query.edit_message_reply_markup()
        await query.message.reply_text(f"🔄 Ticket `{ticket_id}` marked as In Progress", parse_mode="Markdown")
    elif data.startswith("complete_"):
        ticket_id = data.split("_")[1]
        tickets[ticket_id]["status"] = "Completed"
        save_data()
        await query.edit_message_reply_markup()
        await query.message.reply_text(f"✅ Ticket `{ticket_id}` marked as Completed", parse_mode="Markdown")

async def command_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or update.message.caption or "").strip().lower()

    command_map = {
        "📥 start": "start",
        "📖 help": "help",
        "📢 broadcast": "broadcast",
        "🎫 support": "support",
        "📂 check status": "check status"
    }

    for label, command in command_map.items():
        if text.startswith(label.lower()):
            text = command
            break

    if text.startswith("/"):
        text = text[1:]

    if text.startswith("start"):
        await start(update, context)
    elif text.startswith("help"):
        await help_command(update, context)
    elif text.startswith("broadcast") and update.effective_user.id == OWNER_ID:
        await broadcast(update, context)
    elif text.startswith("support"):
        await support_ticket(update, context)
    elif text.startswith("check status"):
        await check_status(update, context)
    else:
        await forward_to_owner(update, context)

def main():
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_status_update))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_owner_reply))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, command_router))
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
                       
