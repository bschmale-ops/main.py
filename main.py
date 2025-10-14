import os
import discord
from discord.ext import commands, tasks
import datetime
from datetime import timezone
import json
import asyncio
from flask import Flask, jsonify
import threading
import time

print("🚀 Starting Discord CS2 Bot...")

# =========================
# FLASK STATUS SERVER
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
last_check_time = datetime.datetime.now(timezone.utc)

# =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# =========================
# DATA MANAGEMENT
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    """Lädt gespeicherte Daten"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                # Alte Datenstruktur migrieren
                if "ALERT_TIME" not in data:
                    data["ALERT_TIME"] = 5
                return data
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 5}
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 5}

def save_data(data):
    """Speichert Daten"""
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}")
        return False

# Initial Daten laden
data = load_data()
TEAMS = {}
CHANNELS = {}
ALERT_TIME = data.get("ALERT_TIME", 5)

# Guild IDs konvertieren
for guild_id_str, teams in data.get("TEAMS", {}).items():
    TEAMS[int(guild_id_str)] = teams

for guild_id_str, channel_id in data.get("CHANNELS", {}).items():
    CHANNELS[int(guild_id_str)] = channel_id

print(f"📊 Geladen: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams, Alert-Time: {ALERT_TIME}min")

# =========================
# FLASK ROUTES
# =========================
@app.route('/')
def home():
    return "✅ Discord CS2 Bot - ONLINE"

@app.route('/ping')
def ping():
    return jsonify({
        "status": "online",
        "bot_ready": bot.is_ready(),
        "alerts_running": send_alerts.is_running(),
        "uptime": str(datetime.datetime.now(timezone.utc) - start_time),
        "monitored_teams": sum(len(teams) for teams in TEAMS.values()),
        "monitored_guilds": len(TEAMS)
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
        "last_check": last_check_time.isoformat(),
        "teams_count": sum(len(teams) for teams in TEAMS.values()),
        "alert_time": ALERT_TIME
    })

def run_flask():
    """Startet Flask Server"""
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Flask starten
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print("✅ Flask server started")

# =========================
# MATCH FUNCTIONS
# =========================
async def get_upcoming_matches():
    """Holt CS2 Matches (Demo-Daten)"""
    try:
        matches = []

        # Demo-Matches für Test
        demo_teams = [
            ('Natus Vincere', 'FaZe Clan'),
            ('Vitality', 'G2 Esports'),
            ('MOUZ', 'Spirit'), 
            ('FURIA', 'Falcons'),
            ('Aurora', '3DMAX')
        ]

        for i, (team1, team2) in enumerate(demo_teams):
            match_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=i + 1)
            matches.append({
                'team1': team1,
                'team2': team2,
                'unix_time': int(match_time.timestamp()),
                'event': 'ESL Pro League',
                'link': 'https://www.hltv.org/matches'
            })

        return matches
        
    except Exception as e:
        print(f"❌ Error getting matches: {e}")
        return []

# =========================
# ALERT SYSTEM
# =========================
@tasks.loop(minutes=5)
async def send_alerts():
    """Sendet Match Alerts"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        matches = await get_upcoming_matches()
        current_time = last_check_time.timestamp()

        alerts_sent = 0
        
        for guild_id, teams in TEAMS.items():
            channel_id = CHANNELS.get(guild_id)
            if not channel_id:
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            for match in matches:
                match_teams = f"{match['team1']} {match['team2']}".lower()
                
                # Prüfe ob eines der abonnierten Teams im Match ist
                if any(team.lower() in match_teams for team in teams):
                    time_until_match = (match['unix_time'] - current_time) / 60  # Minuten
                    
                    # Alert wenn Match innerhalb der eingestellten Zeit startet
                    if 0 <= time_until_match <= ALERT_TIME:
                        embed = discord.Embed(
                            title="⚔️ CS2 Match Alert",
                            description=f"**{match['team1']}** vs **{match['team2']}**",
                            color=0x00ff00,
                            url=match['link']
                        )
                        embed.add_field(name="Event", value=match['event'], inline=True)
                        embed.add_field(name="Start in", value=f"{int(time_until_match)} Minuten", inline=True)
                        embed.add_field(name="Link", value=match['link'], inline=False)
                        
                        await channel.send(embed=embed)
                        
                        # CS2 Rolle pingen
                        role = discord.utils.get(channel.guild.roles, name="CS2")
                        if role:
                            await channel.send(f"📢 {role.mention}")
                        
                        alerts_sent += 1

        if alerts_sent > 0:
            print(f"✅ {alerts_sent} Alerts gesendet")
        else:
            print(f"🔍 {len(matches)} Matches geprüft, keine Alerts nötig")
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für Alerts"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    if team not in TEAMS[guild_id]:
        TEAMS[guild_id].append(team)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"✅ **{team}** hinzugefügt!")
        else:
            await ctx.send(f"⚠️ **{team}** hinzugefügt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"⚠️ **{team}** ist bereits abonniert!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Entferne ein Team von Alerts"""
    guild_id = ctx.guild.id
    if guild_id in TEAMS and team in TEAMS[guild_id]:
        TEAMS[guild_id].remove(team)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"❌ **{team}** entfernt!")
        else:
            await ctx.send(f"⚠️ **{team}** entfernt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send("❌ Team nicht gefunden!")

@bot.command()
async def list_teams(ctx):
    """Zeige alle abonnierten Teams"""
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    if teams:
        team_list = "\n".join([f"• **{team}**" for team in teams])
        embed = discord.Embed(
            title="📋 Abonnierte Teams",
            description=team_list,
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Noch keine Teams abonniert!")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Setze den Alert-Channel"""
    CHANNELS[ctx.guild.id] = channel.id
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        await ctx.send(f"📡 Alert-Channel auf {channel.mention} gesetzt!")
    else:
        await ctx.send(f"⚠️ Channel gesetzt, aber Speichern fehlgeschlagen!")

@bot.command()
async def settime(ctx, minutes: int):
    """Setze die Alert-Vorlaufzeit in Minuten"""
    global ALERT_TIME
    if 1 <= minutes <= 60:
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ Alert-Vorlaufzeit auf **{minutes} Minuten** gesetzt!")
        else:
            await ctx.send(f"⚠️ Zeit gesetzt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send("❌ Bitte eine Zeit zwischen 1 und 60 Minuten angeben!")

@bot.command()
async def test_alert(ctx):
    """Testet den Alert mit Ping"""
    channel_id = CHANNELS.get(ctx.guild.id)
    if not channel_id:
        await ctx.send("❌ Kein Alert-Channel gesetzt. Verwende `/setchannel`")
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Channel nicht gefunden")
        return

    # Test-Embed erstellen
    embed = discord.Embed(
        title="⚔️ TEST Match Alert",
        description="**Natus Vincere** vs **FaZe Clan**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Event", value="TEST Event", inline=True)
    embed.add_field(name="Start in", value="5 Minuten", inline=True)
    embed.add_field(name="Link", value="https://www.hltv.org/matches", inline=False)

    await channel.send(embed=embed)

    # Rolle pingen
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await channel.send(f"📢 {role.mention} **TEST ALERT**")

    await ctx.send("✅ Test-Alert gesendet!")

@bot.command()
async def debug_matches(ctx):
    """Zeigt verfügbare Matches an"""
    try:
        matches = await get_upcoming_matches()
        
        if not matches:
            await ctx.send("❌ Keine Matches verfügbar")
            return
            
        match_list = ""
        for i, match in enumerate(matches, 1):
            match_time = datetime.datetime.fromtimestamp(match['unix_time'], tz=timezone.utc)
            time_str = match_time.strftime("%H:%M")
            match_list += f"{i}. **{match['team1']}** vs **{match['team2']}** - {time_str} Uhr\n"
        
        embed = discord.Embed(
            title="🔍 Verfügbare Matches",
            description=match_list,
            color=0x0099ff
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Fehler: {e}")

@bot.command()
async def check_data(ctx):
    """Zeigt gespeicherte Daten an"""
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    channel_id = CHANNELS.get(guild_id)
    
    embed = discord.Embed(title="📊 Gespeicherte Daten", color=0x00ff00)
    embed.add_field(name="Teams", value=f"{len(teams)} Teams", inline=True)
    embed.add_field(name="Alert-Time", value=f"{ALERT_TIME} min", inline=True)
    embed.add_field(name="Channel", value=f"<#{channel_id}>" if channel_id else "Nicht gesetzt", inline=True)
    
    if teams:
        team_list = "\n".join([f"• {team}" for team in teams])
        embed.add_field(name="Abonnierte Teams", value=team_list, inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def status(ctx):
    """Zeigt Bot-Status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(title="🤖 Bot Status", color=0x00ff00)
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)
    embed.add_field(name="Alerts", value="✅ Aktiv" if send_alerts.is_running() else "❌ Inaktiv", inline=True)
    embed.add_field(name="Server", value=f"{len(TEAMS)}", inline=True)
    embed.add_field(name="Teams", value=f"{sum(len(teams) for teams in TEAMS.values())}", inline=True)
    embed.add_field(name="Alert-Time", value=f"{ALERT_TIME} min", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def health(ctx):
    """Health Check"""
    try:
        matches = await get_upcoming_matches()
        
        embed = discord.Embed(title="🏥 Health Check", color=0x00ff00)
        embed.add_field(name="Bot", value="✅ Online", inline=True)
        embed.add_field(name="Alerts", value="✅ Aktiv" if send_alerts.is_running() else "❌ Inaktiv", inline=True)
        embed.add_field(name="Matches", value=f"✅ {len(matches)} gefunden", inline=True)
        embed.add_field(name="Daten", value="✅ Geladen", inline=True)
        embed.add_field(name="Flask", value="✅ Läuft", inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Health Check failed: {e}")

@bot.command()
async def ping(ctx):
    """Einfacher Ping"""
    await ctx.send('🏓 Pong!')

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    """Bot Startup"""
    print(f'✅ {bot.user} ist online!')
    
    # Alert System starten
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔄 Alert system started")
    
    print(f"📊 Monitoring {len(TEAMS)} Server mit {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Alert-Time: {ALERT_TIME} Minuten")

# =========================
# START BOT
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
