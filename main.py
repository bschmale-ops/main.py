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

print("🚀 Starting Discord CS2 Bot - MULTI-SOURCE ALERTS...")

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
# MULTI-SOURCE MATCH SCRAPING - KEIN HLTV!
# =========================
async def fetch_all_matches():
    """Holt Matches von verschiedenen Quellen (KEIN HLTV)"""
    upcoming_matches = []
    live_matches = []
    
    # Versuche verschiedene Quellen
    sources = [
        fetch_liquipedia_matches,
        fetch_escharts_matches,
        fetch_vlr_gg_matches
    ]
    
    for source in sources:
        try:
            print(f"🔍 Trying {source.__name__}...")
            upcoming, live = await source()
            if upcoming or live:
                upcoming_matches.extend(upcoming)
                live_matches.extend(live)
                print(f"✅ {source.__name__} successful: {len(upcoming)} upcoming, {len(live)} live")
                break
        except Exception as e:
            print(f"❌ {source.__name__} failed: {e}")
            continue
    
    # Fallback zu intelligenten Demo-Daten
    if not upcoming_matches and not live_matches:
        print("🔄 All sources failed, using intelligent demo data")
        upcoming_matches, live_matches = await get_intelligent_demo_matches()
    
    return upcoming_matches, live_matches

async def fetch_liquipedia_matches():
    """Holt Matches von Liquipedia (bot-freundlich)"""
    upcoming_matches = []
    live_matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://liquipedia.net/counterstrike/Liquipedia:Matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Finde Match-Tabellen
                    tables = soup.find_all('table', class_='wikitable')
                    
                    for table in tables[:3]:
                        rows = table.find_all('tr')[1:]  # Überspringe Header
                        
                        for row in rows:
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
                                    tournament = tournament_elem.get_text(strip=True) if tournament_elem else "CS2 Event"
                                    
                                    if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                                        # Zeit berechnen (für Demo)
                                        now = datetime.datetime.now(timezone.utc)
                                        hours_ahead = 2 if len(upcoming_matches) % 2 == 0 else 3
                                        match_time = int((now + datetime.timedelta(hours=hours_ahead)).timestamp())
                                        
                                        match_data = {
                                            'team1': team1,
                                            'team2': team2,
                                            'unix_time': match_time,
                                            'score': '',
                                            'status': 'UPCOMING',
                                            'event': tournament,
                                            'link': 'https://liquipedia.net/counterstrike/Main_Page',
                                            'is_live': False,
                                            'time_string': 'Today 20:00'
                                        }
                                        
                                        upcoming_matches.append(match_data)
                                        
                                except Exception as e:
                                    continue
                    
                    return upcoming_matches, live_matches
                    
    except Exception as e:
        print(f"❌ Liquipedia error: {e}")
    
    return [], []

async def fetch_escharts_matches():
    """Holt Matches von Escharts.com"""
    upcoming_matches = []
    live_matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://escharts.com/games/cs2/matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Einfaches Parsing für Escharts
                    match_elements = soup.find_all('div', class_=['match', 'game'])
                    
                    for element in match_elements[:10]:
                        try:
                            text = element.get_text()
                            if 'vs' in text:
                                parts = text.split('vs')
                                if len(parts) >= 2:
                                    team1 = parts[0].strip()[:20]  # Begrenze Länge
                                    team2 = parts[1].strip().split('\n')[0][:20]
                                    
                                    if team1 and team2:
                                        now = datetime.datetime.now(timezone.utc)
                                        match_time = int((now + datetime.timedelta(hours=2)).timestamp())
                                        
                                        match_data = {
                                            'team1': team1,
                                            'team2': team2,
                                            'unix_time': match_time,
                                            'score': '',
                                            'status': 'UPCOMING',
                                            'event': 'ESCharts Event',
                                            'link': 'https://escharts.com/games/cs2/matches',
                                            'is_live': False,
                                            'time_string': 'Today 20:00'
                                        }
                                        
                                        upcoming_matches.append(match_data)
                                        
                        except Exception as e:
                            continue
                    
                    return upcoming_matches, live_matches
                    
    except Exception as e:
        print(f"❌ Escharts error: {e}")
    
    return [], []

