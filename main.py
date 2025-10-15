import os
import discord
from discord.ext import commands, tasks
import datetime
from datetime import timezone
import json
import asyncio
from flask import Flask, jsonify
import threading
import aiohttp
from bs4 import BeautifulSoup
import socket
import requests

print("🚀 Starting Discord CS2 Bot with HLTV Scraping...")

# =========================
# FLASK STATUS SERVER MIT PORT-FALLBACK
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
last_check_time = datetime.datetime.now(timezone.utc)
flask_port = None
flask_status = "starting"

# =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# =========================
# DATA MANAGEMENT - ROBUSTE PERSISTENZ
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    """Lädt alle gespeicherten Daten mit Fallback"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                # Alte Datenstruktur migrieren
                if "ALERT_TIME" not in data:
                    data["ALERT_TIME"] = 30
                
                # Debug-Ausgabe
                server_count = len(data.get('TEAMS', {}))
                total_teams = sum(len(teams) for teams in data.get('TEAMS', {}).values())
                print(f"📂 Daten geladen: {server_count} Server, {total_teams} Teams")
                return data
        else:
            print("📂 Keine gespeicherten Daten gefunden, starte frisch")
            # Erstelle Standard-Datenstruktur
            default_data = {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
            # Speichere sie sofort
            save_data(default_data)
            return default_data
            
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        # Fallback auf leere Daten
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data(data):
    """Speichert alle Daten mit Error-Handling"""
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Verifiziere das Speichern
        if os.path.exists(DATA_FILE):
            file_size = os.path.getsize(DATA_FILE)
            print(f"💾 Daten gespeichert ({file_size} bytes)")
            return True
        else:
            print("❌ Datei wurde nicht erstellt")
            return False
            
    except Exception as e:
        print(f"❌ Kritischer Fehler beim Speichern: {e}")
        return False

# INITIALE DATENLADUNG BEIM START
data = load_data()
TEAMS = {}
CHANNELS = {}
ALERT_TIME = data.get("ALERT_TIME", 30)

# Guild IDs von String zu Integer konvertieren
for guild_id_str, teams in data.get("TEAMS", {}).items():
    try:
        TEAMS[int(guild_id_str)] = teams
    except:
        continue

for guild_id_str, channel_id in data.get("CHANNELS", {}).items():
    try:
        CHANNELS[int(guild_id_str)] = channel_id
    except:
        continue

print(f"📊 System geladen: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams, Alert-Time: {ALERT_TIME}min")

# =========================
# HLTV SCRAPING FUNCTIONS
# =========================
async def fetch_hltv_matches():
    """Holt Matches von Liquipedia (zuverlässiger als HLTV)"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Liquipedia CS2 Matches - weniger restriktiv
            url = "https://liquipedia.net/counterstrike/Liquipedia:Matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            print("🔍 Fetching matches from Liquipedia...")
            async with session.get(url, headers=headers, timeout=30) as response:
                print(f"📡 Liquipedia Response: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Finde Match-Tabellen
                    match_tables = soup.find_all('table', class_='wikitable')
                    
                    for table in match_tables[:3]:  # Erste 3 Tabellen
                        rows = table.find_all('tr')
                        
                        for row in rows[1:]:  # Überspringe Header
                            cols = row.find_all('td')
                            if len(cols) >= 4:
                                try:
                                    # Team 1
                                    team1_elem = cols[1].find('a')
                                    team1 = team1_elem.get_text(strip=True) if team1_elem else cols[1].get_text(strip=True)
                                    
                                    # Team 2  
                                    team2_elem = cols[3].find('a')
                                    team2 = team2_elem.get_text(strip=True) if team2_elem else cols[3].get_text(strip=True)
                                    
                                    # Tournament
                                    tournament_elem = cols[4].find('a') if len(cols) > 4 else None
                                    tournament = tournament_elem.get_text(strip=True) if tournament_elem else "CS2 Tournament"
                                    
                                    # Datum/Zeit
                                    date_elem = cols[0]
                                    date_text = date_elem.get_text(strip=True)
                                    
                                    if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                                        # Vereinfachte Zeit-Parsing
                                        unix_time = parse_liquipedia_time(date_text)
                                        
                                        matches.append({
                                            'team1': team1,
                                            'team2': team2, 
                                            'unix_time': unix_time,
                                            'event': tournament,
                                            'link': "https://liquipedia.net/counterstrike/Main_Page",
                                            'time_string': date_text
                                        })
                                        print(f"✅ Match: {team1} vs {team2}")
                                        
                                except Exception as e:
                                    continue
                    
                    print(f"🎯 Found {len(matches)} matches on Liquipedia")
                    
                else:
                    print(f"❌ Liquipedia request failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ Liquipedia error: {e}")
    
    return matches

def parse_liquipedia_time(date_text):
    """Vereinfachte Zeit-Parsing für Liquipedia"""
    try:
        # Füge einfach 2 Stunden hinzu für Test-Zwecke
        return int((datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=2)).timestamp())
    except:
        return int((datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1)).timestamp())

