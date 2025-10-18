import os
import discord
from discord.ext import commands, tasks
import datetime
from datetime import timezone, timedelta
import json
import asyncio
from flask import Flask, jsonify
import threading
import aiohttp
import re

print("🚀 Starting Discord CS2 Bot - GRID.GG API + TWITCH")

# =========================
# BOT SETUP
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents, case_insensitive=True)

# NEU: Setup Hook für persistente Buttons
@bot.event
async def setup_hook():
    print("✅ Persistent buttons setup!")

# =========================
# CONFIGURATION FROM ENVIRONMENT
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET") 
GRID_API_KEY = os.getenv("GRID_API_KEY")
TWITCH_USERNAME = "shiseii"
ANNOUNCEMENT_CHANNEL_ID = 1162297673920024667
MATCH_ALERT_CHANNEL_ID = 1427554150824284160  # Für Match Alerts & alles andere

# =========================
# AUTO-SUBSCRIBE TEAMS
# =========================
AUTO_SUBSCRIBE_TEAMS = [
    'Falcons', 'MOUZ', 'Team Spirit', 'Team Vitality', 'The Mongolz',
    'FURIA', 'Natus Vincere', 'FaZe', '3DMAX', 'Astralis', 
    'G2', 'Aurora', 'Liquid', 'M80'
]

# Check ob alle Tokens vorhanden sind
required_tokens = {
    "DISCORD_TOKEN": DISCORD_TOKEN,
    "GRID_API_KEY": GRID_API_KEY,
    "TWITCH_CLIENT_ID": TWITCH_CLIENT_ID,
    "TWITCH_CLIENT_SECRET": TWITCH_CLIENT_SECRET
}

for name, token in required_tokens.items():
    if not token:
        print(f"❌ {name} fehlt in Environment Variables!")
        exit(1)

print("✅ Alle Tokens erfolgreich geladen!")

# Team Display Names mit korrekten Emoji-IDs
TEAM_DISPLAY_NAMES = {
    # MAIN TEAMS MIT LOGOS:
    'Falcons': '<:falcons:1428075105615085598> FALCONS',
    'MOUZ': '<:mouz:1428075167850041425> MOUZ',
    'Team Spirit': '<:spirit:1428075208564019302> TEAM SPIRIT',
    'Team Vitality': '<:vitality:1428075243510956113> TEAM VITALITY',
    'The Mongolz': '<:themongolz:1428075231939133581> THE MONGOLZ',
    'TheMongolz': '<:themongolz:1428075231939133581> THE MONGOLZ',
    'FURIA': '<:furia:1428075132156641471> FURIA',
    'Natus Vincere': '<:navi:1428075186976194691> NATUS VINCERE',
    'FaZe': '<:faze:1428075117753401414> FAZE',
    '3DMAX': '<:3dmax:1428075077408133262> 3DMAX',
    'Astralis': '<:astralis:1428075043526672394> ASTRALIS',
    'G2': '<:g2:1428075144240431154> G2',
    'Aurora': '<:aurora:1428075062287798272> AURORA',
    'AURORA': '<:aurora:1428075062287798272> AURORA',
    'Liquid': '<:liquid:1428075155456000122> LIQUID',
    'M80': '<:m80:1428076593028530236> M80',
    'ENCE': 'ENCE',
    'BIG': 'BIG',
    'Wildcard': 'WILDCARD',
    'Sangal': 'SANGAL',
    'RED Canids': 'RED CANIDS',
    
    # ACADEMY TEAMS OHNE LOGOS:
    'Falcons Force': 'FALCONS FORCE',
    'NAVI Junior': 'NAVI JUNIOR',
    'Spirit Academy': 'SPIRIT ACADEMY',
    'BIG Academy': 'BIG ACADEMY',
    'Wildcard Academy': 'WILDCARD ACADEMY',
    'MIBR Academy': 'MIBR ACADEMY',
    'Young Ninjas': 'YOUNG NINJAS',
    'ENCE Academy': 'ENCE ACADEMY',
    'ODDIK Academy': 'ODDIK ACADEMY',
    '3DMAX Academy': '3DMAX ACADEMY',
    'Sangal Academy': 'SANGAL ACADEMY',
    'RED Canids Academy': 'RED CANIDS ACADEMY',
    
    # FEMALE TEAMS OHNE LOGOS:
    'MIBR fe': 'MIBR FE',
    'FURIA fe': 'FURIA FE',
    'NIP Impact': 'NIP IMPACT',
    'Flame Sharks fe': 'FLAME SHARKS FE',
    'Imperial Valkyries': 'IMPERIAL VALKYRIES',
    'n!faculty female': 'N!FACULTY FEMALE',
    
    # RESTLICHE TEAMS:
    'B8': '<:b8:1428264645042503761> B8',
    'BetBoom': '<:betboom:1428264669533048932> BETBOOM',
    'Complexity': '<:complexity:1428264681222439023> COMPLEXITY',
    'FlyQuest': '<:flyquest:1428264694795472896> FLYQUEST',
    'Fnatic': '<:fnatic:1428265467201458289> FNATIC',
    'GamerLegion': '<:gamerlegion:1428264709613686865> GAMERLEGION',
    'Heroic': '<:heroic:1428264721269915668> HEROIC',
    'Imperial': '<:imperial:1428264741532602399> IMPERIAL',
    'Lynn Vision': '<:lynnvision:1428264754064916510> LYNN VISION',
    'MIBR': '<:mibr:1428264767784751226> MIBR',
    'Ninjas in Pyjamas': '<:nip:1428264779507830824> NINJAS IN PYJAMAS',
    'paiN': '<:pain:1428264796012417077> PAIN',
    'SAW': '<:saw:1428264807496417341> SAW',
    'TYLOO': '<:tyloo:1428264914367021198> TYLOO',
    'Virtus.pro': '<:virtuspro:1428266203474034748> VIRTUS.PRO',
    'Legacy': '<:legacy:1428269690001821766> LEGACY',
    
    'TEAM NOVAQ': 'TEAM NOVAQ',
    'GENONE': 'GENONE',
    'FISH123': 'FISH123',
    'ARCRED': 'ARCRED',
    'KONO.ECF': 'KONO.ECF',
    'AM GAMING': 'AM GAMING',
    'MASONIC': 'MASONIC',
    'MINDFREAK': 'MINDFREAK',
    'ROOSTER': 'ROOSTER'
}

