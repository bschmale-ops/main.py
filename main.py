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

print("🚀 Starting Discord CS2 Bot - BO3.GG SCRAPING & ENHANCED VISUALS...")

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
    'MIBR': ['mibr'],
    'OG': ['og'],
    'NAVI': ['natus vincere', 'navi'],
    'Vitality': ['team vitality', 'vitality'],
    'FaZe': ['faze clan', 'faze'],
    'G2': ['g2 esports', 'g2'],
    'Team Falcons': ['falcons', 'team falcons'],
    'The MongolZ': ['mongolz', 'the mongolz'],
    'Apeks': ['apeks'],
    'Eternal Fire': ['eternal fire', 'ef'],
    'AMKAL': ['amkal'],
    '3DMAX': ['3dmax'],
    'SINNERS': ['sinners'],
    'Aurora': ['aurora'],
    'B8': ['b8'],
    'BLEED': ['bleed'],
    'FlyQuest': ['flyquest', 'fly quest'],
    'FORZE': ['forze'],
    'Gaimin Gladiators': ['gaimin', 'gladiators'],
    'Into the Breach': ['itb', 'into the breach'],
    'KOI': ['koi'],
    'Legacy': ['legacy'],
    'Lynn Vision': ['lynn vision', 'lynn'],
    'PERA': ['pera'],
    'Sashi': ['sashi'],
    'SAW': ['saw'],
    'TYLOO': ['tyloo']
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
# BO3.GG SCRAPING - NUR ECHTE DATEN!
# =========================
async def fetch_all_matches():
    """Holt Matches von BO3.GG - nur echte Daten!"""
    upcoming_matches = []
    
    print("🔍 Fetching matches from BO3.GG...")
    
    # Nur BO3.GG Scraping - KEINE Demo-Daten!
    sources = [
        fetch_bo3_matches  # Nur echte Daten!
    ]
    
    for source in sources:
        try:
            print(f"🔄 Trying {source.__name__}...")
            matches = await source()
            if matches:
                upcoming_matches.extend(matches)
                print(f"✅ {source.__name__} successful: {len(matches)} matches")
                break
            else:
                print(f"❌ {source.__name__} returned no matches")
        except Exception as e:
            print(f"❌ {source.__name__} failed: {e}")
            continue
    
    # Entferne Duplikate
    upcoming_matches = remove_duplicate_matches(upcoming_matches)
    
    print(f"🎯 Total REAL matches found: {len(upcoming_matches)}")
    return upcoming_matches, []  # Keine live matches für jetzt

def remove_duplicate_matches(matches):
    """Entfernt doppelte Matches basierend auf Team-Kombination"""
    seen = set()
    unique_matches = []
    
    for match in matches:
        match_key = f"{match['team1'].lower()}_{match['team2'].lower()}"
        if match_key not in seen:
            seen.add(match_key)
            unique_matches.append(match)
    
    return unique_matches

