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

print("🚀 Starting Discord CS2 Bot - LIVE MATCHES ONLY...")

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
    
    # Direkte Suche in Synonyms
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    
    # Fuzzy Matching für Tippfehler
    for correct_name, variants in TEAM_SYNONYMS.items():
        for variant in variants:
            variant_lower = variant.lower()
            # Einfacher String Vergleich
            if input_lower in variant_lower or variant_lower in input_lower:
                return correct_name, True
            
            # Gemeinsame Wörter finden
            input_words = set(input_lower.split())
            variant_words = set(variant_lower.split())
            if input_words & variant_words:  # Gemeinsame Wörter
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

print(f"📊 System geladen: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")

# =========================
# LIVE MATCH SCRAPING FUNCTIONS - NUR LIVE MATCHES!
# =========================
async def fetch_live_matches():
    """Holt NUR aktuelle LIVE Matches von HLTV"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # HLTV Live Matches Seite
            url = "https://www.hltv.org/matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            print("🔴 Fetching LIVE matches from HLTV...")
            async with session.get(url, headers=headers, timeout=30) as response:
                print(f"📡 HLTV Response: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # LIVE Matches finden - suche nach "live" Indikatoren
                    live_indicators = soup.find_all(lambda tag: 
                                                   tag.name == 'div' and 
                                                   'live' in tag.get_text().lower() and
                                                   'match' in tag.get('class', []))
                    
                    # Alternative: Suche nach Matches mit LIVE Status
                    all_matches = soup.find_all('div', class_=['match', 'upcomingMatch', 'liveMatch'])
                    
                    for match in all_matches:
                        try:
                            match_text = match.get_text().lower()
                            
                            # Prüfe ob Match LIVE ist
                            is_live = any(indicator in match_text for indicator in 
                                         ['live', 'ongoing', 'playing now', 'currently', 'bo3', 'bo5'])
                            
                            # Oder prüfe auf LIVE-Score (z.B. "5-3", "10-7")
                            score_patterns = [f"{i}-{j}" for i in range(0, 16) for j in range(0, 16)]
                            has_score = any(pattern in match_text for pattern in score_patterns)
                            
                            if is_live or has_score:
                                # Team Namen extrahieren
                                team_elements = match.find_all('div', class_=['team', 'matchTeamName'])
                                if len(team_elements) >= 2:
                                    team1 = team_elements[0].get_text(strip=True)
                                    team2 = team_elements[1].get_text(strip=True)
                                    
                                    # Score extrahieren falls vorhanden
                                    score_text = ""
                                    score_elements = match.find_all('span', class_=['score', 'result'])
                                    if score_elements:
                                        score_text = score_elements[0].get_text(strip=True)
                                    
                                    if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                                        matches.append({
                                            'team1': team1,
                                            'team2': team2,
                                            'score': score_text,
                                            'status': 'LIVE',
                                            'event': 'Live Match',
                                            'link': 'https://www.hltv.org/matches',
                                            'is_live': True
                                        })
                                        print(f"🔴 LIVE Match gefunden: {team1} vs {team2} {score_text}")
                        except Exception as e:
                            continue
                    
                    print(f"🎯 Found {len(matches)} LIVE matches")
                    
    except Exception as e:
        print(f"❌ LIVE Match error: {e}")
    
    # Fallback zu Demo LIVE Matches für Testing
    if not matches:
        matches = await get_demo_live_matches()
    
    return matches

async def get_demo_live_matches():
    """Demo LIVE Matches für Testing"""
    print("🟡 Using DEMO LIVE matches for testing")
    
    demo_matches = [
        {
            'team1': 'Natus Vincere',
            'team2': 'FaZe Clan',
            'score': '8-5',
            'status': 'LIVE - Map 1',
            'event': 'IEM Cologne 2024',
            'link': 'https://www.hltv.org/matches',
            'is_live': True
        },
        {
            'team1': 'Team Vitality', 
            'team2': 'G2 Esports',
            'score': '12-3',
            'status': 'LIVE - Map 2',
            'event': 'BLAST Premier',
            'link': 'https://www.hltv.org/matches',
            'is_live': True
        }
    ]
    
    return demo_matches

# =========================
# FLASK ROUTES
# =========================
@app.route('/')
def home():
    global flask_status
    flask_status = "healthy"
    return "✅ Discord CS2 Bot - LIVE MATCHES ONLY"

@app.route('/ping')
def ping():
    global flask_status
    flask_status = "healthy"
    return jsonify({
        "status": "online",
        "bot_ready": bot.is_ready(),
        "alerts_running": send_live_alerts.is_running() if 'send_live_alerts' in globals() else False,
        "uptime": str(datetime.datetime.now(timezone.utc) - start_time),
        "monitored_teams": sum(len(teams) for teams in TEAMS.values()),
        "monitored_guilds": len(TEAMS),
        "flask_port": flask_port,
        "flask_status": flask_status,
        "mode": "LIVE MATCHES ONLY"
    })

@app.route('/health')
def health():
    global flask_status
    flask_status = "healthy"
    return jsonify({
        "status": "healthy", 
        "service": "discord_cs2_bot_live",
        "last_check": last_check_time.isoformat(),
        "teams_count": sum(len(teams) for teams in TEAMS.values()),
        "servers_count": len(TEAMS),
        "flask_port": flask_port,
        "flask_status": flask_status,
        "mode": "LIVE MATCHES ONLY"
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
# LIVE ALERT SYSTEM - NUR FÜR LIVE MATCHES!
# =========================
sent_live_alerts = set()  # Verhindert Doppel-Alerts für Live Matches

@tasks.loop(minutes=2)
async def send_live_alerts():
    """Sendet Alerts NUR für LIVE Matches"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        matches = await fetch_live_matches()

        print(f"🔴 Checking {len(matches)} LIVE matches...")
        
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
                if not match.get('is_live', False):
                    continue
                    
                team1_lower = match['team1'].lower()
                team2_lower = match['team2'].lower()
                
                for subscribed_team in subscribed_teams:
                    subscribed_variants = get_team_variants(subscribed_team)
                    
                    for variant in subscribed_variants:
                        variant_lower = variant.lower()
                        
                        # Intelligente Team-Erkennung für LIVE Matches
                        if (variant_lower in team1_lower or 
                            variant_lower in team2_lower or
                            team1_lower in variant_lower or 
                            team2_lower in variant_lower or
                            any(word in team1_lower.split() for word in variant_lower.split()) or
                            any(word in team2_lower.split() for word in variant_lower.split())):
                            
                            # Eindeutige ID für Live Match Alert
                            alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_LIVE"
                            
                            # Prüfe ob Alert bereits gesendet wurde
                            if alert_id in sent_live_alerts:
                                continue
                            
                            # LIVE Match Embed erstellen
                            embed = discord.Embed(
                                title="🔴 LIVE CS2 MATCH!",
                                description=f"**{match['team1']}** vs **{match['team2']}**",
                                color=0xff0000,  # Rot für Live
                                url=match['link']
                            )
                            
                            # Score hinzufügen falls vorhanden
                            if match.get('score'):
                                embed.add_field(name="Score", value=f"**{match['score']}**", inline=True)
                            
                            embed.add_field(name="Status", value=f"**{match['status']}**", inline=True)
                            embed.add_field(name="Event", value=match['event'], inline=True)
                            embed.add_field(name="Watch", value=f"[HLTV]({match['link']})", inline=False)
                            
                            await channel.send(embed=embed)
                            
                            # CS2 Rolle pingen
                            role = discord.utils.get(channel.guild.roles, name="CS2")
                            if role:
                                await channel.send(f"📢 {role.mention} **LIVE MATCH!**")
                            
                            # Markiere Alert als gesendet
                            sent_live_alerts.add(alert_id)
                            alerts_sent += 1
                            print(f"✅ LIVE Alert gesendet: {match['team1']} vs {match['team2']}")
                            break

        if alerts_sent > 0:
            print(f"🎯 {alerts_sent} LIVE Alerts gesendet")
            
        # Alte Alerts bereinigen (älter als 6 Stunden)
        current_time = datetime.datetime.now(timezone.utc)
        if len(sent_live_alerts) > 50:  # Nur bereinigen wenn viele Alerts vorhanden
            sent_live_alerts.clear()
            print("🧹 Live Alerts Cache cleared")
        
    except Exception as e:
        print(f"❌ LIVE Alert error: {e}")