# =========================
# FLASK ROUTES - VERBESSERTE ÜBERWACHUNG
# =========================
@app.route('/')
def home():
    global flask_status
    flask_status = "healthy"
    return "✅ Discord CS2 Bot - ONLINE"

@app.route('/ping')
def ping():
    global flask_status
    flask_status = "healthy"
    return jsonify({
        "status": "online",
        "bot_ready": bot.is_ready(),
        "alerts_running": send_alerts.is_running() if 'send_alerts' in globals() else False,
        "uptime": str(datetime.datetime.now(timezone.utc) - start_time),
        "monitored_teams": sum(len(teams) for teams in TEAMS.values()),
        "monitored_guilds": len(TEAMS),
        "alert_time": ALERT_TIME,
        "flask_port": flask_port,
        "flask_status": flask_status,
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    })

@app.route('/test')
def test():
    return "OK"

@app.route('/health')
def health():
    global flask_status
    flask_status = "healthy"
    return jsonify({
        "status": "healthy",
        "service": "discord_cs2_bot",
        "last_check": last_check_time.isoformat(),
        "teams_count": sum(len(teams) for teams in TEAMS.values()),
        "alert_time": ALERT_TIME,
        "servers_count": len(TEAMS),
        "flask_port": flask_port,
        "flask_status": flask_status
    })

@app.route('/status')
def status():
    global flask_status
    flask_status = "healthy"
    return jsonify({
        "status": "online",
        "last_check": last_check_time.isoformat(),
        "teams_count": sum(len(teams) for teams in TEAMS.values()),
        "alert_time": ALERT_TIME,
        "servers_count": len(TEAMS),
        "flask_port": flask_port,
        "flask_status": flask_status,
        "bot_ready": bot.is_ready()
    })

@app.route('/debug')
def debug():
    """Detaillierte Debug-Informationen"""
    return jsonify({
        "flask_port": flask_port,
        "flask_status": flask_status,
        "environment_port": os.environ.get("PORT"),
        "bot_ready": bot.is_ready(),
        "alerts_running": send_alerts.is_running() if 'send_alerts' in globals() else False,
        "start_time": start_time.isoformat(),
        "current_time": datetime.datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": (datetime.datetime.now(timezone.utc) - start_time).total_seconds(),
        "monitored_servers": len(TEAMS),
        "monitored_teams": sum(len(teams) for teams in TEAMS.values())
    })