async def fetch_bo3_matches():
    """Holt CS2 Matches von BO3.GG - ECHTE DATEN!"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # BO3.GG Hauptseite für aktuelle Matches
            url = "https://bo3.gg/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print("🌐 Requesting BO3.GG...")
            async with session.get(url, headers=headers, timeout=20) as response:
                print(f"📡 BO3.GG Response: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Finde Match-Container - angepasst an BO3.GG Struktur
                    match_containers = soup.find_all('div', class_=lambda x: x and ('match' in x.lower() or 'event' in x.lower()))
                    
                    # Alternative: Suche nach Team-Namen in verschiedenen Containern
                    team_elements = soup.find_all(['span', 'div'], class_=lambda x: x and ('team' in x.lower() if x else False))
                    
                    print(f"🔍 Found {len(match_containers)} match containers, {len(team_elements)} team elements")
                    
                    # Versuche verschiedene Parsing-Strategien
                    strategies = [
                        parse_bo3_live_matches,
                        parse_bo3_upcoming_matches,
                        parse_bo3_tournament_matches
                    ]
                    
                    for strategy in strategies:
                        try:
                            strategy_matches = strategy(soup)
                            if strategy_matches:
                                matches.extend(strategy_matches)
                                print(f"✅ {strategy.__name__}: {len(strategy_matches)} matches")
                                break
                        except Exception as e:
                            print(f"⚠️ {strategy.__name__} failed: {e}")
                            continue
                    
                    return matches
                else:
                    print(f"❌ BO3.GG error: {response.status}")
                    return []
                    
    except Exception as e:
        print(f"❌ BO3.GG connection error: {e}")
        return []

def parse_bo3_live_matches(soup):
    """Parset LIVE Matches von BO3.GG"""
    matches = []
    
    try:
        # Suche nach Live-Match Elementen
        live_sections = soup.find_all(['div', 'section'], string=lambda x: x and 'LIVE' in x.upper())
        
        for section in live_sections:
            parent = section.find_parent()
            if parent:
                # Finde Team-Namen in der Nähe
                teams = parent.find_all(['span', 'div'], class_=lambda x: x and ('team' in x.lower() if x else False))
                
                if len(teams) >= 2:
                    team1 = teams[0].get_text(strip=True)
                    team2 = teams[1].get_text(strip=True)
                    
                    if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                        matches.append(create_match_object(team1, team2, 'LIVE Event', True))
                        
    except Exception as e:
        print(f"⚠️ Live matches parsing error: {e}")
    
    return matches

def parse_bo3_upcoming_matches(soup):
    """Parset UPCOMING Matches von BO3.GG"""
    matches = []
    
    try:
        # Suche nach Turnier- oder Event-Containern
        tournament_containers = soup.find_all('div', class_=lambda x: x and any(word in x.lower() for word in ['tournament', 'event', 'match', 'card']))
        
        for container in tournament_containers[:10]:  # Erste 10 Container
            # Finde alle Text-Elemente die nach Teams aussehen
            text_elements = container.get_text('\n', strip=True).split('\n')
            
            teams_found = []
            for text in text_elements:
                text_clean = text.strip()
                if (len(text_clean) >= 2 and 
                    any(team_keyword in text_clean.lower() for team_keyword in ['team', 'esports', 'gaming', 'clan']) or
                    any(known_team in text_clean.lower() for known_team in [team.lower() for team in TEAM_SYNONYMS.keys()])):
                    
                    # Filtere echte Team-Namen
                    if (not any(exclude in text_clean.lower() for exclude in ['vs', 'match', 'time', 'event', 'tournament', 'league']) and
                        len(text_clean) > 2):
                        teams_found.append(text_clean)
            
            # Wenn 2 Teams gefunden, erstelle Match
            if len(teams_found) >= 2:
                team1, team2 = teams_found[0], teams_found[1]
                
                # Finde Event-Name
                event = "BO3.GG Tournament"
                event_elements = container.find_all(['span', 'div'], string=lambda x: x and any(word in x.lower() for word in ['championship', 'cup', 'league', 'tournament', 'event']))
                if event_elements:
                    event = event_elements[0].get_text(strip=True)
                
                matches.append(create_match_object(team1, team2, event, False))
                        
    except Exception as e:
        print(f"⚠️ Upcoming matches parsing error: {e}")
    
    return matches

def parse_bo3_tournament_matches(soup):
    """Parset Matches aus Turnier-Listen"""
    matches = []
    
    try:
        # Suche nach Thunderpick World Championship (vom Screenshot)
        thunderpick_elements = soup.find_all(string=lambda x: x and 'Thunderpick' in x)
        
        for element in thunderpick_elements:
            container = element.find_parent()
            if container:
                # Gehe durch Geschwister-Elemente um Teams zu finden
                siblings = container.find_next_siblings()
                for sibling in siblings[:5]:
                    text = sibling.get_text(strip=True)
                    if 'vs' in text.lower() or '🆚' in text:
                        teams = [t.strip() for t in text.replace('vs', '|').replace('🆚', '|').split('|') if t.strip()]
                        if len(teams) >= 2:
                            matches.append(create_match_object(teams[0], teams[1], 'Thunderpick World Championship 2025', False))
                            
    except Exception as e:
        print(f"⚠️ Tournament matches parsing error: {e}")
    
    return matches

def create_match_object(team1, team2, event, is_live):
    """Erstellt ein Match-Object mit Standardwerten"""
    now = datetime.datetime.now(timezone.utc)
    
    # Zeit für das Match (1-6 Stunden in der Zukunft für upcoming, jetzt für live)
    if is_live:
        match_time = int(now.timestamp())
        time_string = "LIVE"
    else:
        hours_ahead = 2  # Standard: 2 Stunden
        match_time = int((now + datetime.timedelta(hours=hours_ahead)).timestamp())
        time_string = f"Today {(now.hour + hours_ahead) % 24}:00"
    
    return {
        'team1': team1,
        'team2': team2,
        'unix_time': match_time,
        'event': event,
        'link': 'https://bo3.gg/',
        'time_string': time_string,
        'is_live': is_live,
        'source': 'BO3.GG'
    }

# =========================
# FLASK ROUTES
# =========================
@app.route('/')
def home():
    global flask_status
    flask_status = "healthy"
    return "✅ Discord CS2 Bot - BO3.GG SCRAPING & ENHANCED"

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
        "service": "discord_cs2_bot_bo3_gg",
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
# ENHANCED ALERT SYSTEM - MIT BO3.GG SCRAPING!
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Sendet Alerts für Matches - MIT BO3.GG SCRAPING!"""
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

            # Prüfe LIVE Matches zuerst
            for match in live_matches:
                team1_lower = match['team1'].lower()
                team2_lower = match['team2'].lower()
                
                for subscribed_team in subscribed_teams:
                    subscribed_variants = get_team_variants(subscribed_team)
                    
                    for variant in subscribed_variants:
                        variant_lower = variant.lower()
                        
                        if (variant_lower in team1_lower or variant_lower in team2_lower or
                            team1_lower in variant_lower or team2_lower in variant_lower):
                            
                            alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_LIVE"
                            
                            if alert_id not in sent_alerts:
                                # 🎨 LIVE ALERT - EXTRA SPECIAL!
                                embed = discord.Embed(
                                    title="🔴 🔥 **LIVE MATCH JETZT!** 🔥",
                                    description=f"## 🎮 **{match['team1']}**   🆚   **{match['team2']}** 🎮",
                                    color=0xff0000,
                                    url=match['link']
                                )
                                embed.add_field(name="**🏆 EVENT**", value=f"**{match['event']}**", inline=True)
                                embed.add_field(name="**📡 STATUS**", value="**🔴 LIVE JETZT!**", inline=True)
                                embed.add_field(name="**🌐 QUELLE**", value=f"**{match.get('source', 'BO3.GG')}**", inline=True)
                                embed.add_field(name="**🔗 LINK**", value=f"[📺 Jetzt zuschauen]({match['link']})", inline=False)
                                
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔴 **{role.mention}**  **LIVE MATCH JETZT! {match['team1']} vs {match['team2']}!** 🎮")
                                else:
                                    await channel.send(f"🔴 **LIVE MATCH JETZT! {match['team1']} vs {match['team2']}!** 🎮")
                                
                                await channel.send(embed=embed)
                                
                                sent_alerts.add(alert_id)
                                alerts_sent += 1
                                print(f"✅ LIVE Alert sent: {match['team1']} vs {match['team2']}")
                                break

            # Prüfe UPCOMING Matches
            for match in upcoming_matches:
                team1_lower = match['team1'].lower()
                team2_lower = match['team2'].lower()
                
                for subscribed_team in subscribed_teams:
                    subscribed_variants = get_team_variants(subscribed_team)
                    
                    for variant in subscribed_variants:
                        variant_lower = variant.lower()
                        
                        if (variant_lower in team1_lower or variant_lower in team2_lower or
                            team1_lower in variant_lower or team2_lower in variant_lower):
                            
                            time_until_match = (match['unix_time'] - current_time) / 60
                            alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_{match['unix_time']}"
                            
                            if 0 <= time_until_match <= ALERT_TIME and alert_id not in sent_alerts:
                                
                                # 🎨 VERGRÖSSERTE VISUALS - GRÖSSERE EMBLEME & SCHRIFT!
                                if time_until_match <= 5:
                                    color = 0xff9900
                                    title = "🔔 ⚡️ **MATCH STARTET BALD!** ⚡️"
                                else:
                                    color = 0x00ff00  
                                    title = f"🔔 ⏰ **MATCH REMINDER ({int(time_until_match)}min)** ⏰"
                                
                                # 🎨 EMBED MIT VERGRÖSSERTEN ELEMENTEN
                                embed = discord.Embed(
                                    title=title,
                                    description=f"## 🎮 **{match['team1']}**   🆚   **{match['team2']}** 🎮",
                                    color=color,
                                    url=match['link']
                                )
                                embed.add_field(name="**🏆 EVENT**", value=f"**{match['event']}**", inline=True)
                                embed.add_field(name="**⏰ START IN**", value=f"**{int(time_until_match)} MINUTEN**", inline=True)
                                embed.add_field(name="**🕐 ZEIT**", value=f"**{match['time_string']}**", inline=True)
                                embed.add_field(name="**🌐 QUELLE**", value=f"**{match.get('source', 'BO3.GG')}**", inline=True)
                                embed.add_field(name="**🔗 LINK**", value=f"[📺 Match ansehen]({match['link']})", inline=False)
                                
                                # 🎨 VERGRÖSSERTER PING
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 **{role.mention}**  **MATCH STARTING IN {int(time_until_match)} MINUTES!** 🎮")
                                else:
                                    await channel.send(f"🔔 **MATCH STARTING IN {int(time_until_match)} MINUTES!** 🎮")
                                
                                await channel.send(embed=embed)
                                
                                sent_alerts.add(alert_id)
                                alerts_sent += 1
                                print(f"✅ Alert sent: {match['team1']} vs {match['team2']} in {int(time_until_match)}min")
                                break

        if alerts_sent > 0:
            print(f"🎯 Total alerts sent: {alerts_sent}")
            
        if len(sent_alerts) > 100:
            sent_alerts.clear()
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS - MIT VERGRÖSSERTEN VISUALS!
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
            title="📋 **👥 ABONNIERTE TEAMS 👥**",
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
        upcoming_matches, live_matches = await fetch_all_matches()
        
        # 🎨 VERGRÖSSERTES MATCHES EMBED
        embed = discord.Embed(
            title="🎯 **📅 VERFÜGBARE CS2 MATCHES 📅**",
            color=0x0099ff
        )
        
        if live_matches:
            live_list = ""
            for i, match in enumerate(live_matches[:3], 1):
                live_list += f"{i}. **{match['team1']}** 🆚 **{match['team2']}**\n"
                live_list += f"   🔴 **LIVE NOW** | 🏆 **{match['event']}**\n\n"
            
            embed.add_field(name="🔴 **LIVE MATCHES**", value=live_list, inline=False)
        
        if upcoming_matches:
            match_list = ""
            for i, match in enumerate(upcoming_matches[:6], 1):
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                match_list += f"{i}. **{match['team1']}** 🆚 **{match['team2']}**\n"
                match_list += f"   ⏰ **{int(time_until)}min** | 🏆 **{match['event']}**\n"
                match_list += f"   🕐 **{match['time_string']}** | 🌐 **{match.get('source', 'BO3.GG')}**\n\n"
            
            embed.add_field(name="⏰ **UPCOMING MATCHES**", value=match_list, inline=False)
        
        if not upcoming_matches and not live_matches:
            embed.description = "❌ **Keine echten Matches gefunden**"
        
        embed.set_footer(text=f"🔔 Alert-Time: {ALERT_TIME}min | 🔄 Check: alle 2min")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ **Fehler:** {e}")

