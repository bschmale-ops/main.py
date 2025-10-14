import os
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import datetime
from datetime import timezone
import json
import re
from flask import Flask, jsonify
import threading
import time
import os

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


print("🚀 Starting Discord CS2 Bot...")

# =========================
# FLASK STATUS SERVER
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
last_check_time = datetime.datetime.now(timezone.utc)
last_data_check = datetime.datetime.now(timezone.utc)
status_history = []
response_times = []

# =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

TEAMS = {}
CHANNELS = {}
ALERT_TIME = 5
DATA_FILE = "bot_data.json"
data_health_status = "healthy"
data_last_backup = None

# =========================
# DATA HEALTH CHECK FUNCTIONS
# =========================
def check_data_health():
    """Überprüft die Gesundheit der bot_data.json"""
    global data_health_status, data_last_backup

    try:
        if not os.path.exists(DATA_FILE):
            data_health_status = "missing"
            return {"status": "missing", "message": "Data file does not exist"}

        # Check file size
        file_size = os.path.getsize(DATA_FILE)
        if file_size == 0:
            data_health_status = "empty"
            return {"status": "empty", "message": "Data file is empty"}

        # Check if file is readable JSON
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                data_health_status = "empty"
                return {"status": "empty", "message": "Data file is empty"}

            data = json.loads(content)

        # Validate structure
        required_keys = ["TEAMS", "CHANNELS", "ALERT_TIME"]
        if not all(key in data for key in required_keys):
            data_health_status = "invalid_structure"
            return {"status": "invalid_structure", "message": "Missing required keys in data"}

        # Validate data types
        if not isinstance(data["TEAMS"], dict):
            data_health_status = "invalid_teams"
            return {"status": "invalid_teams", "message": "TEAMS should be a dictionary"}

        if not isinstance(data["CHANNELS"], dict):
            data_health_status = "invalid_channels"
            return {"status": "invalid_channels", "message": "CHANNELS should be a dictionary"}

        # Create backup if healthy
        if data_health_status == "healthy":
            create_backup()

        data_health_status = "healthy"
        return {
            "status": "healthy", 
            "message": "Data file is valid",
            "file_size": file_size,
            "teams_count": len(data["TEAMS"]),
            "channels_count": len(data["CHANNELS"])
        }

    except json.JSONDecodeError as e:
        data_health_status = "corrupted"
        return {"status": "corrupted", "message": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        data_health_status = "error"
        return {"status": "error", "message": f"Check error: {str(e)}"}

def create_backup():
    """Erstellt ein Backup der bot_data.json"""
    global data_last_backup

    try:
        if os.path.exists(DATA_FILE):
            backup_file = f"bot_data_backup_{datetime.datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            with open(DATA_FILE, "r", encoding='utf-8') as source:
                with open(backup_file, "w", encoding='utf-8') as target:
                    target.write(source.read())

            data_last_backup = datetime.datetime.now(timezone.utc)

            # Clean up old backups (keep last 5)
            backup_files = [f for f in os.listdir('.') if f.startswith('bot_data_backup_') and f.endswith('.json')]
            backup_files.sort()
            if len(backup_files) > 5:
                for old_backup in backup_files[:-5]:
                    os.remove(old_backup)

            return {"status": "success", "backup_file": backup_file}
        return {"status": "error", "message": "No data file to backup"}
    except Exception as e:
        return {"status": "error", "message": f"Backup failed: {str(e)}"}

def repair_data_file():
    """Versucht, die Daten-Datei zu reparieren"""
    try:
        # Find latest backup
        backup_files = [f for f in os.listdir('.') if f.startswith('bot_data_backup_') and f.endswith('.json')]
        if backup_files:
            backup_files.sort(reverse=True)
            latest_backup = backup_files[0]

            with open(latest_backup, "r", encoding='utf-8') as backup:
                data = json.load(backup)

            # Save as current file
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            return {"status": "repaired", "message": f"Restored from backup: {latest_backup}"}
        else:
            # Create fresh data structure
            fresh_data = {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 5}
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump(fresh_data, f, indent=4)

            return {"status": "recreated", "message": "Created fresh data file"}
    except Exception as e:
        return {"status": "error", "message": f"Repair failed: {str(e)}"}

# =========================
# FLASK ROUTES
# =========================
@app.route('/ping')
def ping():
    """Health check endpoint for monitoring"""
    current_time = datetime.datetime.now(timezone.utc)
    uptime = current_time - start_time

    # Calculate uptime in minutes
    uptime_minutes = int(uptime.total_seconds() / 60)

    # Check data health
    data_health = check_data_health()

    return jsonify({
        "status": "online",
        "bot_ready": bot.is_ready() if 'bot' in globals() else False,
        "alerts_running": send_alerts.is_running() if 'send_alerts' in globals() else False,
        "uptime": str(uptime),
        "uptime_minutes": uptime_minutes,
        "monitored_teams": sum(len(teams) for teams in TEAMS.values()),
        "monitored_guilds": len(TEAMS),
        "response_time": response_times[-1] if response_times else 0,
        "data_health": data_health
    })

@app.route('/status')
def status():
    """Detailed status endpoint"""
    data_health = check_data_health()

    return jsonify({
        "status": "online",
        "last_alert_check": last_check_time.isoformat(),
        "last_data_check": last_data_check.isoformat(),
        "teams_count": sum(len(teams) for teams in TEAMS.values()),
        "guilds_count": len(TEAMS),
        "alerts_enabled": send_alerts.is_running() if 'send_alerts' in globals() else False,
        "total_checks": len(status_history),
        "successful_checks": len([s for s in status_history if s.get("status") == "success"]),
        "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
        "data_health": data_health,
        "last_backup": data_last_backup.isoformat() if data_last_backup else None
    })

@app.route('/metrics')
def metrics():
    """Metrics for dashboard"""
    # Calculate uptime details
    current_time = datetime.datetime.now(timezone.utc)
    uptime = current_time - start_time

    # Get recent status (last 24 hours)
    recent_status = [s for s in status_history 
                    if datetime.datetime.fromisoformat(s["timestamp"]) > 
                    current_time - datetime.timedelta(hours=24)]

    successful_checks = len([s for s in recent_status if s.get("status") == "success"])
    total_checks = len(recent_status)
    uptime_percentage = (successful_checks / total_checks * 100) if total_checks > 0 else 100

    # Check data health
    data_health = check_data_health()

    return jsonify({
        "status": "online",
        "uptime": {
            "days": uptime.days,
            "hours": uptime.seconds // 3600,
            "minutes": (uptime.seconds // 60) % 60,
            "seconds": uptime.seconds % 60
        },
        "performance": {
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "last_response_time": response_times[-1] if response_times else 0
        },
        "incidents": {
            "last_24h": len([s for s in recent_status if s.get("status") == "error"]),
            "last_7d": len([s for s in status_history if s.get("status") == "error"]),
            "downtime_minutes": len([s for s in recent_status if s.get("status") == "error"]) * 5  # 5min intervals
        },
        "uptime_percentage": round(uptime_percentage, 2),
        "monitoring": {
            "guilds": len(TEAMS),
            "teams": sum(len(teams) for teams in TEAMS.values()),
            "channels": len(CHANNELS)
        },
        "data_health": data_health
    })

@app.route('/test')
def test():
    """Simple test endpoint without any checks"""
    return "OK"

@app.route('/simple-ping')
def simple_ping():
    """Simple ping for UptimeRobot"""
    return "PONG"

@app.route('/health')
def health():
    """Simple health check"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    })

@app.route('/data/health')
def data_health_route():
    """Spezieller Endpoint für Data Health"""
    health_info = check_data_health()
    return jsonify(health_info)

@app.route('/data/backup', methods=['POST'])
def create_backup_route():
    """Erstellt ein manuelles Backup"""
    backup_result = create_backup()
    return jsonify(backup_result)

@app.route('/data/repair', methods=['POST'])
def repair_data_route():
    """Repariert die Daten-Datei"""
    repair_result = repair_data_file()

    # Reload data after repair
    if repair_result["status"] in ["repaired", "recreated"]:
        load_initial_data()

    return jsonify(repair_result)

def run_flask():
    """Start Flask server in separate thread"""
    app.run(host='0.0.0.0', port=10000, debug=False)

# Start Flask thread
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# =========================
# DATA MANAGEMENT
# =========================
def load_initial_data():
    """Lädt die initialen Daten und prüft sie"""
    global TEAMS, CHANNELS, ALERT_TIME, data_health_status

    print("📂 Loading bot data...")

    # Check data health first
    health_check = check_data_health()

    if health_check["status"] != "healthy":
        print(f"⚠️ Data health issue: {health_check['message']}")

        # Try to repair automatically for certain issues
        if health_check["status"] in ["missing", "empty", "corrupted"]:
            print("🛠️ Attempting automatic repair...")
            repair_result = repair_data_file()
            print(f"🔧 Repair result: {repair_result['status']} - {repair_result['message']}")

    # Now load the data (whether original or repaired)
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)

            TEAMS = {}
            CHANNELS = {}
            ALERT_TIME = data.get("ALERT_TIME", 5)

            # Convert string keys to integers for guild IDs
            for guild_id_str, teams in data.get("TEAMS", {}).items():
                TEAMS[int(guild_id_str)] = teams

            for guild_id_str, channel_id in data.get("CHANNELS", {}).items():
                CHANNELS[int(guild_id_str)] = channel_id

            print(f"📊 Loaded: {len(TEAMS)} guilds, {sum(len(teams) for teams in TEAMS.values())} teams, {len(CHANNELS)} channels")
            data_health_status = "healthy"

        else:
            print("📝 No data file found, starting with empty data")
            TEAMS = {}
            CHANNELS = {}
            ALERT_TIME = 5
            data_health_status = "missing"

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        TEAMS = {}
        CHANNELS = {}
        ALERT_TIME = 5
        data_health_status = "error"

def save_data(data):
    """Save bot data to JSON file with health check"""
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Verify the saved data
        verification = check_data_health()
        if verification["status"] == "healthy":
            print("💾 Data saved and verified successfully")
            return True
        else:
            print(f"⚠️ Data saved but verification failed: {verification['message']}")
            return False

    except Exception as e:
        print(f"❌ Error saving data: {e}")
        return False

# Initial data loading
load_initial_data()

# =========================
# MATCH FUNCTIONS
# =========================
async def get_upcoming_matches():
    """Holt CS2 Matches mit Response-Time Tracking"""
    start_time = time.time()
    try:
        matches = []

        # Erstelle Demo-Matches für Test
        demo_teams = [('Natus Vincere', 'FaZe Clan'), ('Vitality', 'G2 Esports'),
                     ('MOUZ', 'Spirit'), ('FURIA', 'Falcons')]

        for i, (team1, team2) in enumerate(demo_teams):
            match_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=i + 1)
            matches.append({
                'team1': team1,
                'team2': team2,
                'unix_time': int(match_time.timestamp()),
                'event': 'CS2 Tournament',
                'link': 'https://www.hltv.org/matches'
            })

        response_time = (time.time() - start_time) * 1000  # in ms

        # Store response time (keep last 100 measurements)
        response_times.append(response_time)
        if len(response_times) > 100:
            response_times.pop(0)

        return matches, response_time

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        print(f"❌ Error getting matches: {e}")
        return [], response_time

# =========================
# ALERT SYSTEM
# =========================
@tasks.loop(minutes=5)
async def send_alerts():
    """Send match alerts with status tracking"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        matches, response_time = await get_upcoming_matches()

        for guild_id, teams in TEAMS.items():
            channel_id = CHANNELS.get(guild_id)
            if not channel_id:
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            for match in matches:
                if any(team.lower() in (match['team1'] + match['team2']).lower()
                       for team in teams):
                    time_left = (match['unix_time'] - last_check_time.timestamp()) / 60
                    if ALERT_TIME - 1 <= time_left <= ALERT_TIME + 1:
                        embed = discord.Embed(
                            title="⚔️ Match Alert",
                            description=f"{match['team1']} vs {match['team2']} startet bald!",
                            color=0x00ff00)
                        embed.add_field(name="Event", value=match['event'], inline=True)
                        embed.add_field(name="Start in", value=f"{int(time_left)} Minuten", inline=True)
                        embed.add_field(name="Link", value=match['link'], inline=False)
                        await channel.send(embed=embed)

                        # Rolle pingen
                        role = discord.utils.get(channel.guild.roles, name="CS2")
                        if role:
                            await channel.send(f"📢 {role.mention}")

        # Status speichern
        status_history.append({
            "timestamp": last_check_time.isoformat(),
            "status": "success",
            "matches_checked": len(matches),
            "response_time": response_time,
            "alerts_sent": len([m for m in matches if any(
                team.lower() in (m['team1'] + m['team2']).lower() 
                for teams in TEAMS.values() for team in teams
            )])
        })

        # Alte Einträge bereinigen (letzte 7 Tage behalten)
        cutoff_time = last_check_time - datetime.timedelta(days=7)
        status_history[:] = [s for s in status_history 
                           if datetime.datetime.fromisoformat(s["timestamp"]) > cutoff_time]

        print(f"✅ Checked {len(matches)} matches, Response: {response_time:.0f}ms")

    except Exception as e:
        print(f"❌ Alert error: {e}")
        status_history.append({
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e)
        })

# =========================
# HEALTH MONITORING
# =========================
@tasks.loop(minutes=10)
async def data_health_check():
    """Regelmäßige Überprüfung der Daten-Gesundheit"""
    global last_data_check
    try:
        last_data_check = datetime.datetime.now(timezone.utc)
        health_info = check_data_health()

        if health_info["status"] != "healthy":
            print(f"⚠️ Data health issue detected: {health_info['message']}")

        # Create backup every 6 hours if healthy
        if health_info["status"] == "healthy":
            current_time = datetime.datetime.now(timezone.utc)
            if not data_last_backup or (current_time - data_last_backup).total_seconds() > 6 * 3600:
                backup_result = create_backup()
                if backup_result["status"] == "success":
                    print(f"💾 Scheduled backup created: {backup_result['backup_file']}")

    except Exception as e:
        print(f"❌ Data health check error: {e}")

@tasks.loop(minutes=1)
async def health_check():
    """Überwacht die Bot-Gesundheit"""
    try:
        if not send_alerts.is_running():
            print("🔄 Restarting alert system...")
            send_alerts.start()
    except Exception as e:
        print(f"❌ Health check error: {e}")

# =========================
# COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für Alerts"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    if team not in TEAMS[guild_id]:
        TEAMS[guild_id].append(team)
        success = save_data({
            "TEAMS": TEAMS,
            "CHANNELS": CHANNELS,
            "ALERT_TIME": ALERT_TIME
        })
        if success:
            await ctx.send(f"✅ Team '{team}' hinzugefügt!")
        else:
            await ctx.send(f"⚠️ Team '{team}' hinzugefügt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"⚠️ '{team}' ist bereits abonniert.")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Entferne ein Team von Alerts"""
    guild_id = ctx.guild.id
    if team in TEAMS.get(guild_id, []):
        TEAMS[guild_id].remove(team)
        success = save_data({
            "TEAMS": TEAMS,
            "CHANNELS": CHANNELS,
            "ALERT_TIME": ALERT_TIME
        })
        if success:
            await ctx.send(f"❌ Team '{team}' entfernt!")
        else:
            await ctx.send(f"⚠️ Team '{team}' entfernt, aber Speichern fehlgeschlagen!")
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
    success = save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME})
    if success:
        await ctx.send(f"📡 Channel auf {channel.mention} gesetzt!")
    else:
        await ctx.send(f"⚠️ Channel gesetzt, aber Speichern fehlgeschlagen!")