# =========================
# TEAM DATA
# =========================
TEAM_SYNONYMS = {
    # MAIN TEAMS:
    'Natus Vincere': ['navi'],
    'FaZe': ['faze', 'faze clan'], 
    'Team Vitality': ['vitality'],
    'G2': ['g2'],
    'MOUZ': ['mouz'],
    'Team Spirit': ['spirit'],
    'FURIA': ['furia'],
    'Falcons': ['falcons'],
    'Astralis': ['astralis'],
    'Aurora': ['aurora'],
    'Liquid': ['liquid'],
    'M80': ['m80'],
    'ENCE': ['ence'],
    'Complexity': ['complexity', 'col'],
    'Heroic': ['heroic'],
    'Fnatic': ['fnatic'],
    'Virtus.pro': ['virtus pro', 'vp'],
    'Ninjas in Pyjamas': ['nip', 'ninjas in pyjamas'],
    'paiN': ['pain'],
    'Legacy': ['legacy'],
    
    # ACADEMY TEAMS:
    'Falcons Force': ['falcons force', 'falcons academy'],
    'NAVI Junior': ['navi junior', 'navi jr', 'navi academy'],
    'Spirit Academy': ['spirit academy', 'spirit jr'],
    'BIG Academy': ['big academy', 'big jr'],
    'Wildcard Academy': ['wildcard academy', 'wildcard jr'],
    'MIBR Academy': ['mibr academy', 'mibr youth', 'mibr jr'],
    'Young Ninjas': ['young ninjas', 'nip academy', 'ninjas academy'],
    'ENCE Academy': ['ence academy', 'ence jr'],
    'ODDIK Academy': ['oddik academy', 'oddik jr'],
    '3DMAX Academy': ['3dmax academy', '3dmax jr'],
    'Sangal Academy': ['sangal academy', 'sangal jr'],
    'RED Canids Academy': ['red canids academy', 'red canids jr'],
    
    # FEMALE TEAMS:
    'MIBR fe': ['mibr fe', 'mibr female', 'mibr women'],
    'FURIA fe': ['furia fe', 'furia female', 'furia women'],
    'NIP Impact': ['nip impact', 'nip female', 'nip fe'],
    'Flame Sharks fe': ['flame sharks fe', 'flame sharks female'],
    'Imperial Valkyries': ['imperial valkyries', 'imperial female'],
    'n!faculty female': ['n faculty female', 'n!faculty fe']
}

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    
    # 1. Zuerst in TEAM_SYNONYMS suchen
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants]:
            return correct_name, True
    
    # 2. Dann in TEAM_DISPLAY_NAMES suchen (NUR EXAKTE MATCHES)
    for team_name in TEAM_DISPLAY_NAMES.keys():
        if input_lower == team_name.lower():
            return team_name, True
    
    # 3. Wenn nicht gefunden, Team TROTZDEM verwenden
    return input_team, True

def get_display_name(team_name, use_smart_lookup=True):
    """Get team name with emoji for display
    use_smart_lookup=True: Für subscribe/list (intelligente Zuordnung)
    use_smart_lookup=False: Für matches/alerts (exakte Anzeige)
    """
    
    if not use_smart_lookup:
        # FÜR MATCHES/ALERTS: Case-insensitive Suche
        team_name_lower = team_name.lower()
        for display_name, display_value in TEAM_DISPLAY_NAMES.items():
            if display_name.lower() == team_name_lower:
                return display_value
        # Falls nicht gefunden, normal anzeigen
        return f"{team_name.upper()}"
    
    # FÜR SUBSCRIBE/LIST: Intelligente Zuordnung (bestehender Code)
    if team_name in TEAM_DISPLAY_NAMES:
        return TEAM_DISPLAY_NAMES[team_name]
    
    # NEU: Nur exakte Matches für intelligente Zuordnung
    return TEAM_DISPLAY_NAMES.get(team_name, f"{team_name.upper()}")