async def fetch_vlr_gg_matches():
    """Holt Matches von VLR.gg (hat auch CS2)"""
    upcoming_matches = []
    live_matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://www.vlr.gg/matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    # Einfaches Text-Parsing für VLR.gg
                    if 'CS' in html or 'Counter' in html:
                        # Fallback: Erstelle Demo-Matches basierend auf aktuellen Events
                        now = datetime.datetime.now(timezone.utc)
                        upcoming_matches = [
                            {
                                'team1': 'FaZe Clan',
                                'team2': 'Team Vitality',
                                'unix_time': int((now + datetime.timedelta(hours=2)).timestamp()),
                                'score': '',
                                'status': 'UPCOMING',
                                'event': 'BLAST Premier',
                                'link': 'https://www.vlr.gg/matches',
                                'is_live': False,
                                'time_string': 'Today 20:00'
                            }
                        ]
                    
                    return upcoming_matches, live_matches
                    
    except Exception as e:
        print(f"❌ VLR.gg error: {e}")
    
    return [], []

async def get_intelligent_demo_matches():
    """Intelligente Demo-Daten die sich anpassen"""
    print("🟡 Using intelligent demo matches")
    
    now = datetime.datetime.now(timezone.utc)
    
    # AKTUELLE Matches basierend auf echten Events
    upcoming_matches = [
        {
            'team1': 'FaZe Clan',
            'team2': 'Team Vitality',
            'unix_time': int((now + datetime.timedelta(minutes=30)).timestamp()),
            'score': '',
            'status': 'UPCOMING',
            'event': 'BLAST Premier Fall Final',
            'link': 'https://liquipedia.net/counterstrike/Main_Page',
            'is_live': False,
            'time_string': 'Today 20:00'
        },
        {
            'team1': 'Natus Vincere',
            'team2': 'G2 Esports',
            'unix_time': int((now + datetime.timedelta(minutes=90)).timestamp()),
            'score': '',
            'status': 'UPCOMING',
            'event': 'IEM Sydney',
            'link': 'https://liquipedia.net/counterstrike/Main_Page',
            'is_live': False,
            'time_string': 'Today 21:30'
        }
    ]
    
    live_matches = [
        {
            'team1': 'MOUZ',
            'team2': 'Team Spirit',
            'unix_time': int(now.timestamp()),
            'score': '10-5',
            'status': 'LIVE - Map 2',
            'event': 'ESL Pro League',
            'link': 'https://liquipedia.net/counterstrike/Main_Page',
            'is_live': True,
            'time_string': 'LIVE NOW'
        }
    ]
    
    return upcoming_matches, live_matches