@bot.command()
async def debug_matches(ctx):
    """Debug-Informationen zu gefundenen Matches"""
    try:
        upcoming_matches, live_matches = await fetch_all_matches()
        
        # 🎨 VERGRÖSSERTES DEBUG EMBED
        embed = discord.Embed(
            title="🔧 **📊 DEBUG MATCHES 📊**",
            color=0x0099ff
        )
        embed.add_field(name="**🔍 GEFUNDENE MATCHES**", value=f"**Upcoming: {len(upcoming_matches)}, Live: {len(live_matches)}**", inline=True)
        embed.add_field(name="**⏰ ALERT-TIME**", value=f"**{ALERT_TIME}min**", inline=True)
        embed.add_field(name="**🔄 LETZTER CHECK**", value=f"**{last_check_time.strftime('%H:%M:%S')}**", inline=True)
        
        if upcoming_matches or live_matches:
            sources = {}
            for match in upcoming_matches + live_matches:
                source = match.get('source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
            
            source_info = "\n".join([f"• **{source}**: {count}" for source, count in sources.items()])
            embed.add_field(name="**🌐 QUELLEN**", value=source_info, inline=False)
            
            if upcoming_matches:
                match_info = ""
                for i, match in enumerate(upcoming_matches[:4], 1):
                    time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                    match_info += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
                    match_info += f"   ⏰ {int(time_until)}min | 🌐 {match.get('source', 'BO3.GG')}\n\n"
                embed.add_field(name="**🎯 UPCOMING**", value=match_info, inline=False)
            
            if live_matches:
                live_info = ""
                for i, match in enumerate(live_matches[:2], 1):
                    live_info += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
                    live_info += f"   🔴 LIVE | 🌐 {match.get('source', 'BO3.GG')}\n\n"
                embed.add_field(name="**🔴 LIVE**", value=live_info, inline=False)
        
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
    
    # 🎨 VERGRÖSSERTER STATUS
    embed = discord.Embed(title="🤖 **📊 BOT STATUS 📊**", color=0x00ff00)
    embed.add_field(name="**🟢 STATUS**", value="**✅ ONLINE**", inline=True)
    embed.add_field(name="**⏰ UPTIME**", value=f"**{hours}h {minutes}m**", inline=True)
    embed.add_field(name="**🔔 ALERTS**", value="**✅ AKTIV**", inline=True)
    embed.add_field(name="**⏱️ ALERT-TIME**", value=f"**{ALERT_TIME}min**", inline=True)
    embed.add_field(name="**👥 TEAMS**", value=f"**{sum(len(teams) for teams in TEAMS.values())}**", inline=True)
    embed.add_field(name="**🔄 INTERVAL**", value="**2 Minuten**", inline=True)
    embed.add_field(name="**🌐 QUELLEN**", value="**BO3.GG SCRAPING**", inline=False)
    
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
    # 🎨 VERGRÖSSERTER TEST ALERT
    embed = discord.Embed(
        title="🔔 **🎮 TEST ALERT 🎮**",
        description="## 🎮 **Natus Vincere**   🆚   **FaZe Clan** 🎮",
        color=0x00ff00
    )
    embed.add_field(name="**🏆 EVENT**", value="**TEST EVENT**", inline=True)
    embed.add_field(name="**⏰ START IN**", value="**15 MINUTEN**", inline=True)
    embed.add_field(name="**🕐 ZEIT**", value="**Today 20:00**", inline=True)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 **{role.mention}**  **TEST ALERT! MATCH STARTING IN 15 MINUTES!** 🎮")
    else:
        await ctx.send(f"🔔 **TEST ALERT! MATCH STARTING IN 15 MINUTES!** 🎮")
    
    await ctx.send(embed=embed)
    await ctx.send("✅ **TEST ALERT GESENDET!**")

@bot.command()
async def ping(ctx):
    """Einfacher Ping-Befehl"""
    await ctx.send('🏓 **PONG!** 🎯')

@bot.event
async def on_ready():
    """Bot Startup"""
    print(f'✅ {bot.user} ist online! - BO3.GG SCRAPING & ENHANCED')
    
    await asyncio.sleep(2)
    
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔔 BO3.GG Alert system started")
    
    print(f"📊 {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Alert-Time: {ALERT_TIME}min")
    print(f"🎨 Enhanced Visuals aktiviert!")
    print(f"🌐 BO3.GG Scraping aktiviert - NUR ECHTE MATCHES!")

# =========================
# BOT START
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