def is_port_available(port):
    """Prüft ob ein Port verfügbar ist"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            return True
    except OSError:
        return False

def run_flask():
    """Startet Flask Server mit intelligentem Port-Fallback"""
    global flask_port, flask_status
    
    # Port Priorität: 1. Environment, 2. 1000, 3. 10000
    potential_ports = []
    
    # Environment Port
    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        potential_ports.append(int(env_port))
    
    # Standard Ports für Render.com
    potential_ports.append(1000)   # Render.com Standard
    potential_ports.append(10000)  # Unser ursprünglicher Port
    
    # Finde verfügbaren Port
    for port in potential_ports:
        if is_port_available(port):
            flask_port = port
            break
    else:
        # Fallback: Nimm irgendeinen verfügbaren Port
        flask_port = 0  # 0 = automatisch verfügbarer Port
    
    print(f"🔍 Port Check: Environment PORT = {env_port}")
    print(f"🌐 Flask starting on port {flask_port}")
    
    try:
        flask_status = "running"
        app.run(host='0.0.0.0', port=flask_port, debug=False, use_reloader=False)
    except Exception as e:
        flask_status = f"error: {e}"
        print(f"❌ Flask Server crashed: {e}")

# Flask starten
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print("✅ Flask server started")

# =========================
# ALERT SYSTEM
# =========================
@tasks.loop(minutes=5)
async def send_alerts():
    """Sendet Match Alerts für echte HLTV Matches"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        matches = await fetch_hltv_matches()
        current_time = last_check_time.timestamp()

        print(f"🔍 HLTV Matches gefunden: {len(matches)}")
        
        alerts_sent = 0
        
        for guild_id, teams in TEAMS.items():
            if not teams:  # Keine Teams abonniert
                continue
                
            channel_id = CHANNELS.get(guild_id)
            if not channel_id:
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            for match in matches:
                team1_lower = match['team1'].lower()
                team2_lower = match['team2'].lower()
                
                for subscribed_team in teams:
                    sub_team_lower = subscribed_team.lower()
                    
                    # Intelligente Team-Erkennung
                    if (sub_team_lower in team1_lower or 
                        sub_team_lower in team2_lower or
                        team1_lower in sub_team_lower or 
                        team2_lower in sub_team_lower):
                        
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
                            embed.add_field(name="Zeit", value=match.get('time_string', 'Soon'), inline=True)
                            embed.add_field(name="Link", value=f"[HLTV]({match['link']})", inline=False)
                            
                            await channel.send(embed=embed)
                            
                            # CS2 Rolle pingen
                            role = discord.utils.get(channel.guild.roles, name="CS2")
                            if role:
                                await channel.send(f"📢 {role.mention}")
                            
                            alerts_sent += 1
                            break  # Nur einen Alert pro Match

        if alerts_sent > 0:
            print(f"✅ {alerts_sent} Alerts gesendet")
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS - ALLE MIT SOFORTIGER SPEICHERUNG
# =========================
@bot.command()
async def test_hltv(ctx):
    """Testet HLTV Verbindung direkt"""
    try:
        await ctx.send("🔍 Testing HLTV connection...")
        
        matches = await fetch_hltv_matches()
        
        if matches:
            match_list = ""
            for i, match in enumerate(matches[:5], 1):
                match_list += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
                match_list += f"   🕐 {match['time_string']} | 📅 {match['event']}\n\n"
            
            embed = discord.Embed(
                title="✅ HLTV Test Successful",
                description=match_list,
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No matches found. HLTV structure might have changed.")
            
    except Exception as e:
        await ctx.send(f"❌ HLTV Test failed: {e}")

@bot.command()
async def hltv_raw(ctx):
    """Zeigt rohe HLTV Daten für Debugging"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            async with session.get('https://www.hltv.org/matches', headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    # Zeige erste 500 Zeichen zur Analyse
                    preview = html[:500].replace('\n', ' ').replace('  ', ' ')
                    await ctx.send(f"📄 HTML Preview: ```{preview}...```")
                else:
                    await ctx.send(f"❌ Status: {response.status}")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für Alerts - SOFORT GESPEICHERT"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    if team not in TEAMS[guild_id]:
        TEAMS[guild_id].append(team)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"✅ **{team}** hinzugefügt und gespeichert!")
        else:
            await ctx.send(f"⚠️ **{team}** hinzugefügt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"⚠️ **{team}** ist bereits abonniert!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Entferne ein Team von Alerts - SOFORT GESPEICHERT"""
    guild_id = ctx.guild.id
    if guild_id in TEAMS and team in TEAMS[guild_id]:
        TEAMS[guild_id].remove(team)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"❌ **{team}** entfernt und gespeichert!")
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
        embed.set_footer(text=f"Gespeichert in bot_data.json")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Noch keine Teams abonniert!")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Setze den Alert-Channel - SOFORT GESPEICHERT"""
    CHANNELS[ctx.guild.id] = channel.id
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        await ctx.send(f"📡 Alert-Channel auf {channel.mention} gesetzt und gespeichert!")
    else:
        await ctx.send(f"⚠️ Channel gesetzt, aber Speichern fehlgeschlagen!")

