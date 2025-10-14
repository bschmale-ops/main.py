import os
import discord
from discord.ext import commands
import datetime
from datetime import timezone
import json
from flask import Flask, jsonify
import threading

print("🚀 Starting Discord CS2 Bot...")

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

bot_ready = False
DATA_FILE = "bot_data.json"

# =========================
# DATEN MANAGEMENT
# =========================
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return {"TEAMS": {}, "CHANNELS": {}}
    except:
        return {"TEAMS": {}, "CHANNELS": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Daten laden
data = load_data()
TEAMS = data.get("TEAMS", {})
CHANNELS = data.get("CHANNELS", {})

# Guild IDs von String zu Integer konvertieren
TEAMS = {int(k): v for k, v in TEAMS.items()}
CHANNELS = {int(k): v for k, v in CHANNELS.items()}

print(f"📊 Geladene Daten: {len(TEAMS)} Server, {sum(len(t) for t in TEAMS.values())} Teams")

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

# =========================
# COMMANDS MIT DATENSPEICHERUNG
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für Alerts"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    if team not in TEAMS[guild_id]:
        TEAMS[guild_id].append(team)
        save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS})
        await ctx.send(f"✅ Team '{team}' hinzugefügt!")
    else:
        await ctx.send(f"⚠️ '{team}' ist bereits abonniert.")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Entferne ein Team von Alerts"""
    guild_id = ctx.guild.id
    if guild_id in TEAMS and team in TEAMS[guild_id]:
        TEAMS[guild_id].remove(team)
        save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS})
        await ctx.send(f"❌ Team '{team}' entfernt!")
    else:
        await ctx.send("Team nicht gefunden.")

@bot.command()
async def list_teams(ctx):
    """Zeige alle abonnierten Teams"""
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    if teams:
        team_list = "\n".join([f"✅ {team}" for team in teams])
        await ctx.send(f"**Abonnierte Teams:**\n{team_list}")
    else:
        await ctx.send("❌ Noch keine Teams abonniert.")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Setze den Alert-Channel"""
    CHANNELS[ctx.guild.id] = channel.id
    save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS})
    await ctx.send(f"📡 Channel auf {channel.mention} gesetzt!")

@bot.command()
async def ping(ctx):
    await ctx.send('pong 🏓')

@bot.command()
async def status(ctx):
    await ctx.send('🤖 Bot läuft!')

# =========================
# START
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
