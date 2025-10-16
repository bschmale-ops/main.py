import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import datetime
from datetime import timezone, timedelta
import json
import asyncio
from flask import Flask, jsonify
import threading
import aiohttp
from bs4 import BeautifulSoup
import socket
import re

print("🚀 Starting Discord CS2 Bot - PANDASCORE API")

# =========================
# BOT SETUP
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents, case_insensitive=True)

# =========================
# CONFIGURATION
# =========================
PANDASCORE_TOKEN = "NFG_fJz5qyUGHaWJmh-CcIeGELtI5prmh-YHWNibDTqDXR-p6sM"

# =========================
# AUTO-SUBSCRIBE TEAMS
# =========================
AUTO_SUBSCRIBE_TEAMS = [
    'Falcons', 'MOUZ', 'Team Spirit', 'Team Vitality', 'The Mongolz',
    'FURIA', 'Natus Vincere', 'FaZe', '3DMAX', 'Astralis', 
    'G2', 'Aurora', 'Liquid', 'M80'
]

# Team Display Names mit korrekten Emoji-IDs
TEAM_DISPLAY_NAMES = {
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
    'M80': '<:m80:1428076593028530236> M80'
}

# =========================
# TEAM DATA
# =========================
TEAM_SYNONYMS = {
    'Natus Vincere': ['navi'],
    'FaZe Clan': ['faze'], 
    'Team Vitality': ['vitality'],
    'G2 Esports': ['g2'],
    'MOUZ': ['mouz'],
    'Heroic': ['heroic'],
    'Cloud9': ['cloud9', 'c9'],
    'Team Spirit': ['spirit'],
    'FURIA': ['furia'],
    'OG': ['og'],
    'Virtus.pro': ['virtus pro', 'vp'],
    'ENCE': ['ence'],
    'Complexity': ['complexity', 'col'],
    'BIG': ['big'],
    'Eternal Fire': ['eternal fire', 'ef'],
    'Monte': ['monte'],
    'The Mongolz': ['the mongolz', 'mongolz'],
    '9z Team': ['9z', '9z team'],
    'G2 Esports': ['g2 ares', 'g2'],
    'MANA eSports': ['mana', 'mana esports'],
    '3DMAX': ['3dmax'],
    'Lynn Vision': ['lynn vision', 'lynn'],
    'Team Novaq': ['novaq'],
    'AMKAL ESPORTS': ['amkal'],
    'ARCRED': ['arcred'],
    '500': ['500'],
    'AM Gaming': ['am gaming'],
    'Dynamo Eclot': ['dynamo eclot'],
    'm0nesy team': ['m0nesy'],
    'Betera Esports': ['betera'],
    'Falcons': ['falcons'],
    'Astralis': ['astralis'],
    'Aurora': ['aurora'],
    'Liquid': ['liquid'],
    'M80': ['m80']
}

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    return input_team, False

def get_display_name(team_name):
    """Get team name with emoji for display"""
    return TEAM_DISPLAY_NAMES.get(team_name, f"{team_name.upper()}")

def validate_team_display():
    """Validate the structure of TEAM_DISPLAY_NAMES and log potential issues"""
    for team, display in TEAM_DISPLAY_NAMES.items():
        if ' ' not in display:
            print(f"⚠️ Warning: Team '{team}' has an invalid display format: '{display}' (no space between emoji and name)")
        elif not display.startswith('<:') and not display.startswith('<a:'):
            print(f"⚠️ Warning: Team '{team}' has an invalid emoji format: '{display}' (does not start with <: or <a:)")

def center_vs(team1, team2, separator="<:VS:1428145739443208305>"):
    """Dynamische Zentrierung mit Emoji-IDs"""
    # Liste der Zeilen mit vollständigen Emoji-IDs
    lines = [team1, separator, team2]
    
    # Maximale Textlänge ermitteln (der längste Text bestimmt die Breite)
    max_len = max(len(line) for line in lines)
    
    # Zusatzbreite für besseren Rand
    padding = 6
    
    # Alles schön zentriert ausgeben
    centered_lines = []
    for line in lines:
        centered_lines.append(f"# {line.center(max_len + padding)}")
    
    return "\n".join(centered_lines)