# =========================
# EMBED FUNKTIONEN
# =========================
def create_match_alert(match, time_until):
    team1_display = get_display_name(match['team1'], use_smart_lookup=False)
    team2_display = get_display_name(match['team2'], use_smart_lookup=False)
    
    embed = discord.Embed(
        title=f"CS2 MATCH ALERT{'\u2800' * 25}<:cs2:1298250987483697202>",
        description=f"# {team1_display}\n# <:VS:1428145739443208305>\n# {team2_display}\n",
        color=0x00ff00 if time_until > 15 else 0xff9900,
        timestamp=datetime.datetime.now()
    )
    
    # 2 ABSÄTZE über Tournament
    embed.add_field(name="", value="", inline=False)
    embed.add_field(name="", value="", inline=False)
    
    # Zeile 1: "Tournament" und "🕐 Time 16:30" in einer Zeile (rechtsbündig)
    header_line = f"🏆 Tournament{'\u2800' * 25}🕐 Time {match['time_string']}"
    
    # Zeile 2: Nur Tournament-Name
    content_line = f"{match['event']}"
    
    # Beide Zeilen in einem Field
    embed.add_field(name=header_line, value=content_line, inline=False)
    embed.add_field(name="", value="", inline=False)
    embed.add_field(name="⏰ Starts in", value=f"**{int(time_until)} minutes**", inline=False)
    embed.add_field(name="", value="", inline=False)
    embed.add_field(name="📺 Stream Tip", value="[shiseii on Twitch](https://twitch.tv/shiseii)", inline=False)
    embed.set_footer(text="🎮 CS2 Match Bot • Have fun!")
    
    return embed

def create_twitch_go_live_alert():
    """Erstellt das Twitch Go-Live Embed für automatische Posts"""
    
    embed = discord.Embed(
        color=0x9146FF,
        timestamp=datetime.datetime.now()
    )
    
    # ZEILE 1: TWITCH LIVE ALERT als klickbarer Link
    embed.add_field(
        name="",
        value="**[TWITCH LIVE ALERT](https://twitch.tv/shiseii)**",
        inline=False
    )
    
    embed.add_field(name="", value="", inline=False)
    
    # Stream Info über dem Banner
    embed.add_field(
        name="🔴 shiseii is now live on Twitch!",
        value="**[🌐 CLICK HERE TO WATCH LIVE](https://twitch.tv/shiseii)**",
        inline=False
    )
    
    embed.add_field(name="", value="", inline=False)
    
    # Titel
    embed.add_field(
        name="📺 LIVE WITH SHISEII",
        value="",
        inline=False
    )
    
    # Game ohne "🕐 LIVE"
    embed.add_field(
        name="🎮 Just Chatting",
        value="",
        inline=False
    )
    
    # ✅ NUR EIN ABSATZ bis zum Banner
    embed.add_field(name="", value="", inline=False)
    
    # LIVE-Banner
    embed.set_image(url="https://i.ibb.co/6cQh6FjN/LIVE.png")
    
    # Profilbild oben rechts (Thumbnail)
    embed.set_thumbnail(url="https://static-cdn.jtvnw.net/jtv_user_pictures/8b4104f3-43d0-4d7e-a7ae-bd15408acad4-profile_image-70x70.png")
    
    embed.set_footer(text="🎮 CS2 Match Bot • Have fun!")
    
    return embed

# =========================
# DATA MANAGEMENT
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded data from {DATA_FILE}")
                return data
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
    except:
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Save error: {e}")
        return False

# Load initial data
data = load_data()
TEAMS = data.get("TEAMS", {})
CHANNELS = data.get("CHANNELS", {})
ALERT_TIME = data.get("ALERT_TIME", 30)

print(f"📊 Loaded: {len(TEAMS)} servers")

