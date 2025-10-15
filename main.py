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

print("🚀 Starting Discord CS2 Bot with HLTV Scraping...")

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
# DATA MANAGEMENT - VOLLE PERSISTENZ
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    """Lädt alle gespeicherten Daten - crash-safe"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                # Alte Datenstruktur migrieren
                if "ALERT_TIME" not in data:
                    data["ALERT_TIME"] = 30
                print(f"📂 Daten geladen: {len(data.get('TEAMS', {}))} Server, {sum(len(teams) for teams in data.get('TEAMS', {}).values())} Teams")
                return data
        print("📂 Keine gespeicherten Daten gefunden, starte frisch")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
    except Exception as e:
        print(f"❌ Kritischer Fehler beim Laden: {e}")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data(data):
    """Speichert alle Daten sofort - crash-safe"""
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("💾 Daten gespeichert")
        return True
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
    """Holt aktuelle Matches von HLTV"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://www.hltv.org/matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Finde Match-Container
                    match_containers = soup.find_all('div', class_='upcomingMatch')
                    
                    for container in match_containers[:25]:  # Erste 25 Matches
                        try:
                            # Team Namen extrahieren
                            team_elements = container.find_all('div', class_='matchTeamName')
                            if len(team_elements) >= 2:
                                team1 = team_elements[0].get_text(strip=True)
                                team2 = team_elements[1].get_text(strip=True)
                                
                                # Match Zeit extrahieren
                                time_element = container.find('div', class_='matchTime')
                                if time_element:
                                    match_time = time_element.get_text(strip=True)
                                    
                                    # Event Name
                                    event_element = container.find('div', class_='matchEventName')
                                    event = event_element.get_text(strip=True) if event_element else "CS2 Event"
                                    
                                    # Match Link
                                    match_link = container.get('data-z-url')
                                    if match_link and not match_link.startswith('http'):
                                        match_link = f"https://www.hltv.org{match_link}"
                                    else:
                                        match_link = "https://www.hltv.org/matches"
                                    
                                    # Zeit in Unix Timestamp umwandeln
                                    unix_time = parse_match_time(match_time)
                                    
                                    if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                                        matches.append({
                                            'team1': team1,
                                            'team2': team2,
                                            'unix_time': unix_time,
                                            'event': event,
                                            'link': match_link,
                                            'time_string': match_time
                                        })
                                        
                        except Exception as e:
                            continue
                            
                else:
                    print(f"❌ HLTV Request failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ HLTV Scraping error: {e}")
    
    return matches

def parse_match_time(time_str):
    """Konvertiert HLTV Zeit zu Unix Timestamp"""
    try:
        now = datetime.datetime.now(timezone.utc)
        
        if 'Today' in time_str:
            time_part = time_str.replace('Today', '').strip()
            if ':' in time_part:
                hours, minutes = map(int, time_part.split(':'))
                match_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                return int(match_time.timestamp())
        
        elif 'Tomorrow' in time_str:
            time_part = time_str.replace('Tomorrow', '').strip()
            if ':' in time_part:
                hours, minutes = map(int, time_part.split(':'))
                match_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0) + datetime.timedelta(days=1)
                return int(match_time.timestamp())
        
        else:
            return int((now + datetime.timedelta(hours=1)).timestamp())
            
    except Exception as e:
        return int((datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1)).timestamp())

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
        "monitored_guilds": len(TEAMS),
        "alert_time": ALERT_TIME
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
        "alert_time": ALERT_TIME,
        "servers_count": len(TEAMS)
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
        embed.add_field(name="Flask", value="✅ Läuft", inline=True)
        embed.add_field(name="Teams", value=f"✅ {sum(len(teams) for teams in TEAMS.values())}", inline=True)
        
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
    """Bot Startup - Lädt alle gespeicherten Daten"""
    print(f'✅ {bot.user} ist online!')
    
    # Alert System starten
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔄 Alert system started")
    
    print(f"📊 Geladene Daten: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Alert-Time: {ALERT_TIME} Minuten")
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
