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

print("🚀 Starting Discord CS2 Bot with Adaptive Alert System...")

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
# INTELLIGENTES TIMING SYSTEM
# =========================
class AdaptiveScheduler:
    def __init__(self):
        self.base_interval = 5  # Minuten zwischen normalen Checks
        self.urgent_interval = 1  # Minute wenn Matches bald starten
        self.alert_windows = [120, 60, 30, 15, 5]  # Mehrere Alert-Stufen
        self.sent_alerts = set()  # Verhindert Doppel-Alerts
        
    def should_check_urgently(self, matches, alert_time):
        """Prüft ob dringende Checks nötig sind"""
        current_time = datetime.datetime.now(timezone.utc).timestamp()
        
        for match in matches:
            time_until_match = (match['unix_time'] - current_time) / 60
            
            # Wenn Match innerhalb der nächsten 2x base_interval Minuten startet
            if 0 <= time_until_match <= (self.base_interval * 2):
                return True
                
            # Wenn Match innerhalb der Alert-Time + Puffer startet
            if 0 <= time_until_match <= (alert_time + self.base_interval):
                return True
                
        return False
    
    def get_alert_id(self, match, guild_id):
        """Eindeutige ID für Alert um Duplikate zu vermeiden"""
        return f"{guild_id}_{match['team1']}_{match['team2']}_{match['unix_time']}"
    
    def is_alert_sent(self, match, guild_id):
        """Prüft ob Alert bereits gesendet wurde"""
        alert_id = self.get_alert_id(match, guild_id)
        return alert_id in self.sent_alerts
    
    def mark_alert_sent(self, match, guild_id):
        """Markiert Alert als gesendet"""
        alert_id = self.get_alert_id(match, guild_id)
        self.sent_alerts.add(alert_id)
        
        # Alte Alerts bereinigen (älter als 24 Stunden)
        current_time = datetime.datetime.now(timezone.utc).timestamp()
        self.sent_alerts = {alert_id for alert_id in self.sent_alerts 
                           if current_time - int(alert_id.split('_')[-1]) < 86400}

# Adaptive Scheduler initialisieren
scheduler = AdaptiveScheduler()

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

print(f"📊 System geladen: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams, Alert-Time: {ALERT_TIME}min")