# =========================
# GRID.GG API
# =========================
async def fetch_grid_matches():
    matches = []
    try:
        async with aiohttp.ClientSession() as session:
            central_url = "https://api-op.grid.gg/central-data/graphql"
            headers = {
                'x-api-key': GRID_API_KEY,
                'Content-Type': 'application/json'
            }
            
            # Zeitfilter für heute + 1 Tag IN UTC
            now_utc = datetime.datetime.now(timezone.utc)
            start_time = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_time = (now_utc + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            series_list_query = {
                "query": """
                query GetAllSeries {
                  allSeries(
                    filter: {
                      startTimeScheduled: {
                        gte: "%s"
                        lte: "%s"
                      }
                    }
                    orderBy: StartTimeScheduled
                    first: 50
                  ) {
                    edges {
                      node {
                        id
                        tournament {
                          nameShortened
                        }
                        startTimeScheduled
                        title {
                          nameShortened
                        }
                        teams {
                          baseInfo {
                            name
                          }
                        }
                      }
                    }
                  }
                }
                """ % (start_time, end_time)
            }
            
            print(f"🔍 Hole Series von {start_time} bis {end_time}")
            
            async with session.post(central_url, headers=headers, json=series_list_query, timeout=15) as response:
                if response.status == 200:
                    central_data = await response.json()
                    
                    if central_data.get('errors'):
                        print(f"❌ Central Data Error: {central_data['errors']}")
                        return []
                    
                    series_edges = central_data.get('data', {}).get('allSeries', {}).get('edges', [])
                    print(f"✅ Gefundene Series: {len(series_edges)}")
                    
                    # ✅ EXPLIZITE TIMEZONE FÜR ALLE BERECHNUNGEN
                    german_tz = timezone(timedelta(hours=2))
                    current_time_utc = datetime.datetime.now(timezone.utc)
                    
                    for edge in series_edges:
                        try:
                            series_node = edge.get('node', {})
                            
                            # NUR CS2 MATCHES FILTERN
                            title = series_node.get('title', {}).get('nameShortened', '')
                            if title != 'cs2':
                                continue
                            
                            # Teams aus Central Data
                            teams = series_node.get('teams', [])
                            if len(teams) < 2:
                                continue
                                
                            team1_name = teams[0].get('baseInfo', {}).get('name', 'TBD')
                            team2_name = teams[1].get('baseInfo', {}).get('name', 'TBD')
                            
                            # Startzeit verwenden - ✅ ALS UTC INTERPRETIEREN
                            start_time_str = series_node.get('startTimeScheduled')
                            if start_time_str:
                                # Grid.gg liefert UTC Zeit - direkt verwenden
                                match_dt_utc = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                                
                                # ✅ KORREKTE TIME_UNTIL BERECHNUNG: UTC vs UTC
                                time_diff = (match_dt_utc - current_time_utc).total_seconds() / 60
                                
                                # Nur zukünftige Matches (oder max. 2 Stunden vergangen)
                                if time_diff >= -120:
                                    
                                    # ✅ Local Time für Display
                                    match_dt_local = match_dt_utc.astimezone(german_tz)
                                    time_string = match_dt_local.strftime("%H:%M")
                                    
                                    event = series_node.get('tournament', {}).get('nameShortened', 'CS2 Match')
                                    
                                    matches.append({
                                        'team1': team1_name, 
                                        'team2': team2_name, 
                                        'unix_time': int(match_dt_utc.timestamp()),  # ✅ UTC Timestamp
                                        'event': event, 
                                        'time_string': time_string  # ✅ Local Time Display
                                    })
                        except Exception as e:
                            print(f"❌ Series error: {e}")
                            continue
                    
                    matches.sort(key=lambda x: x['unix_time'])
                    print(f"✅ Verfügbare CS2 Matches: {len(matches)}")
                    return matches
                else:
                    print(f"❌ Central Data API error: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Grid.gg API connection error: {e}")
        return []

# =========================
# ALERT SYSTEM - KORRIGIERT
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    try:
        matches = await fetch_grid_matches()
        current_time = datetime.datetime.now(timezone.utc).timestamp()
        
        for guild_id, subscribed_teams in TEAMS.items():
            if not subscribed_teams:
                continue
                
            # ✅ KORRIGIERT: Immer den festen Channel verwenden
            channel_id = MATCH_ALERT_CHANNEL_ID

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            for match in matches:
                for subscribed_team in subscribed_teams:
                    correct_name, found = find_team_match(subscribed_team)
                    team_variants = [correct_name.lower()] + [v.lower() for v in TEAM_SYNONYMS.get(correct_name, [])]
                    
                    if (match['team1'].lower() in team_variants or 
                        match['team2'].lower() in team_variants):
                        
                        time_until = (match['unix_time'] - current_time) / 60
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}"
                        
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            # NEUES EMBED DESIGN VERWENDEN
                            embed = create_match_alert(match, time_until)
                            
                            try:
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 {role.mention}", embed=embed)
                                else:
                                    await channel.send(embed=embed)
                                
                                sent_alerts.add(alert_id)
                                if len(sent_alerts) > 50:
                                    sent_alerts.clear()
                                    
                            except Exception as e:
                                print(f"❌ Send error: {e}")
                            break
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# DAILY DM REMINDER
# =========================
@tasks.loop(time=datetime.time(hour=10, minute=30, tzinfo=timezone.utc))
async def daily_dm_reminder():
    """Sendet tägliche Erinnerung an alle User die /notifications aktiviert haben"""
    try:
        user_ids = [123456789, 987654321]  # ← Durch echte User-IDs ersetzen
        
        for user_id in user_ids:
            try:
                user = await bot.fetch_user(user_id)
                
                embed = discord.Embed(
                    title="🌞 Hey Benni",
                    description=(
                        "**💡 DAILY REMINDER • 12:30**\n\n"
                        "**🕛 NOVA FUTTER 🕛**\n\n"
                        "Deine tägliche CS2 Match Erinnerung\n"
                        "Vergiss nicht heute auf spannende Matches zu checken!"
                    ),
                    color=0xff9900,
                    timestamp=datetime.datetime.now()
                )
                
                # Befehle als schöne Liste
                embed.add_field(
                    name="**🎯 Verfügbare Befehle:**",
                    value=(
                        "▫️ `/status` - Bot Info\n"
                        "▫️ `/matches` - Aktuelle Matches anzeigen\n"
                        "▫️ `/subscribe <team>` - Team abonnieren\n"  
                        "▫️ `/unsubscribe <team>` - Team nicht mehr abonnieren"
                    ),
                    inline=False
                )
                
                embed.set_footer(text="🎮 CS2 Match Bot • Have a nice day!")
                
                await user.send(embed=embed)
                print(f"✅ Daily reminder sent to {user.name}")
                
            except discord.Forbidden:
                print(f"❌ Cannot DM user {user_id} (no permissions)")
            except Exception as e:
                print(f"❌ Error sending DM to {user_id}: {e}")
                
    except Exception as e:
        print(f"❌ Daily reminder error: {e}")

