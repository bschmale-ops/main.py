import os
import discord
from discord.ext import commands, tasks
import datetime
from datetime import timezone
import json
import asyncio
from flask import Flask, jsonify

print("🚀 Starting Discord CS2 Bot...")

# =========================
# FLASK APP - ZUERST STARTEN
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Discord CS2 Bot is ONLINE"

@app.route('/ping')
def ping():
    return jsonify({
        "status": "online",
        "message": "Bot is running",
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    })

@app.route('/test')
def test():
    return "OK"

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/status')
def status():
    return jsonify({
        "status": "online", 
        "bot_ready": False
    })

# Flask sofort starten
def start_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Flask in separatem Thread starten
import threading
flask_thread = threading.Thread(target=start_flask, daemon=True)
flask_thread.start()
print("✅ Flask server started")

# =========================
# DISCORD BOT
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

TEAMS = {}
CHANNELS = {}
ALERT_TIME = 5

@bot.event
async def on_ready():
    print(f'✅ {bot.user} ist online!')
    
    # Update status route
    @app.route('/status')
    def status():
        return jsonify({
            "status": "online",
            "bot_ready": True,
            "teams_count": sum(len(teams) for teams in TEAMS.values()),
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        })
    
    print("🤖 Bot ready and routes updated")

@bot.command()
async def ping(ctx):
    await ctx.send('pong 🏓')

@bot.command()
async def status(ctx):
    await ctx.send('🤖 Bot läuft!')

# =========================
# START BOT
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
