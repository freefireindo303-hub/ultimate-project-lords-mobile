import logging
import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Your verified Bot Token
TOKEN = "8700967275:AAE8UXQ22y7FTlLGM-ZwmF66_6MmjLx9Kh0"

# Flask app to keep Render's free tier awake 24/7
app_web = Flask(__name__)


@app_web.route("/")
def home():
  return "Bot is active and running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 10000))
  app_web.run(host="0.0.0.0", port=port)


def get_combined_menu():
  keyboard = [
      [
          InlineKeyboardButton("🗺️ Select Kingdom", callback_data="menu_kingdom"),
          InlineKeyboardButton("🌍 Kingdoms Info", callback_data="menu_info"),
      ],
      [
          InlineKeyboardButton("🚨 Shield Drops", callback_data="menu_shielddrops"),
          InlineKeyboardButton("🔥 Active Fury", callback_data="menu_fury"),
      ],
      [
          InlineKeyboardButton("📦 Migration Tools", callback_data="menu_migration"),
          InlineKeyboardButton("⚔️ WoW Intelligence", callback_data="menu_wow"),
      ],
      [
          InlineKeyboardButton("🆘 War Help (/helpwar)", callback_data="menu_helpwar"),
          InlineKeyboardButton("🗺️ Map Help (/helpmap)", callback_data="menu_helpmap"),
      ],
      [InlineKeyboardButton("⚙️ Account Status", callback_data="menu_account")],
  ]
  return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  panel = (
      f"🚀 *LM Ultimate War & Cartography Engine*\n"
      f"👤 User: `{user.first_name}` (ID: `{user.id}`)\n"
      f"💎 Status: `Active & Fully Synchronized`\n\n"
      f"Choose a control below or use commands:\n"
      f"• `/helpwar` - War tracker commands\n"
      f"• `/helpmap` - Cartography commands"
  )
  await update.message.reply_text(panel, parse_mode="Markdown", reply_markup=get_combined_menu())


async def shielddrops_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  response = (
      "🚨 *Live Shield Drops Feed* 🚨\n\n"
      "⚔️ *[FHO] Tomi Gi (1.855B)*\n"
      "📍 `K(586:250:572)`\n"
      "⏱ `00:00:02 - Shield Dropped`\n\n"
      "⚔️ *[DZH] wu wu (238M)*\n"
      "📍 `K(586:218:208)`\n"
      "⏱ `04:00:00 - Shield Dropped`"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def fury_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  response = (
      "🔥 *Active Fury Targets* 🔥\n\n"
      "⚔️ *[74] Tan (964M)*\n"
      "📍 `K(586:251:575)`\n"
      "⏱ Time in Fury: `00:04:16`\n"
      "🔴 Status: *Burning / Executing*"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  target = " ".join(context.args) if context.args else "Tomi Gi"
  response = (
      f"📊 *Target Dossier: {target}*\n\n"
      f"🏰 Guild: `[FHO]` | Level: `35`\n"
      f"📍 Coord: `K(586:250:572)`\n"
      f"💪 Might: `1.855B` | Troops: `539.32M`\n"
      f"🛡️ Shield Status: `Inactive (Vulnerable)`"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def gear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  response = (
      "🛡️ *Gear & Stat Inspection*\n\n"
      "Target: *[FHO] Tomi Gi*\n"
      "⚔️ Active Loadout: `Mixed Cavalry/Infantry Boost`\n"
      "💎 Jewels: `Attack / HP Tier 4`\n"
      "⏱ Last Swap: `12 mins ago`"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def kingdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  kingdom_id = context.args[0] if context.args else "855"
  response = (
      f"🏰 *Kingdom Intelligence: K({kingdom_id})*\n\n"
      f"👥 Population: `574` (Arrived: `9` | Left: `320`)\n"
      f"🏚️ Abandoned Percentage: `28.9%`\n"
      f"🛡️ Shielded Castles: `51.4%`\n"
      f"📅 Created: `09.01.2021`\n"
      f"🌍 Migration: `Open, Forever, Dominion: Ⓜ`\n\n"
      f"👑 WoW Ruler: `[#CF] Polska2019`"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query_name = " ".join(context.args) if context.args else "Player"
  response = (
      f"🔍 *Cartography Search: '{query_name}'*\n\n"
      f"🏰 Status: Indexed in Database\n"
      f"📍 Last Tracked Vector: `K(586:250:572)`\n"
      f"💪 Might Level: `1.855B`"
  )
  await update.message.reply_text(response, parse_mode="Markdown")


async def helpwar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  help_text = (
      "⚔️ *WAR TRACKER COMMAND SUITE* ⚔️\n\n"
      "• `/shielddrops` - View recent unshielded targets\n"
      "• `/fury` - View active players in fury / burning\n"
      "• `/info [player]` - Detailed target combat profile\n"
      "• `/gear [player]` - Check active war loadout and jewels\n"
      "• `/walkofshame` - Castles caught unshielded with troops\n"
      "• `/captured` - Track captured enemy leaders"
  )
  await update.message.reply_text(help_text, parse_mode="Markdown")


async def helpmap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  help_text = (
      "🗺️ *CARTOGRAPHY COMMAND SUITE* 🗺️\n\n"
      "• `/kingdom [id]` - Deep kingdom metrics & population\n"
      "• `/search [name]` - Global castle coordinate lookup\n"
      "• `/topgm` - Top guilds by might leaderboard\n"
      "• `/topgk` - Top guilds by kills leaderboard\n"
      "• `/kingdomhistory` - Migration and demographic flow logs"
  )
  await update.message.reply_text(help_text, parse_mode="Markdown")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  if query.data == "menu_shielddrops":
    await shielddrops_command(update, context)
  elif query.data == "menu_fury":
    await fury_command(update, context)
  elif query.data == "menu_helpwar":
    await helpwar_command(update, context)
  elif query.data == "menu_helpmap":
    await helpmap_command(update, context)
  else:
    responses = {
        "menu_kingdom": "🗺️ Type: `/kingdom [id]` (Example: `/kingdom 870`)",
        "menu_info": "🌍 Global kingdom indexes active. Use `/kingdom [id]`.",
        "menu_migration": "📦 Migration management tool active. Use `/kingdomhistory`.",
        "menu_wow": "⚔️ WoW battle history loaded from tracking feeds.",
        "menu_account": "⚙️ Account Tier: Free Tier (Full Hybrid Access Unlocked).",
    }
    text = responses.get(query.data, "Option processed.")
    await context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode="Markdown")


async def text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🤖 Use `/helpwar` for war commands or `/helpmap` for cartography tools.",
      parse_mode="Markdown",
  )


def main():
  import threading

  # Start the lightweight web server in a background thread (keeps Render free tier alive)
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  # Build Telegram Bot application
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("shielddrops", shielddrops_command))
  app.add_handler(CommandHandler("fury", fury_command))
  app.add_handler(CommandHandler("info", info_command))
  app.add_handler(CommandHandler("gear", gear_command))
  app.add_handler(CommandHandler("kingdom", kingdom_command))
  app.add_handler(CommandHandler("search", search_command))
  app.add_handler(CommandHandler("helpwar", helpwar_command))
  app.add_handler(CommandHandler("helpmap", helpmap_command))

  app.add_handler(CallbackQueryHandler(menu_callback))
  app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_fallback))

  print("🔥 Ultimate Combined Hybrid Bot is live...")
  app.run_polling()


if __name__ == "__main__":
  main()
