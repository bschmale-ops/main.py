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

# NEU: Setup Hook für persistente Buttons - ÜBERARBEITETE VERSION
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
    'FURIA': '<:furia:1428075132156641471> FURIA',
    'Natus Vincere': '<:navi:1428075186976194691> NATUS VINCERE',
    'FaZe': '<:faze:1428075117753401414> FAZE',
    '3DMAX': '<:3dmax:1428075077408133262> 3DMAX',
    'Astralis': '<:astralis:1428075043526672394> ASTRALIS',
    'G2': '<:g2:1428075144240431154> G2',
    'Aurora': '<:aurora:1428075062287798272> AURORA',
    'Liquid': '<:liquid:1428075155456000122> LIQUID',
    'M80': '<:m80:1428076593028530236> M80',
    'ENCE': 'ENCE',  # NEU: ENCE Main Team hinzugefügt
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
    'ENCE': ['ence'],  # NEU: ENCE Main Team Synonym
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
        # FÜR MATCHES/ALERTS: Exakt anzeigen was Grid.gg liefert
        return TEAM_DISPLAY_NAMES.get(team_name, f"{team_name.upper()}")
    
    # FÜR SUBSCRIBE/LIST: Intelligente Zuordnung
    if team_name in TEAM_DISPLAY_NAMES:
        return TEAM_DISPLAY_NAMES[team_name]
    
    # NEU: Nur exakte Matches für intelligente Zuordnung
    return TEAM_DISPLAY_NAMES.get(team_name, f"{team_name.upper()}")

def get_team_emoji(team_name, use_smart_lookup=False):
    """Get only the emoji part - mit Regex für Emojis"""
    display = get_display_name(team_name, use_smart_lookup=use_smart_lookup)
    
    # Finde Custom Emojis (Format: <:name:ID>)
    emoji_match = re.search(r'<:[a-zA-Z0-9_]+:\d+>', display)
    if emoji_match:
        return emoji_match.group()
    return ""

def get_team_name_only(team_name, use_smart_lookup=False):
    """Get only the name part - komplett nach dem Emoji"""
    display = get_display_name(team_name, use_smart_lookup=use_smart_lookup)
    
    # Entferne Custom Emojis (Format: <:name:ID>) und gebe den REST zurück
    display_without_emoji = re.sub(r'<:[a-zA-Z0-9_]+:\d+>', '', display).strip()
    
    return display_without_emoji
    
def center_vs(team1, team2):
    """Einfache Zentrierung für Alerts MIT # und KORREKTER VS ID"""
    return f"# {team1}\n# <:VS:1428145739443208305>\n#  {team2}"

def create_frame(title, content):
    """Erstelle Rahmen OHNE Code-Blöcke"""
    separator = "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄"
    return f"{separator}\n{title}\n{separator}\n{content}\n{separator}"

# =========================
# NEUE EMBED FUNKTION FÜR MATCH ALERTS
# =========================
def create_match_alert(match, time_until):
    team1_display = get_display_name(match['team1'], use_smart_lookup=False)
    team2_display = get_display_name(match['team2'], use_smart_lookup=False)
    
    embed = discord.Embed(
        title=f"CS2 MATCH ALERT{'\u2800' * 25}<:cs2:1298250987483697202>",
        description=f"# {team1_display}\n# <:VS:1428145739443208305>\n# {team2_display}\n",  # 1 Absatz nach Vitality
        color=0x00ff00 if time_until > 15 else 0xff9900,
        timestamp=datetime.datetime.now()
    )
    
    # 2 ABSÄTZE über Tournament
    embed.add_field(name="", value="", inline=False)  # ⬅️ Erster Absatz
    embed.add_field(name="", value="", inline=False)  # ⬅️ Zweiter Absatz
    
    # Zeile 1: "Tournament" und "🕐 Time 16:30" in einer Zeile (rechtsbündig)
    header_line = f"🏆 Tournament{'\u2800' * 25}🕐 Time {match['time_string']}"
    
    # Zeile 2: Nur Tournament-Name
    content_line = f"{match['event']}"
    
    # Beide Zeilen in einem Field
    embed.add_field(name=header_line, value=content_line, inline=False)
    embed.add_field(name="", value="", inline=False)  # Absatz
    embed.add_field(name="⏰ Starts in", value=f"**{int(time_until)} minutes**", inline=False)
    embed.add_field(name="", value="", inline=False)  # Absatz
    embed.add_field(name="📺 Stream Tip", value="[shiseii on Twitch](https://twitch.tv/shiseii)", inline=False)
    embed.set_footer(text="🎮 CS2 Match Bot • Have fun!")
    
    return embed