def create_centered_teams_display(team1, team2):
    """Erstelle perfekt zentrierte Team-Anzeige"""
    team1_display = get_display_name(team1)
    team2_display = get_display_name(team2)
    centered_display = center_vs(team1_display, team2_display)
    return centered_display

def create_frame(title, content):
    """Erstelle einen Rahmen für Textnachrichten"""
    separator = "─────────────────────────────"
    return f"{separator}\n{title}\n{separator}\n{content}\n{separator}"

# =========================
# DATA MANAGEMENT
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded data from {DATA_FILE}: {len(data.get('TEAMS', {}))} servers")
                return data
        print(f"📄 No {DATA_FILE} found, starting fresh")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
    except json.JSONDecodeError as e:
        print(f"❌ JSON error in {DATA_FILE}: {e} - resetting to default")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
    except Exception as e:
        print(f"❌ Load error: {e}")
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved data to {DATA_FILE}: {len(TEAMS)} servers")
        return True
    except Exception as e:
        print(f"❌ Save error in {DATA_FILE}: {e}")
        return False

# Load initial data
data = load_data()
TEAMS = data.get("TEAMS", {})
CHANNELS = data.get("CHANNELS", {})
ALERT_TIME = data.get("ALERT_TIME", 30)

print(f"📊 Loaded: {len(TEAMS)} servers, {sum(len(teams) for teams in TEAMS.values())} teams")

# Validate team display names on startup
validate_team_display()

