import os
import discord
from discord.ext import commands
import datetime
from datetime import timezone
from flask import Flask, jsonify
import threading

print("🚀 Starting Discord CS2 Bot...")

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

bot_ready = False

@app.route('/')
def home():
    return "✅ Bot ONLINE"

@app.route('/ping')
def ping():
    return jsonify({"status": "online", "timestamp": datetime.datetime.now(timezone.utc).isoformat()})

@app.route('/test')
def test():
    return "OK"

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

def start_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Start Flask immediately
flask_thread = threading.Thread(target=start_flask, daemon=True)
flask_thread.start()
print("✅ Flask server started")

# =========================
# DISCORD BOT
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    global bot_ready
    print(f'✅ {bot.user} ist online!')
    bot_ready = True

@bot.command()
async def ping(ctx):
    await ctx.send('pong 🏓')

# =========================
# START
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