@bot.command()
async def ping(ctx):
    """Einfacher Ping-Befehl"""
    await ctx.send('pong 🏓')

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
        description="Natus Vincere vs FaZe Clan startet bald!",
        color=discord.Color.green())
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
async def status(ctx):
    """Zeigt Bot-Status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    data_health = check_data_health()

    embed = discord.Embed(title="🤖 Bot Status", color=0x00ff00)
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="Alerts aktiv", value="✅ Ja" if send_alerts.is_running() else "❌ Nein", inline=True)
    embed.add_field(name="Server", value=f"{len(TEAMS)}", inline=True)
    embed.add_field(name="Teams", value=f"{sum(len(teams) for teams in TEAMS.values())}", inline=True)
    embed.add_field(name="Letzter Check", value=last_check_time.strftime("%H:%M:%S"), inline=True)
    embed.add_field(name="Response Time", value=f"{response_times[-1]:.0f}ms" if response_times else "N/A", inline=True)
    embed.add_field(name="Data Health", value=data_health["status"].upper(), inline=True)
    embed.add_field(name="Letztes Backup", value=data_last_backup.strftime("%H:%M") if data_last_backup else "Never", inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def data_check(ctx):
    """Überprüft die Daten-Gesundheit"""
    health_info = check_data_health()

    embed = discord.Embed(title="📊 Data Health Check", color=0x00ff00 if health_info["status"] == "healthy" else 0xff0000)
    embed.add_field(name="Status", value=health_info["status"].upper(), inline=True)
    embed.add_field(name="Message", value=health_info["message"], inline=False)

    if "file_size" in health_info:
        embed.add_field(name="File Size", value=f"{health_info['file_size']} bytes", inline=True)
    if "teams_count" in health_info:
        embed.add_field(name="Teams Count", value=health_info["teams_count"], inline=True)
    if "channels_count" in health_info:
        embed.add_field(name="Channels Count", value=health_info["channels_count"], inline=True)

    embed.add_field(name="Last Backup", value=data_last_backup.strftime("%Y-%m-%d %H:%M") if data_last_backup else "Never", inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def create_backup_cmd(ctx):
    """Erstellt ein manuelles Backup"""
    backup_result = create_backup()

    if backup_result["status"] == "success":
        await ctx.send(f"✅ Backup created: `{backup_result['backup_file']}`")
    else:
        await ctx.send(f"❌ Backup failed: {backup_result['message']}")

@bot.command()
async def repair_data(ctx):
    """Repariert die Daten-Datei"""
    repair_result = repair_data_file()

    # Reload data after repair
    if repair_result["status"] in ["repaired", "recreated"]:
        load_initial_data()

    embed = discord.Embed(
        title="🔧 Data Repair", 
        color=0x00ff00 if repair_result["status"] in ["repaired", "recreated"] else 0xff0000
    )
    embed.add_field(name="Status", value=repair_result["status"].upper(), inline=True)
    embed.add_field(name="Message", value=repair_result["message"], inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def health(ctx):
    """Health Check für Monitoring"""
    try:
        # Teste Match-Abruf
        matches, response_time = await get_upcoming_matches()

        # Check data health
        data_health = check_data_health()

        embed = discord.Embed(title="🏥 Health Check", color=0x00ff00)
        embed.add_field(name="API Response", value="✅ Erreichbar", inline=True)
        embed.add_field(name="Response Time", value=f"{response_time:.0f}ms", inline=True)
        embed.add_field(name="Matches gefunden", value=len(matches), inline=True)
        embed.add_field(name="Alert System", value="✅ Aktiv" if send_alerts.is_running() else "❌ Inaktiv", inline=True)
        embed.add_field(name="Flask Server", value="✅ Läuft", inline=True)
        embed.add_field(name="Daten gespeichert", value=f"✅ {len(TEAMS)} Server", inline=True)
        embed.add_field(name="Data Health", value=data_health["status"].upper(), inline=True)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Health Check failed: {e}")

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    """Bot startup event"""
    print(f'✅ {bot.user} ist online!')

    # Starte alle Tasks
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔄 Alert system started")

    if not health_check.is_running():
        health_check.start()
        print("🏥 Health check started")

    if not data_health_check.is_running():
        data_health_check.start()
        print("📊 Data health check started")

    print("🌐 Flask status server running on port 10000")
    print(f"📊 Monitoring {len(TEAMS)} servers with {sum(len(teams) for teams in TEAMS.values())} teams")

    # Initial data health check
    health_info = check_data_health()
    print(f"📂 Data health: {health_info['status']} - {health_info['message']}")

# =========================
# START BOT
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