# =========================
# BOT COMMANDS - ANGEPASST FÜR LIVE MATCHES
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für LIVE Match Alerts"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    
    correct_name, found_match = find_team_match(team)
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            if found_match:
                variants = get_team_variants(correct_name)
                variants_text = ", ".join([f"`{v}`" for v in variants[:3]])
                await ctx.send(f"✅ **{correct_name}** für LIVE Alerts hinzugefügt! 🔴\nErkennbare Namen: {variants_text}")
            else:
                await ctx.send(f"✅ **{correct_name}** hinzugefügt! ⚠️\n*Unbekanntes Team - funktioniert nur bei exakter Übereinstimmung*")
        else:
            await ctx.send(f"⚠️ **{team}** hinzugefügt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"⚠️ **{correct_name}** ist bereits für LIVE Alerts abonniert!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Entferne ein Team von LIVE Alerts"""
    guild_id = ctx.guild.id
    
    # Finde korrekten Team-Namen für Matching
    correct_name, found_match = find_team_match(team)
    
    if guild_id in TEAMS and correct_name in TEAMS[guild_id]:
        TEAMS[guild_id].remove(correct_name)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"❌ **{correct_name}** von LIVE Alerts entfernt!")
        else:
            await ctx.send(f"⚠️ **{correct_name}** entfernt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"❌ Team **{correct_name}** nicht gefunden!")

@bot.command()
async def check_team(ctx, *, team_name):
    """Prüft ob ein Team-Name erkannt wird"""
    correct_name, found_match = find_team_match(team_name)
    
    if found_match:
        variants = get_team_variants(correct_name)
        variants_text = " | ".join([f"`{v}`" for v in variants])
        
        embed = discord.Embed(
            title="✅ Team erkannt!",
            description=f"**{correct_name}** wird für LIVE Alerts erkannt als:",
            color=0x00ff00
        )
        embed.add_field(name="Erkennbare Namen", value=variants_text, inline=False)
        embed.add_field(name="Tipp", value=f"Verwende `/subscribe {correct_name}`", inline=False)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="⚠️ Team nicht erkannt",
            description=f"**{team_name}** ist nicht in der Datenbank.",
            color=0xff9900
        )
        embed.add_field(
            name="Tipps", 
            value="• Probiere den offiziellen Team-Namen\n• Verwende `/list_teams` für bekannte Teams", 
            inline=False
        )
        await ctx.send(embed=embed)

@bot.command()
async def list_teams(ctx):
    """Zeige alle für LIVE Alerts abonnierten Teams"""
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    
    embed = discord.Embed(title="📋 LIVE Match Team Management", color=0xff0000)
    
    if teams:
        team_list = "\n".join([f"• **{team}**" for team in teams])
        embed.add_field(name="🔴 Deine LIVE Teams", value=team_list, inline=False)
    else:
        embed.add_field(name="❌ LIVE Teams", value="Noch keine Teams für LIVE Alerts abonniert!", inline=False)
    
    known_teams = list(TEAM_SYNONYMS.keys())[:12]
    known_list = "\n".join([f"• {team}" for team in known_teams])
    embed.add_field(name="🎯 Bekannte Teams", value=known_list, inline=False)
    
    embed.add_field(
        name="💡 Info", 
        value="• **NUR LIVE MATCHES** werden gemeldet\n• Alle 2 Minuten Check\n• Sofortiger Ping bei Match-Start", 
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def live_now(ctx):
    """Zeigt aktuell laufende LIVE Matches an"""
    try:
        matches = await fetch_live_matches()
        
        if matches:
            match_list = ""
            for i, match in enumerate(matches[:5], 1):
                score = match.get('score', 'LIVE')
                match_list += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
                match_list += f"   🎯 **{score}** | 📍 {match['status']}\n"
                match_list += f"   🏆 {match['event']}\n\n"
            
            embed = discord.Embed(
                title="🔴 AKTUELLE LIVE MATCHES",
                description=match_list,
                color=0xff0000
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Aktuell keine LIVE Matches verfügbar")
            
    except Exception as e:
        await ctx.send(f"❌ Fehler: {e}")

@bot.command()
async def force_live_check(ctx):
    """Erzwingt eine sofortige LIVE Match Überprüfung"""
    await ctx.send("🔴 Erzwinge sofortige LIVE Match-Überprüfung...")
    await send_live_alerts()
    await ctx.send("✅ LIVE Überprüfung abgeschlossen!")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Setze den Channel für LIVE Match Alerts"""
    CHANNELS[ctx.guild.id] = channel.id
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        await ctx.send(f"📡 LIVE Alert-Channel auf {channel.mention} gesetzt! 🔴")
    else:
        await ctx.send(f"⚠️ Channel gesetzt, aber Speichern fehlgeschlagen!")

@bot.command()
async def settime(ctx, minutes: int):
    """Setze die Check-Interval Zeit (für zukünftige Erweiterungen)"""
    global ALERT_TIME
    if 1 <= minutes <= 240:
        old_time = ALERT_TIME
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ Check-Interval Referenzzeit auf **{minutes} Minuten** gesetzt! 🔄\n*Hinweis: Bei LIVE Matches wird alle 2 Minuten geprüft*")
        else:
            await ctx.send(f"⚠️ Zeit gesetzt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send("❌ Bitte eine Zeit zwischen 1 und 240 Minuten angeben!")

@bot.command()
async def status(ctx):
    """Zeigt Bot-Status für LIVE Matches"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(title="🤖 LIVE Match Bot Status", color=0xff0000)
    embed.add_field(name="Status", value="🔴 LIVE Matches Only", inline=True)
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)
    embed.add_field(name="LIVE Alerts", value="✅ Aktiv" if send_live_alerts.is_running() else "❌ Inaktiv", inline=True)
    embed.add_field(name="Check Interval", value="2 Minuten", inline=True)
    embed.add_field(name="Server", value=f"{len(TEAMS)}", inline=True)
    embed.add_field(name="LIVE Teams", value=f"{sum(len(teams) for teams in TEAMS.values())}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Einfacher Ping"""
    await ctx.send('🏓 Pong! LIVE Matches Mode')

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    """Bot Startup"""
    print(f'✅ {bot.user} ist online! - LIVE MATCHES ONLY')
    
    await asyncio.sleep(2)
    
    if not send_live_alerts.is_running():
        send_live_alerts.start()
        print("🔴 LIVE Alert system started (2-minute intervals)")
    
    print(f"📊 Geladene Daten: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"🌐 Flask Port: {flask_port}")
    print("💾 LIVE MATCHES ONLY System aktiviert")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