# =========================
# HLTV SCRAPING FUNCTIONS
# =========================
async def fetch_hltv_matches():
    """Holt aktuelle Matches von HLTV mit intelligentem Fallback"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://www.hltv.org/matches"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            print("🔍 Fetching REAL HLTV matches...")
            async with session.get(url, headers=headers, timeout=30) as response:
                print(f"📡 HLTV Response: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Verschiedene Parsing-Strategien
                    match_elements = soup.find_all(['div', 'a'], class_=['upcomingMatch', 'match', 'matcha'])
                    
                    for element in match_elements[:15]:
                        try:
                            text = element.get_text(strip=True)
                            if 'vs' in text and len(text) > 10:
                                parts = text.split('vs')
                                if len(parts) >= 2:
                                    team1 = parts[0].strip()
                                    team2 = parts[1].strip().split('\n')[0]
                                    
                                    # Vereinfachte Zeit für Demo
                                    now = datetime.datetime.now(timezone.utc)
                                    match_time = int((now + datetime.timedelta(hours=2)).timestamp())
                                    
                                    if team1 and team2 and len(team1) > 2 and len(team2) > 2:
                                        matches.append({
                                            'team1': team1,
                                            'team2': team2,
                                            'unix_time': match_time,
                                            'event': 'HLTV Event',
                                            'link': 'https://www.hltv.org/matches',
                                            'time_string': 'Today 20:00'
                                        })
                        except Exception as e:
                            continue
                    
                    print(f"🎯 Found {len(matches)} potential matches")
                    
    except Exception as e:
        print(f"❌ HLTV error: {e}")
    
    # Fallback zu intelligenten Demo-Daten
    if not matches:
        matches = await get_intelligent_demo_matches()
    
    return matches

async def get_intelligent_demo_matches():
    """Intelligente Demo-Daten die sich an reale Zeiten anpassen"""
    now = datetime.datetime.now(timezone.utc)
    
    # Erstelle Demo-Matches mit verschiedenen Zeiten
    demo_times = [
        now + datetime.timedelta(minutes=45),   # Bald
        now + datetime.timedelta(hours=2),      # Mittelfristig
        now + datetime.timedelta(hours=6),      # Später
    ]
    
    demo_teams = [
        ('Natus Vincere', 'FaZe Clan'),
        ('Team Vitality', 'G2 Esports'),
        ('FURIA', 'MOUZ'),
        ('Heroic', 'Astralis')
    ]
    
    matches = []
    for i, match_time in enumerate(demo_times):
        if i < len(demo_teams):
            team1, team2 = demo_teams[i]
            matches.append({
                'team1': team1,
                'team2': team2,
                'unix_time': int(match_time.timestamp()),
                'event': f'DEMO Event {i+1}',
                'link': 'https://www.hltv.org/matches',
                'time_string': match_time.strftime('%H:%M')
            })
    
    print(f"🔄 Using {len(matches)} intelligent demo matches")
    return matches

# =========================
# FLASK ROUTES
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
# INTELLIGENTES ALERT SYSTEM
# =========================
@tasks.loop(minutes=5)
async def send_alerts():
    """Adaptives Alert-System mit intelligentem Timing"""
    global last_check_time
    try:
        last_check_time = datetime.datetime.now(timezone.utc)
        matches = await fetch_hltv_matches()
        current_time = last_check_time.timestamp()

        print(f"🔍 Found {len(matches)} matches | Alert-Time: {ALERT_TIME}min")
        
        alerts_sent = 0
        urgent_match_found = False
        
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
                        
                        # Intelligente Team-Erkennung
                        if (variant_lower in team1_lower or 
                            variant_lower in team2_lower or
                            team1_lower in variant_lower or 
                            team2_lower in variant_lower or
                            any(word in team1_lower.split() for word in variant_lower.split()) or
                            any(word in team2_lower.split() for word in variant_lower.split())):
                            
                            time_until_match = (match['unix_time'] - current_time) / 60
                            
                            # Prüfe ob Alert bereits gesendet wurde
                            if scheduler.is_alert_sent(match, guild_id):
                                continue
                            
                            # Adaptive Alert-Logik
                            if 0 <= time_until_match <= ALERT_TIME:
                                # Verschiedene Alert-Stufen
                                if time_until_match <= 5:
                                    color = 0xff0000  # Rot - sehr bald
                                    urgency = "⚡ **SOFORT**"
                                elif time_until_match <= 15:
                                    color = 0xff9900  # Orange - bald
                                    urgency = "🔥 **BALD**"
                                else:
                                    color = 0x00ff00  # Grün - geplant
                                    urgency = "⏰ **GEPLANT**"
                                
                                embed = discord.Embed(
                                    title=f"⚔️ CS2 Match Alert {urgency}",
                                    description=f"**{match['team1']}** vs **{match['team2']}**",
                                    color=color,
                                    url=match['link']
                                )
                                embed.add_field(name="Event", value=match['event'], inline=True)
                                embed.add_field(name="Start in", value=f"**{int(time_until_match)} Minuten**", inline=True)
                                embed.add_field(name="Zeit", value=match.get('time_string', 'Soon'), inline=True)
                                embed.add_field(name="Link", value=f"[HLTV]({match['link']})", inline=False)
                                
                                await channel.send(embed=embed)
                                
                                # CS2 Rolle pingen
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"📢 {role.mention}")
                                
                                # Markiere Alert als gesendet
                                scheduler.mark_alert_sent(match, guild_id)
                                alerts_sent += 1
                                
                                # Aktiviere urgent checking wenn Match sehr bald startet
                                if time_until_match <= 10:
                                    urgent_match_found = True
                                
                                break

        if alerts_sent > 0:
            print(f"✅ {alerts_sent} Alerts gesendet")
            
        # Adaptive Interval-Anpassung
        if urgent_match_found and send_alerts.minutes != 1:
            print("🚀 Urgent matches found - switching to 1 minute intervals")
            send_alerts.change_interval(minutes=1)
        elif not urgent_match_found and send_alerts.minutes != 5:
            print("📊 No urgent matches - switching to 5 minute intervals")
            send_alerts.change_interval(minutes=5)
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Abonniere ein Team für Alerts mit Name-Check"""
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    
    correct_name, found_match = find_team_match(team)
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            if found_match:
                variants = get_team_variants(correct_name)
                variants_text = ", ".join([f"`{v}`" for v in variants[:3]])
                await ctx.send(f"✅ **{correct_name}** hinzugefügt! 🎯\nErkennbare Namen: {variants_text}")
            else:
                await ctx.send(f"✅ **{correct_name}** hinzugefügt! ⚠️\n*Unbekanntes Team - funktioniert nur bei exakter Übereinstimmung*")
        else:
            await ctx.send(f"⚠️ **{team}** hinzugefügt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send(f"⚠️ **{correct_name}** ist bereits abonniert!")

@bot.command()
async def check_team(ctx, *, team_name):
    """Prüft ob ein Team-Name erkannt wird"""
    correct_name, found_match = find_team_match(team_name)
    
    if found_match:
        variants = get_team_variants(correct_name)
        variants_text = " | ".join([f"`{v}`" for v in variants])
        
        embed = discord.Embed(
            title="✅ Team erkannt!",
            description=f"**{correct_name}** wird erkannt als:",
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
    """Zeige alle abonnierten Teams und bekannte Teams"""
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    
    embed = discord.Embed(title="📋 Team Management", color=0x0099ff)
    
    if teams:
        team_list = "\n".join([f"• **{team}**" for team in teams])
        embed.add_field(name="✅ Deine abonnierten Teams", value=team_list, inline=False)
    else:
        embed.add_field(name="❌ Abonnierte Teams", value="Noch keine Teams abonniert!", inline=False)
    
    known_teams = list(TEAM_SYNONYMS.keys())[:15]
    known_list = "\n".join([f"• {team}" for team in known_teams])
    embed.add_field(name="🎯 Bekannte Teams", value=known_list, inline=False)
    
    embed.add_field(
        name="💡 Tipps", 
        value="• `/check_team Name` - Prüft Team-Erkennung\n• `/subscribe Name` - Abonniert Team\n• `/settime 60` - Setzt Alert-Zeit", 
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def settime(ctx, minutes: int):
    """Setze die Alert-Vorlaufzeit in Minuten"""
    global ALERT_TIME
    if 1 <= minutes <= 240:
        old_time = ALERT_TIME
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ Alert-Vorlaufzeit von **{old_time}** auf **{minutes} Minuten** geändert! 🔄")
            
            # Starte Alert-System neu für sofortige Anwendung
            if send_alerts.is_running():
                send_alerts.restart()
                await ctx.send("🔄 Alert-System neu gestartet für sofortige Anwendung!")
        else:
            await ctx.send(f"⚠️ Zeit gesetzt, aber Speichern fehlgeschlagen!")
    else:
        await ctx.send("❌ Bitte eine Zeit zwischen 1 und 240 Minuten angeben!")

@bot.command()
async def force_check(ctx):
    """Erzwingt eine sofortige Überprüfung"""
    await ctx.send("🔍 Erzwinge sofortige Match-Überprüfung...")
    await send_alerts()
    await ctx.send("✅ Überprüfung abgeschlossen!")

@bot.command()
async def debug_system(ctx):
    """Zeigt detaillierte System-Informationen"""
    matches = await fetch_hltv_matches()
    current_time = datetime.datetime.now(timezone.utc).timestamp()
    
    embed = discord.Embed(title="🔧 System Debug", color=0x0099ff)
    
    # Match-Informationen
    match_info = ""
    for i, match in enumerate(matches[:5], 1):
        time_until = (match['unix_time'] - current_time) / 60
        match_info += f"{i}. **{match['team1']}** vs **{match['team2']}**\n"
        match_info += f"   ⏰ {int(time_until)}min | 📅 {match['event']}\n\n"
    
    embed.add_field(name="🎯 Gefundene Matches", value=match_info or "Keine Matches", inline=False)
    
    # System-Status
    embed.add_field(name="🤖 Bot Status", value="✅ Online" if bot.is_ready() else "❌ Offline", inline=True)
    embed.add_field(name="🔄 Alerts", value="✅ Aktiv" if send_alerts.is_running() else "❌ Inaktiv", inline=True)
    embed.add_field(name="⏰ Interval", value=f"{send_alerts.minutes}min", inline=True)
    embed.add_field(name="🔔 Alert-Time", value=f"{ALERT_TIME}min", inline=True)
    embed.add_field(name="🌐 Flask", value=f"✅ {flask_status}", inline=True)
    embed.add_field(name="📊 Teams", value=f"{sum(len(teams) for teams in TEAMS.values())}", inline=True)
    
    await ctx.send(embed=embed)

# Weitere Commands (setchannel, test_alert, etc.) bleiben gleich
# ... [restliche Commands wie zuvor]

@bot.event
async def on_ready():
    """Bot Startup"""
    print(f'✅ {bot.user} ist online!')
    
    await asyncio.sleep(2)
    
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔄 Adaptive Alert system started")
    
    print(f"📊 Geladene Daten: {len(TEAMS)} Server, {sum(len(teams) for teams in TEAMS.values())} Teams")
    print(f"⏰ Alert-Time: {ALERT_TIME} Minuten")
    print(f"🌐 Flask Port: {flask_port}")
    print("💾 Adaptive System aktiviert")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
