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

print("🚀 Starting Discord CS2 Bot - ENHANCED VISUALS & ALL COMMANDS...")

# =========================
# FLASK STATUS SERVER
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
# TEAM NAME MAPPING & FUZZY MATCHING
# =========================
TEAM_SYNONYMS = {
    'Natus Vincere': ['navi', 'natus vincere', 'na`vi', 'natus', 'vincere'],
    'FaZe Clan': ['faze', 'faze clan', 'faze esports', 'fazeclan'],
    'Team Vitality': ['vitality', 'team vitality', 'vit', 'team vit'],
    'G2 Esports': ['g2', 'g2 esports', 'g2esports'],
    'MOUZ': ['mousesports', 'mouz', 'mouse', 'mous'],
    'Heroic': ['heroic'],
    'Astralis': ['astralis'],
    'Ninjas in Pyjamas': ['nip', 'ninjas in pyjamas', 'ninjas', 'pyjamas'],
    'Cloud9': ['cloud9', 'c9', 'cloud 9'],
    'Team Spirit': ['spirit', 'team spirit'],
    'Virtus.pro': ['virtus pro', 'vp', 'virtus.pro', 'virtus'],
    'ENCE': ['ence'],
    'Complexity': ['complexity', 'col'],
    'BIG': ['big', 'berlin international gaming'],
    'FURIA': ['furia'],
    'Imperial': ['imperial'],
    'Eternal Fire': ['eternal fire', 'ef'],
    'Monte': ['monte'],
    '9z Team': ['9z', '9z team'],
    'paiN Gaming': ['pain', 'pain gaming', 'paining'],
    'MIBR': ['mibr']
}

def find_team_match(input_team):
    """Findet das korrekte Team-Name mit Fuzzy Matching"""
    input_lower = input_team.lower().strip()
    
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    
    for correct_name, variants in TEAM_SYNONYMS.items():
        for variant in variants:
            variant_lower = variant.lower()
            if input_lower in variant_lower or variant_lower in input_lower:
                return correct_name, True
            
            input_words = set(input_lower.split())
            variant_words = set(variant_lower.split())
            if input_words & variant_words:
                return correct_name, True
    
    return input_team, False

def get_team_variants(team_name):
    """Gibt alle bekannten Varianten eines Teams zurück"""
    team_lower = team_name.lower()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if team_lower == correct_name.lower() or team_lower in [v.lower() for v in variants]:
            return variants
    return [team_name]

# =========================
# DATA MANAGEMENT
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    """Lädt alle gespeicherten Daten mit Fallback"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                if "ALERT_TIME" not in data:
                    data["ALERT_TIME"] = 30
                
                server_count = len(data.get('TEAMS', {}))
                total_teams = sum(len(teams) for teams in data.get('TEAMS', {}).values())
                print(f"📂 Daten geladen: {server_count} Server, {total_teams} Teams")
                return data
        else:
            print("📂 Keine gespeicherten Daten gefunden, starte frisch")
            default_data = {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
            save_data(default_data)
            return default_data
            
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data(data):
    """Speichert alle Daten mit Error-Handling"""
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
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
# OPTIMIZED HLTV SCRAPING
# =========================
async def fetch_hltv_matches():
    """Holt ECHTE Matches von HLTV - optimierte Version"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://www.hltv.org/matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            print("🔍 Fetching REAL matches from HLTV...")
            async with session.get(url, headers=headers, timeout=30) as response:
                print(f"📡 HLTV Response: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Einfacheres aber effektiveres Parsing
                    match_elements = soup.find_all('div', class_='upcomingMatch')
                    
                    for match in match_elements[:15]:  # Erste 15 Matches
                        try:
                            # Team Namen extrahieren
                            team_elements = match.find_all('div', class_='matchTeamName')
                            if len(team_elements) >= 2:
                                team1 = team_elements[0].get_text(strip=True)
                                team2 = team_elements[1].get_text(strip=True)
                                
                                # Match Zeit
                                time_element = match.find('div', class_='matchTime')
                                match_time = time_element.get_text(strip=True) if time_element else "Soon"
                                
                                # Event Name
                                event_element = match.find('div', class_='matchEventName')
                                event = event_element.get_text(strip=True) if event_element else "CS2 Event"
                                
                                # Match Link
                                match_link = match.get('data-z-url', 'https://www.hltv.org/matches')
                                if match_link and not match_link.startswith('http'):
                                    match_link = f"https://www.hltv.org{match_link}"
                                
                                if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                                    # Echte Zeit berechnen
                                    unix_time = parse_match_time(match_time)
                                    
                                    matches.append({
                                        'team1': team1,
                                        'team2': team2,
                                        'unix_time': unix_time,
                                        'event': event,
                                        'link': match_link,
                                        'time_string': match_time,
                                        'is_live': False
                                    })
                                    print(f"✅ Found: {team1} vs {team2} - {match_time}")
                                    
                        except Exception as e:
                            continue
                    
                    print(f"🎯 Total matches found: {len(matches)}")
                    return matches
                    
                else:
                    print(f"❌ HLTV responded with status: {response.status}")
                    return []
                    
    except Exception as e:
        print(f"❌ HLTV error: {e}")
        return []

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
        
        # Fallback: 2 Stunden in der Zukunft
        return int((now + datetime.timedelta(hours=2)).timestamp())
            
    except:
        return int((datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=2)).timestamp())

