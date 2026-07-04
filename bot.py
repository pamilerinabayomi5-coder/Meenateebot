import os
import io
import asyncio
import logging
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Store user images temporarily in memory
user_images: dict[int, bytes] = {}


def build_action_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("↔️ Flip Horizontal", callback_data="flip_h"),
            InlineKeyboardButton("↕️ Flip Vertical", callback_data="flip_v"),
        ],
        [
            InlineKeyboardButton("↩️ Rotate 90° CCW", callback_data="rotate_90"),
            InlineKeyboardButton("↪️ Rotate 90° CW", callback_data="rotate_270"),
        ],
        [
            InlineKeyboardButton("🔄 Rotate 180°", callback_data="rotate_180"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to the *Image Flip & Rotate Bot*!\n\n"
        "📸 Just send me any image and I'll let you:\n"
        "• Flip it horizontally or vertically\n"
        "• Rotate it 90°, 180°, or 270°\n\n"
        "Send a photo to get started!",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *How to use this bot:*\n\n"
        "1. Send any image (photo or file)\n"
        "2. Choose an action from the buttons\n"
        "3. The transformed image will be sent back\n"
        "4. You can keep applying transformations!\n\n"
        "*Commands:*\n"
        "/start — Welcome message\n"
        "/help  — Show this help",
        parse_mode="Markdown",
    )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Accept photos or documents that are images
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("⚠️ Please send a valid image file.")
        return

    image_bytes = await file.download_as_bytearray()
    user_images[user_id] = bytes(image_bytes)

    await update.message.reply_text(
        "✅ Image received! Choose a transformation:",
        reply_markup=build_action_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    if user_id not in user_images:
        await query.edit_message_text("⚠️ No image found. Please send a new image first.")
        return

    image_data = user_images[user_id]
    img = Image.open(io.BytesIO(image_data))

    action = query.data

    if action == "flip_h":
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        caption = "↔️ Flipped Horizontally"
    elif action == "flip_v":
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        caption = "↕️ Flipped Vertically"
    elif action == "rotate_90":
        img = img.transpose(Image.ROTATE_90)
        caption = "↩️ Rotated 90° Counter-Clockwise"
    elif action == "rotate_180":
        img = img.transpose(Image.ROTATE_180)
        caption = "🔄 Rotated 180°"
    elif action == "rotate_270":
        img = img.transpose(Image.ROTATE_270)
        caption = "↪️ Rotated 90° Clockwise"
    else:
        await query.edit_message_text("❌ Unknown action.")
        return

    # Save transformed image to bytes
    output = io.BytesIO()
    fmt = img.format if img.format else "PNG"
    if fmt == "JPEG" and img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output, format=fmt)
    output.seek(0)

    # Store updated image for further transformations
    user_images[user_id] = output.getvalue()
    output.seek(0)

    await query.message.reply_photo(
        photo=output,
        caption=f"{caption}\n\nApply another transformation:",
        reply_markup=build_action_keyboard(),
    )


async def handle_non_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📸 Please send me an image (photo or image file) to get started!\n"
        "Use /help for instructions."
    )


async def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)
    )
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_image)
    )

    logger.info("Bot is running...")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
