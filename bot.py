from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update, Bot
import asyncio
import nest_asyncio
import db
import sqlite3
import openai
import os
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

# Get keys from environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI key
openai.api_key = OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
bot = Bot(token=TOKEN)
nest_asyncio.apply()
db.init_db()  # initialize database

DB_FILE = "db.sqlite3"  # your DB file

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I’m your Vehicle Care Bot 🚗\n"
        "Commands:\n"
        "/add <vehicle_name> - Add a vehicle\n"
        "/list - List your vehicles\n"
        "/update <vehicle_name> fuel/oil <km> - Update fuel or oil\n"
        "/status - Check vehicle status\n"
        "/remove <vehicle_name> - Remove a vehicle\n"
        "/suggest - Get AI suggestions on which vehicle to use\n"
        "/resetme - Reset all your vehicle data"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /add <vehicle_name>")
        return
    name = " ".join(context.args)
    db.add_vehicle(user_id, name)
    await update.message.reply_text(f"Vehicle '{name}' added!")

async def list_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = db.list_vehicles(user_id)
    if not vehicles:
        await update.message.reply_text("You have no vehicles yet.")
        return
    
    msg = "Your vehicles:\n"
    for v in vehicles:
        # v = (id, name, fuel, oil, tyre)
        msg += f"🚗 {v[1]} | ⛽ Fuel: {v[2]} km | 🛢 Oil: {v[3]} km | 🛞 Tyre: {v[4]}%\n"
    
    await update.message.reply_text(msg)

async def update_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /update <vehicle_name> fuel/oil <km>")
        return

    name, field, km = context.args
    if field not in ["fuel", "oil"]:
        await update.message.reply_text("Field must be 'fuel' or 'oil'")
        return

    try:
        km = int(km)
    except:
        await update.message.reply_text("KM must be a number")
        return

    db.update_vehicle_by_name(user_id, name, field, km)
    await update.message.reply_text(f"Vehicle '{name}' updated: {field} = {km} km")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = db.list_vehicles(user_id)
    if not vehicles:
        await update.message.reply_text("You have no vehicles yet.")
        return
    reply = "🚗 Vehicle Status:\n"
    for v in vehicles:
        vid, name, fuel, oil, tyre = v
        reply += f"\n{name}:\n   ⛽ Fuel left: {fuel} km\n   🛢️ Oil left: {oil} km\n   🛞 Tyre: {tyre}%\n"
    await update.message.reply_text(reply)

from db import reset_user
async def reset_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reset_user(user_id)
    await update.message.reply_text("🗑️ All your vehicle data has been reset!")

async def remove_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❌ Usage: /remove <vehicle_name>")
        return

    name = " ".join(context.args)
    db.remove_vehicle_by_name(user_id, name)
    await update.message.reply_text(f"🗑️ Vehicle '{name}' removed.")

# ==================== AI HELPER ====================
def ai_suggestion(vehicles):
    msg = "🚗 AI Vehicle Suggestions:\n"
    for v in vehicles:
        name = v[1]
        fuel = v[2]
        oil = v[3]
        alerts = []

        if fuel <= 20:
            alerts.append("🔴 Low Fuel (Critical!)")
        elif fuel <= 50:
            alerts.append("⚠️ Fuel Low")

        if oil <= 300:
            alerts.append("🔴 Oil Change Needed!")
        elif oil <= 500:
            alerts.append("⚠️ Oil Change Soon")

        alert_text = " | ".join(alerts) if alerts else "✅ Healthy"
        msg += f"{name}: {alert_text}\n"

    return msg

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = db.list_vehicles(user_id)
    if not vehicles:
        await update.message.reply_text("You have no vehicles yet.")
        return
    suggestion = ai_suggestion(vehicles)
    await update.message.reply_text(suggestion)

# ==================== CLEAN simulate_vehicle_usage FUNCTION ====================
async def simulate_vehicle_usage(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # Fetch all vehicles
    cur.execute("SELECT id, user_id, name, fuel_km_left, oil_km_left, tyre FROM vehicles")
    vehicles = cur.fetchall()
    
    for v in vehicles:
        vid, user_id, name, fuel, oil, tyre = v
        # Reduce safely
        fuel = max(0, fuel - 5)
        oil = max(0, oil - 10)
        tyre = max(0, tyre - 1)

        # Update DB
        cur.execute(
            "UPDATE vehicles SET fuel_km_left=?, oil_km_left=?, tyre=? WHERE id=?",
            (fuel, oil, tyre, vid)
        )

        # Build notification
        status_msg = (
            f"🚗 {name}\n"
            f"⛽ Fuel: {fuel} km\n"
            f"🛢 Oil: {oil} km\n"
            f"🛞 Tyre: {tyre}%\n"
        )

        # Simple suggestion
        if fuel < 20:
            suggestion = "⚠️ Low fuel! Please refuel soon."
        elif oil < 200:
            suggestion = "⚠️ Oil running low! Schedule maintenance."
        elif tyre < 50:
            suggestion = "⚠️ Tyre health is low, check pressure/replace."
        else:
            suggestion = "✅ All good! You can drive safely."

        # Send notification
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{status_msg}\n💡 Suggestion: {suggestion}"
            )
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

    conn.commit()
    conn.close()

# ==================== MAIN ====================
if __name__ == "__main__":
    db.init_db()
    app = Application.builder().token(TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_vehicles))
    app.add_handler(CommandHandler("update", update_vehicle))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("remove", remove_vehicle))
    app.add_handler(CommandHandler("suggest", suggest))
    app.add_handler(CommandHandler("resetme", reset_user_cmd))

    # JobQueue for automatic updates every 60 seconds
    job_queue = app.job_queue
    job_queue.run_repeating(simulate_vehicle_usage, interval=60, first=10)

    # Run bot
    app.run_polling()