# =========================
# FLASK ROUTES
# =========================
@app.route('/')
def home():
    global flask_status
    flask_status = "healthy"
    return "✅ Discord CS2 Bot - ENHANCED VISUALS"

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
        "flask_status": flask_status
    })

@app.route('/health')
def health():
    global flask_status
    flask_status = "healthy"
    return jsonify({
        "status": "healthy",
        "service": "discord_cs2_bot_enhanced",
        "last_check": last_check_time.isoformat(),
        "teams_count": sum(len(teams) for teams in TEAMS.values()),
        "servers_count": len(TEAMS),
        "alert_time": ALERT_TIME,
        "flask_port": flask_port,
        "flask_status": flask_status
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
    """Startet Flask Server"""
    global flask_port, flask_status
    
    potential_ports = []
    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        potential_ports.append(int(env_port))
    
    potential_ports.append(1000)
    potential_ports.append(10000)
    
    for port in potential_ports:
        if is_port_available(port):
            flask_port = port
            break
    else:
        flask_port = 0
    
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
# ENHANCED ALERT SYSTEM - MIT VISUAL VERBESSERUNGEN!
# =========================
sent_alerts = set()

@tasks.loop(minutes=3)
async def send_alerts():
    """Sendet Alerts für Matches - MIT VISUAL VERBESSERUNGEN!"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        matches = await fetch_hltv_matches()
        current_time = last_check_time.timestamp()

        print(f"🔍 Checking {len(matches)} matches...")
        
        alerts_sent = 0
        
        for guild_id, subscribed_teams in TEAMS.items():
            if not subscribed_teams:
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
                
                for subscribed_team in subscribed_teams:
                    subscribed_variants = get_team_variants(subscribed_team)
                    
                    for variant in subscribed_variants:
                        variant_lower = variant.lower()
                        
                        # Einfache aber effektive Team-Erkennung
                        if (variant_lower in team1_lower or 
                            variant_lower in team2_lower or
                            team1_lower in variant_lower or 
                            team2_lower in variant_lower):
                            
                            time_until_match = (match['unix_time'] - current_time) / 60
                            alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_{match['unix_time']}"
                            
                            # Alert wenn Match innerhalb der Alert-Time startet
                            if 0 <= time_until_match <= ALERT_TIME and alert_id not in sent_alerts:
                                
                                # 🎨 VISUAL VERBESSERUNGEN - GRÖSSERE ELEMENTE!
                                if time_until_match <= 5:
                                    color = 0xff9900  # Orange - sehr bald
                                    title = "🔔 ⚡ MATCH STARTET BALD! ⚡"
                                else:
                                    color = 0x00ff00  # Grün - geplant
                                    title = f"🔔 ⏰ MATCH REMINDER ({int(time_until_match)}min) ⏰"
                                
                                # 🎨 VERBESSERTES EMBED MIT GRÖSSERER SCHRIFT & MEHR EMOJIS
                                embed = discord.Embed(
                                    title=title,
                                    description=f"# 🎮 **{match['team1']}**  🆚  **{match['team2']}** 🎮",
                                    color=color,
                                    url=match['link']
                                )
                                embed.add_field(name="**📅 EVENT**", value=f"**{match['event']}**", inline=True)
                                embed.add_field(name="**⏰ START IN**", value=f"**{int(time_until_match)} MINUTEN**", inline=True)
                                embed.add_field(name="**🕐 ZEIT**", value=f"**{match['time_string']}**", inline=True)
                                embed.add_field(name="**🔗 LINK**", value=f"[📺 Match ansehen]({match['link']})", inline=False)
                                
                                # 🎨 VERBESSERTER PING MIT GRÖSSERER SCHRIFT
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 {role.mention} **MATCH STARTING IN {int(time_until_match)} MINUTES!** 🎮")
                                await channel.send(embed=embed)
                                
                                sent_alerts.add(alert_id)
                                alerts_sent += 1
                                print(f"✅ Alert sent: {match['team1']} vs {match['team2']} in {int(time_until_match)}min")
                                break

        if alerts_sent > 0:
            print(f"🎯 Total alerts sent: {alerts_sent}")
            
        # Cache bereinigen
        if len(sent_alerts) > 50:
            sent_alerts.clear()
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS - MIT ALLEN NOTWENDIGEN COMMANDS!
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für Alerts"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    
    correct_name, found_match = find_team_match(team)
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            if found_match:
                variants = get_team_variants(correct_name)
                variants_text = ", ".join([f"`{v}`" for v in variants[:3]])
                await ctx.send(f"✅ **{correct_name}** für Alerts hinzugefügt! 🎯\n**Erkennbare Namen:** {variants_text}")
            else:
                await ctx.send(f"✅ **{correct_name}** hinzugefügt! ⚠️")
        else:
            await ctx.send(f"⚠️ **Speichern fehlgeschlagen!**")
    else:
        await ctx.send(f"⚠️ **{correct_name}** bereits abonniert!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Entferne ein Team von Alerts"""
    guild_id = ctx.guild.id
    
    correct_name, found_match = find_team_match(team)
    
    if guild_id in TEAMS and correct_name in TEAMS[guild_id]:
        TEAMS[guild_id].remove(correct_name)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"❌ **{correct_name}** von Alerts entfernt!")
        else:
            await ctx.send(f"⚠️ **{correct_name}** entfernt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"❌ **Team {correct_name} nicht gefunden!**")

@bot.command()
async def list_teams(ctx):
    """Zeige alle abonnierten Teams"""
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    
    if teams:
        team_list = "\n".join([f"• **{team}**" for team in teams])
        embed = discord.Embed(
            title="📋 👥 ABONNIERTE TEAMS 👥",
            description=team_list,
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ **Noch keine Teams abonniert!**")

@bot.command()
async def settime(ctx, minutes: int):
    """Setze Alert-Vorlaufzeit in Minuten"""
    global ALERT_TIME
    if 1 <= minutes <= 240:
        old_time = ALERT_TIME
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ **ALERT-ZEIT VON {old_time} AUF {minutes} MINUTEN GESETZT!** 🔔")
        else:
            await ctx.send(f"⚠️ **Zeit gesetzt, aber Speichern fehlgeschlagen!**")
    else:
        await ctx.send("❌ **Bitte 1-240 Minuten angeben!**")

@bot.command()
async def matches(ctx):
    """Zeigt verfügbare Matches an"""
    try:
        matches = await fetch_hltv_matches()
        
        if matches:
            # 🎨 VERBESSERTES MATCHES EMBED MIT GRÖSSERER SCHRIFT
            match_list = ""
            for i, match in enumerate(matches[:8], 1):
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                match_list += f"{i}. **{match['team1']}** 🆚 **{match['team2']}**\n"
                match_list += f"   ⏰ **{int(time_until)}min** | 📅 **{match['event']}**\n"
                match_list += f"   🕐 **{match['time_string']}**\n\n"
            
            embed = discord.Embed(
                title="🎯 📅 VERFÜGBARE CS2 MATCHES 📅",
                description=match_list,
                color=0x0099ff
            )
            embed.set_footer(text=f"🔔 Alert-Time: {ALERT_TIME}min | ⏰ Check: alle 3min")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ **Keine Matches auf HLTV gefunden**")
            
    except Exception as e:
        await ctx.send(f"❌ **Fehler:** {e}")

@bot.command()
async def debug_matches(ctx):
    """Debug-Informationen zu gefundenen Matches"""
    try:
        matches = await fetch_hltv_matches()
        
        embed = discord.Embed(
            title="🔧 📊 DEBUG MATCHES 📊",
            color=0x0099ff
        )
        embed.add_field(name="**🔍 GEFUNDENE MATCHES**", value=f"**{len(matches)}**", inline=True)
        embed.add_field(name="**⏰ ALERT-TIME**", value=f"**{ALERT_TIME}min**", inline=True)
        embed.add_field(name="**🔄 LETZTER CHECK**", value=f"**{last_check_time.strftime('%H:%M:%S')}**", inline=True)
        
        if matches:
            match_info = ""
            for i, match in enumerate(matches[:5], 1):
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                match_info += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
                match_info += f"   ⏰ {int(time_until)}min | {match['event']}\n\n"
            embed.add_field(name="**🎯 MATCHES**", value=match_info, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ **Debug Fehler:** {e}")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Setze den Alert-Channel"""
    CHANNELS[ctx.guild.id] = channel.id
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        await ctx.send(f"📡 **CHANNEL AUF {channel.mention} GESETZT!** ✅")
    else:
        await ctx.send(f"⚠️ **Channel gesetzt, aber Speichern fehlgeschlagen!**")

@bot.command()
async def status(ctx):
    """Zeigt Bot-Status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # 🎨 VERBESSERTER STATUS MIT GRÖSSERER SCHRIFT
    embed = discord.Embed(title="🤖 📊 BOT STATUS 📊", color=0x00ff00)
    embed.add_field(name="**🟢 STATUS**", value="**✅ ONLINE**", inline=True)
    embed.add_field(name="**⏰ UPTIME**", value=f"**{hours}h {minutes}m**", inline=True)
    embed.add_field(name="**🔔 ALERTS**", value="**✅ AKTIV**", inline=True)
    embed.add_field(name="**⏱️ ALERT-TIME**", value=f"**{ALERT_TIME}min**", inline=True)
    embed.add_field(name="**👥 TEAMS**", value=f"**{sum(len(teams) for teams in TEAMS.values())}**", inline=True)
    embed.add_field(name="**🔄 INTERVAL**", value="**3 Minuten**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def force_check(ctx):
    """Erzwingt eine sofortige Überprüfung"""
    await ctx.send("🔍 **ERZwinge sofortige Match-Überprüfung...**")
    await send_alerts()
    await ctx.send("✅ **ÜBERPRÜFUNG ABGESCHLOSSEN!**")

@bot.command()
async def test_alert(ctx):
    """Testet einen Alert"""
    # 🎨 VERBESSERTER TEST ALERT
    embed = discord.Embed(
        title="🔔 🎮 TEST ALERT 🎮",
        description="# 🎮 **Natus Vincere**  🆚  **FaZe Clan** 🎮",
        color=0x00ff00
    )
    embed.add_field(name="**📅 EVENT**", value="**TEST EVENT**", inline=True)
    embed.add_field(name="**⏰ START IN**", value="**15 MINUTEN**", inline=True)
    embed.add_field(name="**🕐 ZEIT**", value="**Today 20:00**", inline=True)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention} **TEST ALERT! MATCH STARTING IN 15 MINUTES!** 🎮")
    await ctx.send(embed=embed)
    await ctx.send("✅ **TEST ALERT GESENDET!**")

@bot.command()
async def ping(ctx):
    """Einfacher Ping-Befehl"""
    await ctx.send('🏓 **PONG!** 🎯')

@bot.event
async def on_ready():
    """Bot Startup"""
    print(f'✅ {bot.user} ist online! - ENHANCED VISUALS')
    
    await asyncio.sleep(2)
    
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔔 Enhanced Alert system started")
    
    print(f"📊 {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Alert-Time: {ALERT_TIME}min")
    print(f"🎨 Enhanced Visuals aktiviert!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
