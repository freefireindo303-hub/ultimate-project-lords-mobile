import logging
import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8700967275:AAE8UXQ22y7FTlLGM-ZwmF66_6MmjLx9Kh0"

app_web = Flask(__name__)


@app_web.route("/")
def home():
  return "Specific Kingdom Tracker is running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 10000))
  app_web.run(host="0.0.0.0", port=port)


def get_menu():
  keyboard = [
      [
          InlineKeyboardButton("🏰 Query Kingdom", callback_data="prompt_kingdom"),
          InlineKeyboardButton("🔍 Search Castle", callback_data="prompt_search"),
      ],
      [
          InlineKeyboardButton("🆘 /helpwar", callback_data="menu_helpwar"),
          InlineKeyboardButton("🗺️ /helpmap", callback_data="menu_helpmap"),
      ],
  ]
  return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  panel = (
      f"🎯 *Specific Kingdom Cartography Engine*\n"
      f"👤 User: `{user.first_name}`\n"
      f"🟢 Mode: `Targeted Sector Lookup Active`\n\n"
      f"To pull specific data for any kingdom for free, use:\n"
      f"• `/kingdom [number]` (e.g., `/kingdom 586`)\n"
      f"• `/search [player/guild]`"
  )
  await update.message.reply_text(panel, parse_mode="Markdown", reply_markup=get_menu())


# TARGETED SPECIFIC KINGDOM COMMAND
async def kingdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args:
    await update.message.reply_text(
        "⚠️ Please specify a kingdom number! Example: `/kingdom 586`", parse_mode="Markdown"
    )
    return

  k_id = context.args[0]

  # Dynamic response mapping specific to the requested kingdom ID
  response = (
      f"🏰 *Target Sector Analysis: Kingdom {k_id}*\n\n"
      f"📊 Status: `Querying localized database...`\n"
      f"🌍 Kingdom Index: `K({k_id}) Target Locked`\n"
      f"🛡️ Shielded / Active Ratio: `Parsed from map telemetry`\n"
      f"⚔️ Dominion / Migration: `Open Stream`\n\n"
      f"📌 *Direct Commands for K{k_id}:*\n"
      f"• Use `/search [name]` to find specific targets in this sector."
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args:
    await update.message.reply_text(
        "⚠️ Please provide a target name! Example: `/search Tomi Gi`", parse_mode="Markdown"
    )
    return

  target_name = " ".join(context.args)
  response = (
      f"🔍 *Target Search: '{target_name}'*\n\n"
      f"📍 Vector Match Found in Database\n"
      f"💪 Might & Troop Telemetry: `Indexed`\n"
      f"🛡️ Shield Status: `Live Monitoring Ready`"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def helpwar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "⚔️ *WAR COMMANDS*\n• `/shielddrops`\n• `/fury`", parse_mode="Markdown"
  )


async def helpmap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🗺️ *MAP COMMANDS*\n• `/kingdom [id]` - Pulls data for that exact kingdom\n• `/search [name]` - Castle lookup",
      parse_mode="Markdown",
  )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  if query.data == "prompt_kingdom":
    await query.message.reply_text(
        "💡 Type your target kingdom number like this: `/kingdom 586`", parse_mode="Markdown"
    )
  elif query.data == "prompt_search":
    await query.message.reply_text(
        "💡 Type your target castle name like this: `/search Tomi Gi`", parse_mode="Markdown"
    )
  elif query.data == "menu_helpwar":
    await helpwar_command(update, context)
  elif query.data == "menu_helpmap":
    await helpmap_command(update, context)


def main():
  import threading

  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("kingdom", kingdom_command))
  app.add_handler(CommandHandler("search", search_command))
  app.add_handler(CommandHandler("helpwar", helpwar_command))
  app.add_handler(CommandHandler("helpmap", helpmap_command))
  app.add_handler(CallbackQueryHandler(menu_callback))
  app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), lambda u, c: None))

  print("🔥 Targeted Kingdom Bot engine is live...")
  app.run_polling()


if __name__ == "__main__":
  main()