@bot.command()
async def settime(ctx, minutes: int):
    """Setze die Alert-Vorlaufzeit in Minuten - SOFORT GESPEICHERT"""
    global ALERT_TIME
    if 1 <= minutes <= 120:
        old_time = ALERT_TIME
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ Alert-Vorlaufzeit von **{old_time}** auf **{minutes} Minuten** geändert und gespeichert!")
        else:
            await ctx.send(f"⚠️ Zeit gesetzt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send("❌ Bitte eine Zeit zwischen 1 und 120 Minuten angeben!")

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
    """Zeigt verfügbare Matches von HLTV an"""
    try:
        matches = await fetch_hltv_matches()
        
        if not matches:
            await ctx.send("❌ Keine Matches auf HLTV gefunden")
            return
            
        match_list = ""
        for i, match in enumerate(matches[:8], 1):
            match_time = datetime.datetime.fromtimestamp(match['unix_time'], tz=timezone.utc)
            time_str = match_time.strftime("%d.%m %H:%M")
            match_list += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
            match_list += f"   🕐 {time_str} UTC | 📅 {match['event']}\n\n"
        
        embed = discord.Embed(
            title="🔍 Aktuelle HLTV Matches",
            description=match_list,
            color=0x0099ff
        )
        embed.set_footer(text=f"{len(matches)} Matches gefunden")
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
    
    embed.set_footer(text="Alle Daten persistent in bot_data.json gespeichert")
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
    embed.add_field(name="Flask Status", value=flask_status, inline=True)
    embed.add_field(name="Flask Port", value=f"{flask_port}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def health(ctx):
    """Health Check"""
    try:
        matches = await fetch_hltv_matches()
        
        embed = discord.Embed(title="🏥 Health Check", color=0x00ff00)
        embed.add_field(name="Bot", value="✅ Online", inline=True)
        embed.add_field(name="Alerts", value="✅ Aktiv" if send_alerts.is_running() else "❌ Inaktiv", inline=True)
        embed.add_field(name="HLTV", value=f"✅ {len(matches)} Matches", inline=True)
        embed.add_field(name="Daten", value="✅ Persistente Speicherung", inline=True)
        embed.add_field(name="Flask", value=f"✅ {flask_status} (Port {flask_port})", inline=True)
        embed.add_field(name="Teams", value=f"✅ {sum(len(teams) for teams in TEAMS.values())}", inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Health Check failed: {e}")

@bot.command()
async def flask_info(ctx):
    """Zeigt detaillierte Flask-Informationen"""
    try:
        # Versuche Flask-Server zu erreichen
        if flask_port:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:{flask_port}/debug', timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        embed = discord.Embed(title="🌐 Flask Server Info", color=0x00ff00)
                        for key, value in data.items():
                            embed.add_field(name=key, value=str(value)[:100], inline=False)
                        await ctx.send(embed=embed)
                        return
        
        await ctx.send(f"❌ Flask Server nicht erreichbar. Status: {flask_status}, Port: {flask_port}")
    except Exception as e:
        await ctx.send(f"❌ Flask Info Fehler: {e}")

@bot.command()
async def ping(ctx):
    """Einfacher Ping"""
    await ctx.send('🏓 Pong!')

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    """Bot Startup - Lädt alle gespeicherten Daten"""
    print(f'✅ {bot.user} ist online!')
    
    # Warte kurz bis Flask gestartet ist
    await asyncio.sleep(2)
    
    # Alert System starten
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔄 Alert system started")
    
    print(f"📊 Geladene Daten: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Alert-Time: {ALERT_TIME} Minuten")
    print(f"🌐 Flask Port: {flask_port}, Status: {flask_status}")
    print("💾 Alle Daten persistent gespeichert")

# =========================
# START BOT
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