# =========================
# TWITCH LIVE EMBED FUNKTION - OPTION 2
# =========================
def create_twitch_go_live_alert():
    embed = discord.Embed(
        title="🔴 JETZT LIVE AUF TWITCH!",
        description="**shiseii streamt CS2**\nKomm vorbei und chill mit! 🎮",
        color=0x9146FF,  # Twitch Lila
        url="https://twitch.tv/shiseii"
    )
    embed.add_field(name="🎮 Spiel", value="Counter-Strike 2", inline=True)
    embed.add_field(name="💬 Chat", value="Aktiv & Friendly", inline=True)
    embed.add_field(name="🎵 Musik", value="Lofi Beats", inline=True)
    embed.set_thumbnail(url="https://static-cdn.jtvnw.net/jtv_user_pictures/your_profile_image")
    embed.set_image(url="https://static-cdn.jtvnw.net/jtv_user_pictures/your_stream_banner")
    embed.set_footer(text="Viel Spaß beim Zuschauen! 🎪")
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
# GRID.GG API - GRAPHQL VERSION (KORRIGIERT)
# =========================
async def fetch_grid_matches():
    matches = []
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api-op.grid.gg/central-data/graphql"
            headers = {
                'x-api-key': GRID_API_KEY,
                'Content-Type': 'application/json'
            }
            
            # KORREKTE allSeries QUERY MIT edges/node
            graphql_query = {
                "query": """
                query GetUpcomingSeries {
                    allSeries {
                        edges {
                            node {
                                id
                                startDate
                                participants {
                                    team {
                                        name
                                    }
                                }
                                tournament {
                                    name
                                }
                                status
                            }
                        }
                    }
                }
                """
            }
            
            async with session.post(url, headers=headers, json=graphql_query, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Grid.gg API Response erhalten")
                    
                    if data.get('errors'):
                        print(f"❌ GraphQL Errors: {data['errors']}")
                        return []
                    
                    # Response verarbeiten MIT edges/node
                    edges = data.get('data', {}).get('allSeries', {}).get('edges', [])
                    
                    current_time = datetime.datetime.now(timezone.utc)
                    
                    for edge in edges:
                        try:
                            series = edge.get('node', {})
                            
                            # Nur upcoming Series
                            if series.get('status') != 'UPCOMING':
                                continue
                                
                            participants = series.get('participants', [])
                            if len(participants) >= 2:
                                team1 = participants[0].get('team', {}).get('name', 'TBD')
                                team2 = participants[1].get('team', {}).get('name', 'TBD')
                                
                                if team1 != 'TBD' and team2 != 'TBD':
                                    start_date = series.get('startDate')
                                    if start_date:
                                        match_dt = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                                        unix_time = int(match_dt.timestamp())
                                        
                                        # Nur zukünftige Matches
                                        if match_dt > current_time:
                                            german_tz = timezone(timedelta(hours=2))
                                            local_dt = match_dt.astimezone(german_tz)
                                            time_string = local_dt.strftime("%H:%M")
                                            
                                            tournament = series.get('tournament', {})
                                            event = tournament.get('name', 'CS2 Tournament')
                                            
                                            matches.append({
                                                'team1': team1, 
                                                'team2': team2, 
                                                'unix_time': unix_time,
                                                'event': event, 
                                                'time_string': time_string
                                            })
                        except Exception as e:
                            print(f"❌ Series parsing error: {e}")
                            continue
                    
                    matches.sort(key=lambda x: x['unix_time'])
                    print(f"✅ Gefundene Matches: {len(matches)}")
                    return matches
                else:
                    print(f"❌ Grid.gg API error: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Grid.gg API connection error: {e}")
        return []

# ALTERNATIVE QUERY FALLS DIE ERSTE NICHT FUNKTIONIERT
async def fetch_grid_matches_alternative():
    """Alternative Query falls series nicht funktioniert"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api-op.grid.gg/central-data/graphql"
            
            headers = {
                'x-api-key': GRID_API_KEY,
                'Content-Type': 'application/json'
            }
            
            graphql_query = {
                "query": """
                query GetUpcomingEvents {
                    __schema {
                        types {
                            name
                            fields {
                                name
                            }
                        }
                    }
                }
                """
            }
            
            async with session.post(url, headers=headers, json=graphql_query, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    print("🔍 Verfügbare Queries:")
                    if data.get('data'):
                        types = data['data']['__schema']['types']
                        query_type = next((t for t in types if t['name'] == 'Query'), None)
                        if query_type:
                            available_queries = [field['name'] for field in query_type.get('fields', [])]
                            print(f"✅ Verfügbare Queries: {available_queries}")
                    return []
    except Exception as e:
        print(f"❌ Alternative query error: {e}")
        return []

# =========================
# ALERT SYSTEM - ANGEPASST FÜR GRID.GG
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    try:
        matches = await fetch_grid_matches()  # Jetzt Grid.gg Funktion
        current_time = datetime.datetime.now(timezone.utc).timestamp()
        
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
    try:
        message = create_frame(
            "🌞 DAILY REMINDER • 12:30",
            f"#      🕛 NOVA FUTTER 🕛\n"
            f"#\n"
            f"#\n"
            f"#   Viel Erfolg heute! 🚀\n"
            f"#\n"
            f"#   {datetime.datetime.now().strftime('%d.%m.%Y')}"
        )
        
        target_user_id = 238376746230087682
        
        try:
            user = await bot.fetch_user(target_user_id)
            await user.send(message)
            print(f"✅ Daily DM sent to {user.name}")
        except Exception as e:
            print(f"❌ Failed to send daily DM: {e}")
            
    except Exception as e:
        print(f"❌ Daily DM error: {e}")

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
# BOT COMMANDS - ANGEPASST FÜR GRID.GG
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
async def debug(ctx):
    """Findet die korrekten Feldnamen für Series"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api-op.grid.gg/central-data/graphql"
            headers = {
                'x-api-key': GRID_API_KEY,
                'Content-Type': 'application/json'
            }
            
            # SCHEMA EXPLORATION - Welche Felder hat Series?
            schema_query = {
                "query": """
                query GetSeriesFields {
                    __type(name: "Series") {
                        name
                        fields {
                            name
                            type {
                                name
                                kind
                            }
                        }
                    }
                }
                """
            }
            
            await ctx.send("🔍 **Erkunde Series Felder...**")
            
            async with session.post(url, headers=headers, json=schema_query, timeout=15) as response:
                data = await response.json()
                
                if data.get('data', {}).get('__type'):
                    series_fields = data['data']['__type']['fields']
                    field_names = [f['name'] for f in series_fields]
                    await ctx.send(f"✅ **Series Felder:** {', '.join(field_names)}")
                    
                    # Teste mit den gefundenen Feldern
                    test_fields = ["id", "name", "startTime", "scheduledStartTime", "teams", "tournament"]
                    available_fields = [f for f in test_fields if f in field_names]
                    
                    await ctx.send(f"🧪 **Teste mit Feldern:** {', '.join(available_fields)}")
                    
                    # Test Query mit verfügbaren Feldern
                    test_query = {
                        "query": f"""
                        query TestSeries {{
                            allSeries {{
                                edges {{
                                    node {{
                                        {" ".join(available_fields)}
                                    }}
                                }}
                            }}
                        }}
                        """
                    }
                    
                    async with session.post(url, headers=headers, json=test_query, timeout=15) as test_response:
                        test_data = await test_response.json()
                        if not test_data.get('errors'):
                            await ctx.send("✅ **Query funktioniert!**")
                            # Zeige ein Beispiel
                            if test_data.get('data', {}).get('allSeries', {}).get('edges'):
                                sample_edge = test_data['data']['allSeries']['edges'][0]
                                await ctx.send(f"📄 **Beispiel:** ```{json.dumps(sample_edge, indent=2)[:800]}```")
                        else:
                            await ctx.send(f"❌ **Test Query Fehler:** {test_data['errors'][0]['message']}")
                
                else:
                    await ctx.send(f"❌ Schema Error: ```{json.dumps(data, indent=2)[:1000]}```")
                    
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        
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
        team_list = "\n".join([f"• **{get_display_name(team)}**" for team in teams])
        framed_message = create_frame("📋 SUBSCRIBED TEAMS", team_list)
        await ctx.send(framed_message)
    else:
        await ctx.send("❌ **No teams subscribed yet!**")

@bot.command()
async def statstest(ctx):
    """Testet die Stats Feed API mit x-api-key Header"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api-op.grid.gg/statistics-feed/graphql"
            
            headers = {
                'x-api-key': GRID_API_KEY,
                'Content-Type': 'application/json'
            }
            
            query = {
                "query": """
                query {
                    __schema {
                        types {
                            name
                            fields {
                                name
                            }
                        }
                    }
                }
                """
            }
            
            async with session.post(url, headers=headers, json=query) as response:
                data = await response.json()
                await ctx.send(f"🔍 Stats Feed API:\nStatus: {response.status}")
                
                if 'data' in data:
                    types = data['data']['__schema']['types']
                    match_types = [t for t in types if any(x in t['name'].lower() for x in ['match', 'series', 'team', 'tournament'])]
                    await ctx.send(f"📋 Relevante Types: {[t['name'] for t in match_types[:10]]}")
                else:
                    await ctx.send(f"📄 Response: ```{json.dumps(data, indent=2)[:1000]}```")
                
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        
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
        matches = await fetch_grid_matches()  # Jetzt Grid.gg Funktion
        
        if matches:
            match_list = ""
            for match in matches[:6]:
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                
                team1_emoji = get_team_emoji(match['team1'], use_smart_lookup=False)
                team1_name = get_team_name_only(match['team1'], use_smart_lookup=False)
                team2_emoji = get_team_emoji(match['team2'], use_smart_lookup=False)
                team2_name = get_team_name_only(match['team2'], use_smart_lookup=False)
                
                match_list += f"**{team1_emoji} {team1_name} <:VS:1428145739443208305> {team2_emoji} {team2_name}**\n"
                match_list += f"__⏰ {int(time_until)}min | 🏆 {match['event']}__\n\n"
            
            footer = f"🔔 Alert: {ALERT_TIME}min | 🔄 Check: every 2min"
            framed_message = create_frame("🎯 AVAILABLE CS2 MATCHES", f"{match_list}{footer}")
            await ctx.send(framed_message)
        else:
            await ctx.send("❌ **No matches found**")
        
    except Exception as e:
        await ctx.send(f"❌ **Error:** {e}")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    CHANNELS[str(ctx.guild.id)] = channel.id
    if save_data():
        await ctx.send(f"📡 **Alert channel set to {channel.mention}!** ✅")
    else:
        await ctx.send("⚠️ **Save failed!**")

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
    
    status_content = (
        f"🟢 STATUS: ✅ ONLINE\n"
        f"⏰ UPTIME: {hours}h {minutes}m\n"
        f"🔔 ALERTS: ✅ ACTIVE\n"
        f"⏱️ ALERT TIME: {ALERT_TIME}min\n"
        f"👥 SUBSCRIBED: {subscribed_count} TEAMS\n"
        f"🌐 SOURCE: GRID.GG API"  # Geändert zu Grid.gg
    )
    
    framed_message = create_frame("🤖 BOT STATUS", status_content)
    await ctx.send(framed_message)

@bot.command()
async def test(ctx):
    """Testet das neue Embed Design - zeigt Match Alert"""
    test_match = {
        'team1': 'Falcons',
        'team2': 'Team Vitality', 
        'event': 'BLAST Premier Fall Finals',
        'time_string': '16:30'
    }
    
    embed = create_match_alert(test_match, 15)
    await ctx.send("🎨 **NEUES EMBED DESIGN TEST:**", embed=embed)

@bot.command()
async def twitchtest(ctx):
    """Testet das Twitch Live Embed Design"""
    embed = create_twitch_go_live_alert()
    await ctx.send("🔴 **TWITCH LIVE TEST:**", embed=embed)
        
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
# ROLE BUTTONS COMMAND - ÜBERARBEITETE VERSION
# =========================
@bot.command()
async def createroles(ctx):
    """Erstelle die Game-Role Buttons in diesem Channel - NEUES LAYOUT"""
    
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
    return "✅ CS2 Match Bot - GRID.GG API + TWITCH"  # Geändert

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
    print(f'✅ {bot.user} is online! - GRID.GG API + TWITCH')  # Geändert
    
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