# =========================
# TWITCH LIVE CHECKER
# =========================
@tasks.loop(minutes=5)
async def check_twitch_live():
    """Einfacher Twitch Check ohne API"""
    try:
        async with aiohttp.ClientSession() as session:
            # Twitch Channel Seite abrufen
            url = f"https://twitch.tv/{TWITCH_USERNAME}"
            async with session.get(url) as response:
                html = await response.text()
                
                # Einfache Prüfung ob "isLiveBroadcast" im HTML ist
                if '"isLiveBroadcast":true' in html:
                    await send_simple_announcement()
                    
    except Exception as e:
        print(f"❌ Simple Twitch check error: {e}")

async def send_simple_announcement():
    """Einfache Live Announcement ohne API"""
    try:
        if not ANNOUNCEMENT_CHANNEL_ID:
            return
            
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not channel:
            return
            
        # Anti-Spam Check
        if hasattr(send_simple_announcement, 'last_announcement'):
            time_since_last = datetime.datetime.now() - send_simple_announcement.last_announcement
            if time_since_last < timedelta(hours=2):
                return
        
        # DEIN CUSTOM ANNOUNCEMENT TEXT
        announcement_text = (
            f"@everyone @here  |  https://twitch.tv/{TWITCH_USERNAME}  |  "
            f"{TWITCH_USERNAME} is going live !  --  check out the stream here:"
        )
        
        # NEUES TWITCH EMBED DESIGN VERWENDEN
        embed = create_twitch_go_live_alert()
        
        await channel.send(announcement_text, embed=embed)
            
        send_simple_announcement.last_announcement = datetime.datetime.now()
        print(f"✅ Twitch Live Announcement gesendet!")
        
    except Exception as e:
        print(f"❌ Twitch announcement error: {e}")

# =========================
# PERSISTENT BUTTON HANDLER
# =========================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id', '')
        
        role_mapping = {
            'role_cs2': 'CS 2',
            'role_valorant': 'Valorant', 
            'role_lol': 'League of Legends',
            'role_apex': 'Apex Legends',
            'role_cod': 'Call of Duty',
            'role_diablo': 'Diablo 4',
            'role_tibia': 'Tibia',
            'role_pubg': 'PUBG',
            'role_rust': 'Rust',
            'role_fortnite': 'Fortnite',
            'role_r6': 'Rainbow Six Siege',
            'role_overwatch': 'Overwatch',
            'role_wow': 'World of Warcraft',
            'role_halo': 'Halo 2'
        }
        
        if custom_id in role_mapping:
            await interaction.response.defer(ephemeral=True)
            role_name = role_mapping[custom_id]
            
            try:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if not role:
                    role = await interaction.guild.create_role(
                        name=role_name, 
                        mentionable=True, 
                        color=discord.Color.blue()
                    )
                
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    await interaction.followup.send(f"❌ {role_name} Rolle entfernt!", ephemeral=True)
                else:
                    await interaction.user.add_roles(role)
                    await interaction.followup.send(f"✅ {role_name} Rolle hinzugefügt!", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)

# =========================
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    correct_name, found = find_team_match(team)
    
    # NEU: Warnung wenn Team nicht in unseren Listen steht
    original_lower = team.lower()
    correct_lower = correct_name.lower()
    
    if original_lower != correct_lower:
        # Team wurde "intelligent" zugeordnet (z.B. "navi" → "Natus Vincere")
        message = f"✅ **{get_display_name(correct_name)}** added for alerts! 🎯"
    else:
        # Team wurde direkt übernommen (nicht in Listen)
        message = f"✅ **{correct_name.upper()}** added for alerts! ⚠️ (Team not in database)"
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        if save_data():
            await ctx.send(message)
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send(f"⚠️ **{get_display_name(correct_name)}** is already subscribed!")

@bot.command()
async def unsubscribe(ctx, *, team):
    guild_id = str(ctx.guild.id)
    correct_name, found = find_team_match(team)
    
    if guild_id in TEAMS and correct_name in TEAMS[guild_id]:
        TEAMS[guild_id].remove(correct_name)
        if save_data():
            await ctx.send(f"❌ **{get_display_name(correct_name)}** removed from alerts!")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send(f"❌ **Team {get_display_name(correct_name)} not found!**")

@bot.command()
async def list(ctx):
    guild_id = str(ctx.guild.id)
    teams = TEAMS.get(guild_id, [])
    
    if teams:
        # Mit ## • UND Teamnamen in Fett MIT Logos
        team_list = "\n".join([f" • **{get_display_name(team, use_smart_lookup=True)}**" for team in teams])
        
        embed = discord.Embed(
            title=f"SUBSCRIBED TEAMS{'\u2800' * 25}📋",
            description=team_list,
            color=0x0099ff
        )
        
        embed.set_footer(text="🎮 CS2 Match Bot • Use /subscribe <team>")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ **No teams subscribed yet!**")
        
@bot.command()
async def settime(ctx, minutes: int):
    global ALERT_TIME
    if 1 <= minutes <= 240:
        ALERT_TIME = minutes
        if save_data():
            await ctx.send(f"⏰ **Alert time set to {minutes} minutes!** 🔔")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send("❌ **Please specify 1-240 minutes!**")

