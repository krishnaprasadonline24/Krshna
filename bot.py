import json
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import TOKEN, ADMIN_ID, DEFAULT_TIMEOUT, ADMIN_TIMEOUT

# Load/save JSON data
def load_data(filename: str) -> dict | list:
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [] if "users" in filename else {}

def save_data(data: dict | list, filename: str) -> None:
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# Quick-lock button
async def quick_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_states = load_data("user_states.json")
    
    if user_id not in user_states:
        user_states[user_id] = {
            "is_locked": False,
            "last_active": time.time(),
        }
    
    keyboard = [
        [InlineKeyboardButton(
            "🔒 Lock Me" if not user_states[user_id]["is_locked"] else "🔓 Unlock Me",
            callback_data=f"toggle_{user_id}"
        )]
    ]
    await update.message.reply_text(
        "🛠️ Control your session:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle button clicks
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.data.split("_")[1]
    user_states = load_data("user_states.json")
    
    user_states[user_id]["is_locked"] = not user_states[user_id]["is_locked"]
    user_states[user_id]["last_active"] = time.time()
    
    save_data(user_states, "user_states.json")
    
    new_text = "🔓 Unlock Me" if user_states[user_id]["is_locked"] else "🔒 Lock Me"
    await query.edit_message_text(
        text=f"Status: {'🔒 Locked' if user_states[user_id]['is_locked'] else '🔓 Unlocked'}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(new_text, callback_data=f"toggle_{user_id}")]])
    )
    await query.answer()

# Promote/demote users (admin-only)
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Admin only!")
        return
    
    target = context.args[0] if context.args else None
    if not target:
        await update.message.reply_text("Usage: /promote <user_id>")
        return
    
    admins = load_data("admins.json")
    if target not in admins:
        admins.append(target)
        save_data(admins, "admins.json")
        await update.message.reply_text(f"✅ User {target} promoted!")
    else:
        await update.message.reply_text("⚠️ Already an admin!")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Admin only!")
        return
    
    target = context.args[0] if context.args else None
    if not target:
        await update.message.reply_text("Usage: /demote <user_id>")
        return
    
    admins = load_data("admins.json")
    if target in admins:
        admins.remove(target)
        save_data(admins, "admins.json")
        await update.message.reply_text(f"✅ User {target} demoted!")
    else:
        await update.message.reply_text("⚠️ Not an admin!")

# Check session status
def is_locked(user_id: int) -> bool:
    user_states = load_data("user_states.json")
    user_data = user_states.get(str(user_id), {})
    
    if user_data.get("is_locked", False):
        return True
    
    last_active = user_data.get("last_active", 0)  # Default to epoch time
    timeout = ADMIN_TIMEOUT if str(user_id) in load_data("admins.json") else DEFAULT_TIMEOUT
    
    return (time.time() - last_active) > timeout

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_states = load_data("user_states.json")
    
    # Update last activity time
    user_states[str(user_id)] = {
        "last_active": time.time(),
        "is_locked": user_states.get(str(user_id), {}).get("is_locked", False)
    }
    save_data(user_states, "user_states.json")
    
    if is_locked(user_id):
        await update.message.reply_text("🔒 Session locked! Use /quick_lock to unlock.")
    else:
        await update.message.reply_text("✅ Active session!")

# Main bot setup
async def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("promote", promote))
    application.add_handler(CommandHandler("demote", demote))
    application.add_handler(CommandHandler("quick_lock", quick_lock))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running...")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())