# =========================
# PANDASCORE API
# =========================
async def fetch_pandascore_matches():
    """Fetch real matches from PandaScore API"""
    matches = []
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.pandascore.co/csgo/matches/upcoming"
            headers = {'Authorization': f'Bearer {PANDASCORE_TOKEN}', 'Accept': 'application/json'}
            params = {'sort': 'begin_at', 'page[size]': 20}
            print("🌐 Fetching PandaScore API...")
            async with session.get(url, headers=headers, params=params, timeout=15) as response:
                print(f"📡 PandaScore Response: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    for match_data in data:
                        try:
                            opponents = match_data.get('opponents', [])
                            if len(opponents) >= 2:
                                team1 = opponents[0].get('opponent', {}).get('name', 'TBD')
                                team2 = opponents[1].get('opponent', {}).get('name', 'TBD')
                                if team1 != 'TBD' and team2 != 'TBD':
                                    begin_at = match_data.get('begin_at')
                                    if begin_at:
                                        match_dt = datetime.datetime.fromisoformat(begin_at.replace('Z', '+00:00'))
                                        unix_time = int(match_dt.timestamp())
                                        german_tz = timezone(timedelta(hours=2))  # Sommerzeit
                                        local_dt = match_dt.astimezone(german_tz)
                                        time_string = local_dt.strftime("%H:%M")
                                    else:
                                        continue
                                    league = match_data.get('league', {})
                                    event = league.get('name', 'CS2 Tournament')
                                    matches.append({
                                        'team1': team1, 'team2': team2, 'unix_time': unix_time,
                                        'event': event, 'time_string': time_string, 'is_live': False,
                                        'source': 'PandaScore'
                                    })
                                    print(f"✅ Found: {team1} vs {team2} at {time_string}")
                        except Exception as e:
                            print(f"⚠️ Error parsing match: {e}")
                            continue
                    print(f"🎯 PandaScore: {len(matches)} matches found")
                    return matches
                else:
                    print(f"❌ PandaScore API error: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ PandaScore connection error: {e}")
        return []

# =========================
# ALERT SYSTEM - ALS NORMALE TEXTNACHRICHTEN MIT RAHMEN!
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Send match alerts - ALS NORMALE TEXTNACHRICHTEN!"""
    try:
        matches = await fetch_pandascore_matches()
        current_time = datetime.datetime.now(timezone.utc).timestamp()
        
        print(f"🔍 Checking {len(matches)} matches for alerts...")
        
        for guild_id, subscribed_teams in TEAMS.items():
            if not subscribed_teams:
                continue
                
            channel_id = CHANNELS.get(guild_id)
            if not channel_id:
                print(f"❌ No channel set for guild {guild_id}")
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Channel {channel_id} not found for guild {guild_id}")
                continue

            print(f"✅ Channel found: #{channel.name} in {channel.guild.name}")

            for match in matches:
                for subscribed_team in subscribed_teams:
                    correct_name, found = find_team_match(subscribed_team)
                    team_variants = [correct_name.lower()] + [v.lower() for v in TEAM_SYNONYMS.get(correct_name, [])]
                    
                    # VERBESSERTES MATCHING
                    if (match['team1'].lower() in team_variants or 
                        match['team2'].lower() in team_variants or
                        any(variant in match['team1'].lower() for variant in team_variants) or
                        any(variant in match['team2'].lower() for variant in team_variants)):
                        
                        time_until = (match['unix_time'] - current_time) / 60
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}"
                        
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            print(f"🚨 SENDING ALERT for {match['team1']} vs {match['team2']}!")
                            
                            # ✅ ALS NORMALE TEXTNACHRICHT MIT RAHMEN!
                            centered_display = create_centered_teams_display(match['team1'], match['team2'])
                            
                            match_content = (
                                f"\n\n{centered_display}\n\n\n\n"  # 4 Leerzeilen nach Teams
                                f"*🏆 {match['event']}*\n"
                                f"*⏰ Starts in {int(time_until)} minutes{' ' * 20}🕐 {match['time_string']}*"  # Zeit rechts
                            )
                            
                            framed_message = create_frame(
                                f"🎮 **MATCH ALERT** • {int(time_until)} MINUTES",
                                match_content
                            )
                            
                            try:
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 {role.mention}\n{framed_message}")
                                else:
                                    await channel.send(framed_message)
                                
                            except Exception as e:
                                print(f"❌ Failed to send message: {e}")
                                continue
                            
                            sent_alerts.add(alert_id)
                            print(f"✅ Alert sent and tracked: {match['team1']} vs {match['team2']} in {int(time_until)}min")
                            
                            if len(sent_alerts) > 50:
                                sent_alerts.clear()
                                
                            break
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS - ALLE ALS NORMALE TEXTNACHRICHTEN!
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Subscribe to a team for alerts"""
    guild_id = str(ctx.guild.id)
    print(f"Debug subscribe: guild_id={guild_id}, team_input={team}")
    
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    correct_name, found = find_team_match(team)
    print(f"Debug subscribe: correct_name={correct_name}, found={found}")
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        if save_data():
            await ctx.send(f"✅ **{get_display_name(correct_name)}** added for alerts! 🎯")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send(f"⚠️ **{get_display_name(correct_name)}** is already subscribed!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Unsubscribe from a team"""
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
    """Show subscribed teams as a text list (untereinander)"""
    guild_id = str(ctx.guild.id)
    print(f"Debug list: guild_id={guild_id}, raw TEAMS={TEAMS.get(guild_id, [])}")
    
    teams = TEAMS.get(guild_id, [])
    
    if teams:
        print(f"Debug list: Found {len(teams)} teams")
        team_list = "\n".join([f"• {get_display_name(team)}" for team in teams])
        framed_message = create_frame("📋 **SUBSCRIBED TEAMS**", team_list)
        await ctx.send(framed_message)
    else:
        print(f"Debug list: No teams for guild {guild_id}")
        await ctx.send("❌ **No teams subscribed yet!**")

@bot.command()
async def settime(ctx, minutes: int):
    """Set alert time in minutes"""
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
    """Show available matches - ALS NORMALE TEXTNACHRICHT!"""
    try:
        matches = await fetch_pandascore_matches()
        
        if matches:
            match_list = ""
            for i, match in enumerate(matches[:6], 1):
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                match_list += f"{i}. {get_display_name(match['team1'])} <:VS:1428145739443208305> {get_display_name(match['team2'])}\n"
                match_list += f"   *⏰ {int(time_until)}min | 🏆 {match['event']}*\n\n"
            
            footer = f"*🔔 Alert: {ALERT_TIME}min | 🔄 Check: every 2min*"
            framed_message = create_frame("🎯 **AVAILABLE CS2 MATCHES**", f"{match_list}{footer}")
            await ctx.send(framed_message)
        else:
            await ctx.send("❌ **No matches found**")
        
    except Exception as e:
        await ctx.send(f"❌ **Error:** {e}")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Set alert channel"""
    CHANNELS[str(ctx.guild.id)] = channel.id
    if save_data():
        await ctx.send(f"📡 **Alert channel set to {channel.mention}!** ✅")
    else:
        await ctx.send("⚠️ **Save failed!**")

@bot.command()
async def autosetup(ctx):
    """Auto-Subscribe Teams"""
    guild_id = str(ctx.guild.id)
    
    # Auto-Subscribe Teams
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
    """Show bot status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    guild_id = str(ctx.guild.id)
    subscribed_count = len(TEAMS.get(guild_id, []))
    
    status_content = (
        f"**🟢 STATUS:** **✅ ONLINE**\n"
        f"**⏰ UPTIME:** **{hours}h {minutes}m**\n"
        f"**🔔 ALERTS:** **✅ ACTIVE**\n"
        f"**⏱️ ALERT TIME:** **{ALERT_TIME}min**\n"
        f"**👥 SUBSCRIBED:** **{subscribed_count} TEAMS**\n"
        f"**🌐 SOURCE:** **PANDASCORE API**"
    )
    
    framed_message = create_frame("🤖 **BOT STATUS**", status_content)
    await ctx.send(framed_message)

@bot.command()
async def test(ctx):
    """Test alert - ALS NORMALE TEXTNACHRICHT!"""
    centered_display = create_centered_teams_display("Falcons", "Team Vitality")
    
    test_content = (
        f"\n\n{centered_display}\n\n\n\n"  # 4 Leerzeilen nach Teams
        f"*🏆 NODWIN Clutch Series*\n"
        f"*⏰ Starts in 15 minutes{' ' * 20}🕐 16:00*"  # Zeit rechts
    )
    
    framed_message = create_frame("🎮 **TEST ALERT** • 15 MINUTES", test_content)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention}\n{framed_message}")
    else:
        await ctx.send(framed_message)

@bot.command()
async def debug(ctx):
    """Debug: Test Zentrierung und Emojis"""
    centered_display = create_centered_teams_display("Team Spirit", "The Mongolz")
    await ctx.send(f"**Debug Output:**\n{centered_display}")

@bot.command()
async def debug_matches(ctx):
    """Debug: Zeige alle gefundenen Matches"""
    matches = await fetch_pandascore_matches()
    if matches:
        for i, match in enumerate(matches[:5]):
            time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
            await ctx.send(
                f"**Match {i+1}:** {match['team1']} vs {match['team2']}\n"
                f"**Event:** {match['event']}\n"
                f"**In:** {int(time_until)}min\n"
                f"**Time:** {match['time_string']}"
            )
    else:
        await ctx.send("❌ **No matches found**")

@bot.command()
async def ping(ctx):
    """Ping command"""
    await ctx.send('🏓 **PONG!** 🎯')

# =========================
# FLASK & STARTUP - AUTO SUBSCRIBE ONLY!
# =========================
@app.route('/')
def home():
    return "✅ CS2 Match Bot - PANDASCORE API"

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
    print(f'✅ {bot.user} is online! - PANDASCORE API')
    
    # Auto-Subscribe für alle Server
    for guild in bot.guilds:
        guild_id = str(guild.id)
        
        # Auto-Subscribe Teams
        if guild_id not in TEAMS:
            TEAMS[guild_id] = []
        
        for team in AUTO_SUBSCRIBE_TEAMS:
            if team not in TEAMS[guild_id]:
                TEAMS[guild_id].append(team)
                print(f"✅ Auto-subscribed {team} for guild {guild.name}")
    
    # ✅ KORREKT SPEICHERN
    if save_data():
        print("✅ Auto-subscribe data saved successfully!")
    else:
        print("❌ Failed to save auto-subscribe data!")
    
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    print("🔔 AUTO-SUBSCRIBE COMPLETE! Alert system started!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