@bot.command()
async def matches(ctx):
    try:
        matches = await fetch_grid_matches()
        
        if matches:
            embed = discord.Embed(
                title=f"🎯 LIVE & UPCOMING CS2 MATCHES{'\u2800' * 15}<:cs2:1298250987483697202>",
                color=0x0099ff,
                timestamp=datetime.datetime.now()
            )
            
            for match in matches[:6]:
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                
                # Team-Namen mit Fallback auf 🌍 wenn kein Logo
                team1_display = get_display_name(match['team1'], use_smart_lookup=False)
                team2_display = get_display_name(match['team2'], use_smart_lookup=False)
                
                # Ersetze Team-Namen ohne Logo mit 🌍
                if not re.search(r'<:[a-zA-Z0-9_]+:\d+>', team1_display):
                    team1_display = f"🌍 {team1_display}"
                if not re.search(r'<:[a-zA-Z0-9_]+:\d+>', team2_display):
                    team2_display = f"🌍 {team2_display}"
                
                # Teams mit Fett + ABSATZ nach team2
                match_content = (
                    f"**{team1_display}**\n"
                    f"**<:VS:1428145739443208305>**\n"
                    f"**{team2_display}**\n"
                    f"\n"
                    f"**🏆 {match['event']}**\n"
                )
                
                # Zeitangaben ohne Fett
                starts_in_text = f"⏰ Starts in: {int(time_until)} minutes"
                padding = '\u2800' * 25
                time_line = f"{starts_in_text}{padding}🕐 {match['time_string']}"
                
                # Alles in einem Field
                embed.add_field(
                    name="",
                    value=f"{match_content}{time_line}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    inline=False
                )
            
            embed.set_footer(text="🎮 CS2 Match Bot • Use /subscribe <team>")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ **No matches found**")
        
    except Exception as e:
        await ctx.send(f"❌ **Error:** {e}")

@bot.command()
async def autosetup(ctx):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    added_teams = []
    for team in AUTO_SUBSCRIBE_TEAMS:
        if team not in TEAMS[guild_id]:
            TEAMS[guild_id].append(team)
            added_teams.append(team)
    
    if save_data():
        if added_teams:
            team_list = "\n".join([f"• {get_display_name(team)}" for team in added_teams])
            await ctx.send(f"✅ **Auto-subscribed {len(added_teams)} teams!**\n{team_list}")
        else:
            await ctx.send("✅ **Teams already subscribed!**")
    else:
        await ctx.send("⚠️ **Save failed!**")

@bot.command()
async def status(ctx):
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    guild_id = str(ctx.guild.id)
    subscribed_count = len(TEAMS.get(guild_id, []))
    
    # ✅ NEUE LOGIK FÜR ALERT CHANNEL & TIME
    alert_channel_status = "❌"
    if MATCH_ALERT_CHANNEL_ID:
        channel = bot.get_channel(MATCH_ALERT_CHANNEL_ID)
        if channel:
            alert_channel_status = f"✅ #{channel.name}"
    
    alert_time_status = f"✅ {ALERT_TIME}min" if ALERT_TIME else "❌"
    
    # Status-Informationen
    status_content = (
        f" • 🟢 **STATUS:** ✅ ONLINE\n"
        f" • ⏰ **UPTIME:** {hours}h {minutes}m\n" 
        f" • 🔔 **ALERTS:** {alert_channel_status}\n"
        f" • ⏱️ **ALERT TIME:** {alert_time_status}\n"
        f" • 👥 **SUBSCRIBED:** {subscribed_count} TEAMS\n"
        f" • 🌐 **SOURCE:** GRID.GG LIVE-API"
    )
    
    embed = discord.Embed(
        title=f"BOT STATUS{'\u2800' * 28}🤖",
        description=status_content,
        color=0x00ff00
    )
    
    embed.set_footer(text="🎮 CS2 Match Bot • Have fun!")
    
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx):
    """Testet das Embed Design - zeigt Match Alert"""
    test_match = {
        'team1': 'Falcons',
        'team2': 'Team Vitality', 
        'event': 'BLAST Premier Fall Finals',
        'time_string': '16:30'
    }
    
    embed = create_match_alert(test_match, 15)
    await ctx.send("🎨 **EMBED DESIGN TEST:**", embed=embed)
    
@bot.command()
async def debugalert(ctx):
    """🔍 LIVE Debug vom Alert-System"""
    matches = await fetch_grid_matches()
    current_time = datetime.datetime.now(timezone.utc).timestamp()
    
    await ctx.send(f"**🔍 LIVE DEBUG:** {len(matches)} Matches, ALERT_TIME={ALERT_TIME}")
    await ctx.send(f"**🕐 Aktuelle Zeit:** {datetime.datetime.now().strftime('%H:%M')}")
    
    for match in matches:
        time_until = (match['unix_time'] - current_time) / 60
        await ctx.send(f"**🎯 {match['team1']} vs {match['team2']}:** {time_until:.1f} min")
        
        # Prüfe Bedingung
        if 0 <= time_until <= ALERT_TIME:
            await ctx.send("✅ **WÜRDE JETZT PINGEN!**")
            
            # Prüfe Teams
            for guild_id, subscribed_teams in TEAMS.items():
                for subscribed_team in subscribed_teams:
                    correct_name, found = find_team_match(subscribed_team)
                    team_variants = [correct_name.lower()] + [v.lower() for v in TEAM_SYNONYMS.get(correct_name, [])]
                    
                    if (match['team1'].lower() in team_variants or 
                        match['team2'].lower() in team_variants):
                        await ctx.send(f"✅ **Team Match:** {subscribed_team} → {correct_name}")
        else:
            await ctx.send(f"❌ **Noch nicht in Alert-Zeit:** {time_until:.1f} min")
            