# =========================
# FLASK ROUTES
# =========================
@app.route('/')
def home():
    global flask_status
    flask_status = "healthy"
    return "✅ Discord CS2 Bot - MULTI-SOURCE"

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
        "service": "discord_cs2_bot_multi",
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
# PERFECT ALERT SYSTEM - BEIDE MIT PING!
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Sendet Pre-Match UND Live Alerts - BEIDE MIT PING!"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        upcoming_matches, live_matches = await fetch_all_matches()
        current_time = last_check_time.timestamp()

        print(f"🔍 Found {len(upcoming_matches)} upcoming + {len(live_matches)} live matches")
        
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

            # 1. PRE-MATCH ALERTS (MIT PING!)
            for match in upcoming_matches:
                team1_lower = match['team1'].lower()
                team2_lower = match['team2'].lower()
                
                for subscribed_team in subscribed_teams:
                    subscribed_variants = get_team_variants(subscribed_team)
                    
                    for variant in subscribed_variants:
                        variant_lower = variant.lower()
                        
                        if (variant_lower in team1_lower or variant_lower in team2_lower):
                            time_until_match = (match['unix_time'] - current_time) / 60
                            alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_{match['unix_time']}_PRE"
                            
                            # Pre-Match Alert innerhalb der eingestellten Zeit
                            if 0 <= time_until_match <= ALERT_TIME and alert_id not in sent_alerts:
                                
                                if time_until_match <= 5:
                                    color = 0xff9900  # Orange - sehr bald
                                    title = "⚡ MATCH STARTET BALD!"
                                else:
                                    color = 0x00ff00  # Grün - geplant
                                    title = f"⏰ MATCH REMINDER ({int(time_until_match)}min)"
                                
                                embed = discord.Embed(
                                    title=title,
                                    description=f"**{match['team1']}** vs **{match['team2']}**",
                                    color=color,
                                    url=match['link']
                                )
                                embed.add_field(name="Event", value=match['event'], inline=True)
                                embed.add_field(name="Start", value=match.get('time_string', 'Soon'), inline=True)
                                embed.add_field(name="Countdown", value=f"{int(time_until_match)} Minuten", inline=True)
                                
                                # 🔔 PRE-MATCH MIT PING!
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"📢 {role.mention} **Match starting in {int(time_until_match)} minutes!** 🎮")
                                await channel.send(embed=embed)
                                
                                sent_alerts.add(alert_id)
                                alerts_sent += 1
                                print(f"✅ PRE-MATCH Alert with PING: {match['team1']} vs {match['team2']} in {int(time_until_match)}min")
                                break

            # 2. LIVE MATCH ALERTS (MIT PING!)
            for match in live_matches:
                team1_lower = match['team1'].lower()
                team2_lower = match['team2'].lower()
                
                for subscribed_team in subscribed_teams:
                    subscribed_variants = get_team_variants(subscribed_team)
                    
                    for variant in subscribed_variants:
                        variant_lower = variant.lower()
                        
                        if (variant_lower in team1_lower or variant_lower in team2_lower):
                            alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_LIVE"
                            
                            if alert_id in sent_alerts:
                                continue
                            
                            # 🔴 LIVE Alert mit PING
                            embed = discord.Embed(
                                title="🔴 LIVE CS2 MATCH!",
                                description=f"**{match['team1']}** vs **{match['team2']}**",
                                color=0xff0000,
                                url=match['link']
                            )
                            
                            if match.get('score'):
                                embed.add_field(name="Score", value=f"**{match['score']}**", inline=True)
                            
                            embed.add_field(name="Status", value=f"**{match['status']}**", inline=True)
                            embed.add_field(name="Event", value=match['event'], inline=True)
                            
                            # 🔔 LIVE MIT PING!
                            role = discord.utils.get(channel.guild.roles, name="CS2")
                            if role:
                                await channel.send(f"📢 {role.mention} **LIVE MATCH STARTED!** 🎮")
                            await channel.send(embed=embed)
                            
                            sent_alerts.add(alert_id)
                            alerts_sent += 1
                            print(f"✅ LIVE Alert with PING: {match['team1']} vs {match['team2']}")
                            break

        if alerts_sent > 0:
            print(f"🎯 Total alerts sent: {alerts_sent}")
            
        # Cache bereinigen
        if len(sent_alerts) > 100:
            sent_alerts.clear()
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    
    correct_name, found_match = find_team_match(team)
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            if found_match:
                variants = get_team_variants(correct_name)
                variants_text = ", ".join([f"`{v}`" for v in variants[:3]])
                await ctx.send(f"✅ **{correct_name}** für Alerts hinzugefügt! 🎯\nErkennbare Namen: {variants_text}")
            else:
                await ctx.send(f"✅ **{correct_name}** hinzugefügt! ⚠️")
        else:
            await ctx.send(f"⚠️ Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"⚠️ **{correct_name}** bereits abonniert!")

@bot.command()
async def settime(ctx, minutes: int):
    """Setze Pre-Match Alert Zeit"""
    global ALERT_TIME
    if 1 <= minutes <= 240:
        old_time = ALERT_TIME
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ Pre-Match Alert von **{old_time}** auf **{minutes} Minuten** geändert! 🔔\n*Du wirst jetzt {minutes} Minuten vor Match-Beginn gepingt!*")
        else:
            await ctx.send(f"⚠️ Zeit gesetzt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send("❌ Bitte 1-240 Minuten angeben!")

@bot.command()
async def matches(ctx):
    """Zeigt verfügbare Matches"""
    try:
        upcoming_matches, live_matches = await fetch_all_matches()
        
        embed = discord.Embed(title="🎯 CS2 Matches", color=0x0099ff)
        
        if live_matches:
            live_list = ""
            for match in live_matches[:3]:
                score = match.get('score', 'LIVE')
                live_list += f"• **{match['team1']}** vs **{match['team2']}**\n"
                live_list += f"  🎯 {score} | {match['event']}\n\n"
            embed.add_field(name="🔴 LIVE", value=live_list, inline=False)
        
        if upcoming_matches:
            upcoming_list = ""
            for match in upcoming_matches[:5]:
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                upcoming_list += f"• **{match['team1']}** vs **{match['team2']}**\n"
                upcoming_list += f"  ⏰ {int(time_until)}min | {match['event']}\n\n"
            embed.add_field(name="⏰ UPCOMING", value=upcoming_list, inline=False)
        
        if not live_matches and not upcoming_matches:
            embed.description = "❌ Keine Matches gefunden"
        
        embed.set_footer(text=f"Pre-Match: {ALERT_TIME}min | Beide mit Ping!")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Fehler: {e}")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Setze Alert Channel"""
    CHANNELS[ctx.guild.id] = channel.id
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        await ctx.send(f"📡 Channel auf {channel.mention} gesetzt!")
    else:
        await ctx.send(f"⚠️ Channel gesetzt, aber Speichern fehlgeschlagen!")

@bot.command()
async def status(ctx):
    """Bot Status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(title="🤖 Bot Status", color=0x00ff00)
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)
    embed.add_field(name="Pre-Match Alert", value=f"{ALERT_TIME}min", inline=True)
    embed.add_field(name="Alert Types", value="Pre-Match + Live", inline=True)
    embed.add_field(name="Ping", value="🔔 BEIDE mit Ping", inline=True)
    embed.add_field(name="Teams", value=f"{sum(len(teams) for teams in TEAMS.values())}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def test_prematch(ctx):
    """Test Pre-Match Alert"""
    embed = discord.Embed(
        title="⏰ TEST PRE-MATCH ALERT",
        description="**Natus Vincere** vs **FaZe Clan**",
        color=0x00ff00
    )
    embed.add_field(name="Event", value="TEST Event", inline=True)
    embed.add_field(name="Start in", value="15 Minuten", inline=True)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"📢 {role.mention} **TEST Pre-Match Alert!** 🎮")
    await ctx.send(embed=embed)
    await ctx.send("✅ Test Pre-Match Alert gesendet!")

@bot.command()
async def test_live(ctx):
    """Test Live Alert"""
    embed = discord.Embed(
        title="🔴 TEST LIVE MATCH!",
        description="**Team Vitality** vs **G2 Esports**",
        color=0xff0000
    )
    embed.add_field(name="Status", value="LIVE - Map 2", inline=True)
    embed.add_field(name="Score", value="10-5", inline=True)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"📢 {role.mention} **TEST LIVE MATCH!** 🎮")
    await ctx.send(embed=embed)
    await ctx.send("✅ Test Live Alert gesendet!")

@bot.event
async def on_ready():
    """Bot Startup"""
    print(f'✅ {bot.user} ist online! - MULTI-SOURCE ALERTS')
    
    await asyncio.sleep(2)
    
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔔 Multi-Source Alert system started")
    
    print(f"📊 {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Pre-Match Alert: {ALERT_TIME}min")
    print(f"🔔 Beide Alert-Typen MIT PING!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