@bot.command()
async def debugtime(ctx):
    """🔍 Debug der Zeitberechnung & Timezone Probleme"""
    now_utc = datetime.datetime.now(timezone.utc)
    now_local = datetime.datetime.now()
    
    await ctx.send(f"**🌍 TIMEZONE DEBUG:**")
    await ctx.send(f"UTC Zeit: {now_utc.strftime('%H:%M')}")
    await ctx.send(f"Local Zeit: {now_local.strftime('%H:%M')}")
    await ctx.send(f"Difference: {(now_local - now_utc.replace(tzinfo=None)).total_seconds() / 3600:.1f} Stunden")
    
    matches = await fetch_grid_matches()
    for match in matches[:2]:
        match_dt_utc = datetime.datetime.fromtimestamp(match['unix_time'], tz=timezone.utc)
        match_dt_local = match_dt_utc.astimezone(timezone(timedelta(hours=2)))
        
        await ctx.send(f"**🎯 {match['team1']} vs {match['team2']}:**")
        await ctx.send(f"Match UTC: {match_dt_utc.strftime('%H:%M')}")
        await ctx.send(f"Match Local: {match_dt_local.strftime('%H:%M')}")
        await ctx.send(f"Time String: {match['time_string']}")
        
        # Beide Berechnungen
        time_until_utc = (match_dt_utc - now_utc).total_seconds() / 60
        time_until_local = (match_dt_local - now_local.replace(tzinfo=timezone(timedelta(hours=2)))).total_seconds() / 60
        
        await ctx.send(f"Time Until (UTC): {time_until_utc:.1f} min")
        await ctx.send(f"Time Until (Local): {time_until_local:.1f} min")

@bot.command()
async def twitchtest(ctx):
    """Twitch Test mit LIVE-Banner und Twitch-Daten"""
    
    announcement = "@everyone @here  |  https://twitch.tv/shiseii  |  shiseii is going live !  --  check out the stream here:"
    
    embed = discord.Embed(
        color=0x9146FF,
        timestamp=datetime.datetime.now()
    )
    
    # ZEILE 1: TWITCH LIVE ALERT als klickbarer Link
    embed.add_field(
        name="",
        value="**[TWITCH LIVE ALERT](https://twitch.tv/shiseii)**",
        inline=False
    )
    
    embed.add_field(name="", value="", inline=False)
    
    # Stream Info über dem Banner
    embed.add_field(
        name="🔴 shiseii is now live on Twitch!",
        value="**[🌐 CLICK HERE TO WATCH LIVE](https://twitch.tv/shiseii)**",
        inline=False
    )
    
    embed.add_field(name="", value="", inline=False)
    
    # Titel
    embed.add_field(
        name="📺 TWITCH_TEST_TITLE",
        value="",
        inline=False
    )
    
    # Game ohne "🕐 LIVE"
    embed.add_field(
        name="🎮 TWITCH_TEST_GAME",
        value="",
        inline=False
    )
    
    # ✅ NUR EIN ABSATZ bis zum Banner
    embed.add_field(name="", value="", inline=False)
    
    # LIVE-Banner
    embed.set_image(url="https://i.ibb.co/6cQh6FjN/LIVE.png")
    
    # Profilbild oben rechts (Thumbnail)
    embed.set_thumbnail(url="https://static-cdn.jtvnw.net/jtv_user_pictures/8b4104f3-43d0-4d7e-a7ae-bd15408acad4-profile_image-70x70.png")
    
    embed.set_footer(text="🎮 CS2 Match Bot • Have fun!")
    
    await ctx.send(announcement, embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx, channel: discord.TextChannel):
    """Setzt den Channel für Match Alerts - TEMPORÄR"""
    global MATCH_ALERT_CHANNEL_ID
    MATCH_ALERT_CHANNEL_ID = channel.id
    
    await ctx.send(f"✅ **Match Alert Channel auf {channel.mention} gesetzt!** (Bis zum Neustart)")
    print(f"🔧 Match Alert Channel TEMPORÄR geändert zu: {channel.name}")

@bot.command()
async def ping(ctx):
    await ctx.send('🏓 **PONG!** 🎯')

# =========================
# TWITCH COMMANDS
# =========================
@bot.command()
async def setannouncechannel(ctx, channel: discord.TextChannel):
    """Setzt den Channel für Twitch Announcements"""
    global ANNOUNCEMENT_CHANNEL_ID
    ANNOUNCEMENT_CHANNEL_ID = channel.id
    await ctx.send(f"📢 **Twitch Announcements werden in {channel.mention} gepostet!**")

# =========================
# ROLE BUTTONS COMMAND
# =========================
@bot.command()
async def createroles(ctx):
    """Erstelle die Game-Role Buttons in diesem Channel"""
    
    # ERSTE NACHRICHT: Hauptüberschrift + CS2 & Valorant
    embed1 = discord.Embed(
        title="🎮 **Choose Your Games**",
        description="Click the buttons to add/remove game roles\nYou will be pinged for matches of your selected games!\n\n---",
        color=0x5865F2
    )
    
    # ERSTER VIEW: CS2 und Valorant
    view1 = discord.ui.View(timeout=None)
    
    # CS2 Button
    cs2_button = discord.ui.Button(
        label="CS 2", 
        emoji="<:cs2:1298250987483697202>", 
        style=discord.ButtonStyle.secondary, 
        custom_id="role_cs2",
        row=0
    )
    view1.add_item(cs2_button)
    
    # Valorant Button
    valorant_button = discord.ui.Button(
        label="Valorant", 
        emoji="<:valorant:1298251760720150550>", 
        style=discord.ButtonStyle.secondary, 
        custom_id="role_valorant",
        row=1
    )
    view1.add_item(valorant_button)
    
    await ctx.send(embed=embed1, view=view1)
    
    # ZWEITE NACHRICHT: "Other Games" als reiner Text mit Absätzen
    await ctx.send("** **")
    await ctx.send("## Other Games")
    await ctx.send("** **")
    
    # DRITTE NACHRICHT: Erste Reihe Other Games
    view2 = discord.ui.View(timeout=None)
    
    buttons_row1 = [
        ("League of Legends", "<:lol:1298252270240272416>", "role_lol"),
        ("Apex Legends", "<:apex:1298251721184772119>", "role_apex"),
        ("Call of Duty", "<:cod:1298251740965109770>", "role_cod")
    ]
    
    for label, emoji, custom_id in buttons_row1:
        button = discord.ui.Button(
            label=label, 
            emoji=emoji, 
            style=discord.ButtonStyle.secondary, 
            custom_id=custom_id,
            row=0
        )
        view2.add_item(button)
    
    await ctx.send(view=view2)
    
    # VIERTE NACHRICHT: Zweite Reihe Other Games
    view3 = discord.ui.View(timeout=None)
    
    buttons_row2 = [
        ("Diablo 4", "<:d4:1304002853253152799>", "role_diablo"),
        ("Tibia", "<:tibia:1305455884201103393>", "role_tibia"),
        ("PUBG", "<:pubg:1305772146861277255>", "role_pubg")
    ]
    
    for label, emoji, custom_id in buttons_row2:
        button = discord.ui.Button(
            label=label, 
            emoji=emoji, 
            style=discord.ButtonStyle.secondary, 
            custom_id=custom_id,
            row=0
        )
        view3.add_item(button)
    
    await ctx.send(view=view3)
    
    # FÜNFTE NACHRICHT: Dritte Reihe Other Games
    view4 = discord.ui.View(timeout=None)
    
    buttons_row3 = [
        ("Rust", "<:rust:1305456246996078614>", "role_rust"),
        ("Fortnite", "<:fortnite:1305772894336450571>", "role_fortnite"),
        ("Rainbow Six Siege", "<:r6:1305774806083305515>", "role_r6")
    ]
    
    for label, emoji, custom_id in buttons_row3:
        button = discord.ui.Button(
            label=label, 
            emoji=emoji, 
            style=discord.ButtonStyle.secondary, 
            custom_id=custom_id,
            row=0
        )
        view4.add_item(button)
    
    await ctx.send(view=view4)
    
    # SECHSTE NACHRICHT: Vierte Reihe Other Games
    view5 = discord.ui.View(timeout=None)
    
    buttons_row4 = [
        ("Overwatch", "<:overwatch:1305773706471276554>", "role_overwatch"),
        ("World of Warcraft", "<:wow:1305809271992352809>", "role_wow"),
        ("Halo 2", "<:halo2:1305775045204770846>", "role_halo")
    ]
    
    for label, emoji, custom_id in buttons_row4:
        button = discord.ui.Button(
            label=label, 
            emoji=emoji, 
            style=discord.ButtonStyle.secondary, 
            custom_id=custom_id,
            row=0
        )
        view5.add_item(button)
    
    await ctx.send(view=view5)

# =========================
# FLASK & STARTUP
# =========================
@app.route('/')
def home():
    return "✅ CS2 Match Bot - GRID.GG LIVE-API + TWITCH"

@app.route('/health')
def health():
    return jsonify({
        "status": "online", 
        "teams": sum(len(teams) for teams in TEAMS.values()),
        "servers": len(TEAMS)
    })

def run_flask():
    try:
        app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
    except:
        pass

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online! - GRID.GG LIVE-API + TWITCH')
    
    for guild in bot.guilds:
        guild_id = str(guild.id)
        
        if guild_id not in TEAMS:
            TEAMS[guild_id] = []
        
        for team in AUTO_SUBSCRIBE_TEAMS:
            if team not in TEAMS[guild_id]:
                TEAMS[guild_id].append(team)
    
    save_data()
    
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    if not daily_dm_reminder.is_running():
        daily_dm_reminder.start()
    if not check_twitch_live.is_running():
        check_twitch_live.start()
    print("🔔 Alert system started!")
    print("⏰ Daily DM reminder started!")
    print("📺 Twitch live checker started!")

if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
