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
    'Falcons': '<:falcons:1428075105615085598> Falcons',
    'MOUZ': '<:mouz:1428075167850041425> MOUZ',
    'Team Spirit': '<:spirit:1428075208564019302> Team Spirit',
    'Team Vitality': '<:vitality:1428075243510956113> Team Vitality',
    'The Mongolz': '<:themongolz:1428075231939133581> The Mongolz',
    'FURIA': '<:furia:1428075132156641471> FURIA',
    'Natus Vincere': '<:navi:1428075186976194691> Natus Vincere',
    'FaZe': '<:faze:1428075117753401414> FaZe',
    '3DMAX': '<:3dmax:1428075077408133262> 3DMAX',
    'Astralis': '<:astralis:1428075043526672394> Astralis',
    'G2': '<:g2:1428075144240431154> G2',
    'Aurora': '<:aurora:1428075062287798272> Aurora',
    'Liquid': '<:liquid:1428075155456000122> Liquid',
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
    'SPARTA': ['sparta'],
    'Falcons': ['falcons'],
    'Astralis': ['astralis'],
    'Aurora': ['aurora'],
    'Liquid': ['liquid'],
    'M80': ['m80'}

# Temporäre Teams (nur während Laufzeit)
TEMP_TEAMS = []

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    return input_team, False

def get_display_name(team_name):
    """Get team name with emoji for display, with fallback if emoji fails"""
    display = TEAM_DISPLAY_NAMES.get(team_name, f"{team_name}")
    if ' ' in display and not display.startswith('<'):
        print(f"⚠️ Emoji for {team_name} might be invalid: {display}")
        return team_name  # Fallback auf reinen Namen
    return display

def validate_team_display():
    """Validate the structure of TEAM_DISPLAY_NAMES and log potential issues"""
    for team, display in TEAM_DISPLAY_NAMES.items():
        if ' ' not in display:
            print(f"⚠️ Warning: Team '{team}' has an invalid display format: '{display}' (no space between emoji and name)")
        elif not display.startswith('<:') and not display.startswith('<a:'):
            print(f"⚠️ Warning: Team '{team}' has an invalid emoji format: '{display}' (does not start with <: or <a:)")

def get_team_emoji(team_name):
    """Get only the emoji part of the display name"""
    display = TEAM_DISPLAY_NAMES.get(team_name, f"{team_name}")
    if ' ' in display:
        return display[:display.index(' ')]
    return ""

def get_team_name(team_name):
    """Get only the name part of the display name, handling multiple words"""
    display = TEAM_DISPLAY_NAMES.get(team_name, f"{team_name}")
    if ' ' in display:
        return display[display.index(' ') + 1:]
    return display

def center_vs(team1, team2, separator="<:VS:1428106772312227984>", emoji_visual_width=2):
    # Maximale Länge: Teamnamen oder Separator (berücksichtigt visuelle Breite)
    max_len = max(len(team1), len(team2), emoji_visual_width if separator == "🆚" else len(separator))
    line1 = team1.center(max_len)
    line2 = separator.center(max_len)
    line3 = team2.center(max_len)
    return f"{line1}\n{line2}\n{line3}"

def create_centered_teams_display(team1, team2):
    """Erstelle perfekt zentrierte Team-Anzeige"""
    team1_display = get_display_name(team1)
    team2_display = get_display_name(team2)
    centered_display = center_vs(team1_display, team2_display)
    return centered_display

def create_frame(title, content):
    """Erstelle einen Rahmen für Textnachrichten (für Debug oder Text-Ausgabe)"""
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

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved data to {DATA_FILE}: {len(data.get('TEAMS', {}))} servers")
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
# ALERT SYSTEM - ALS EMBED MIT MAXIMALER GRÖSSE
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Send match alerts as Embed with maximum size"""
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

            all_teams = subscribed_teams + [t for t in TEMP_TEAMS if t not in subscribed_teams]
            for match in matches:
                for subscribed_team in all_teams:
                    correct_name, found = find_team_match(subscribed_team)
                    team_variants = [correct_name.lower()] + [v.lower() for v in TEAM_SYNONYMS.get(correct_name, [])]
                    if (match['team1'].lower() in team_variants or match['team2'].lower() in team_variants or
                        any(variant in match['team1'].lower() for variant in team_variants) or
                        any(variant in match['team2'].lower() for variant in team_variants)):
                        time_until = (match['unix_time'] - current_time) / 60
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}"
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            print(f"🚨 SENDING ALERT for {match['team1']} vs {match['team2']}!")
                            centered_display = create_centered_teams_display(match['team1'], match['team2'])
                            embed = discord.Embed(
                                title=f"🎮 **MATCH ALERT** • {int(time_until)} MINUTES",
                                description=f"\n\n{centered_display}\n\n\n*🏆 {match['event']}*\n*⏰ Starts in {int(time_until)} minutes*\n*🕐 {match['time_string']}*",
                                color=0x00ff00,
                                timestamp=datetime.datetime.now(timezone.utc)
                            )
                            embed.set_footer(text=f"Powered by PandaScore | Alert ID: {alert_id}")
                            try:
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 {role.mention}", embed=embed)
                                else:
                                    await channel.send(embed=embed)
                                print(f"✅ Alert sent: {embed.to_dict()}")
                            except Exception as e:
                                print(f"❌ Failed to send message: {e}")
                                continue
                            sent_alerts.add(alert_id)
                            print(f"✅ Alert tracked: {match['team1']} vs {match['team2']} in {int(time_until)}min")
                            if len(sent_alerts) > 50:
                                sent_alerts.clear()
                            break
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Subscribe to a team for alerts (temporär oder persistent)"""
    guild_id = str(ctx.guild.id)
    print(f"Debug subscribe: guild_id={guild_id}, team_input={team}")
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
        print(f"Debug subscribe: Created new list for guild {guild_id}")
    correct_name, found = find_team_match(team)
    print(f"Debug subscribe: correct_name={correct_name}, found={found}")
    if correct_name not in TEAMS[guild_id] and correct_name not in TEMP_TEAMS:
        TEMP_TEAMS.append(correct_name)
        print(f"Debug subscribe: Added {correct_name} to TEMP_TEAMS, list now: {TEMP_TEAMS}")
        await ctx.send(f"✅ **{get_display_name(correct_name)}** added for alerts (temporär)! 🎯")
    elif correct_name in TEAMS[guild_id]:
        await ctx.send(f"⚠️ **{get_display_name(correct_name)}** is already permanently subscribed!")
    else:
        await ctx.send(f"⚠️ **{get_display_name(correct_name)}** is already temporarily subscribed!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Unsubscribe from a team"""
    guild_id = str(ctx.guild.id)
    correct_name, found = find_team_match(team)
    if correct_name in TEMP_TEAMS:
        TEMP_TEAMS.remove(correct_name)
        print(f"Debug unsubscribe: Removed {correct_name} from TEMP_TEAMS, list now: {TEMP_TEAMS}")
        await ctx.send(f"❌ **{get_display_name(correct_name)}** removed from temporary alerts!")
    elif guild_id in TEAMS and correct_name in TEAMS[guild_id]:
        TEAMS[guild_id].remove(correct_name)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"❌ **{get_display_name(correct_name)}** removed from permanent alerts!")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send(f"❌ **Team {get_display_name(correct_name)} not found!**")

@bot.command()
async def list(ctx):
    """Show subscribed teams as an Embed list"""
    guild_id = str(ctx.guild.id)
    print(f"Debug list: guild_id={guild_id}, raw TEAMS={TEAMS.get(guild_id, [])}, TEMP_TEAMS={TEMP_TEAMS}")
    teams = TEAMS.get(guild_id, [])
    all_teams = teams + [t for t in TEMP_TEAMS if t not in teams]
    if not all_teams:
        print(f"Debug list: No teams for guild {guild_id}")
        await ctx.send("❌ **No teams subscribed yet!**")
        return
    print(f"Debug list: Found {len(teams)} permanent + {len(TEMP_TEAMS)} temporary teams")
    team_list = "\n".join([f"• {get_display_name(team)}" for team in all_teams])
    embed = discord.Embed(
        title="📋 **SUBSCRIBED TEAMS**",
        description=team_list,
        color=0x00ff00,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Total Teams: {len(all_teams)} | Updated: {datetime.datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M')}")
    await ctx.send(embed=embed)

@bot.command()
async def settime(ctx, minutes: int):
    """Set alert time in minutes"""
    global ALERT_TIME
    if 1 <= minutes <= 240:
        ALERT_TIME = minutes
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"⏰ **Alert time set to {minutes} minutes!** 🔔")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send("❌ **Please specify 1-240 minutes!**")

@bot.command()
async def matches(ctx):
    """Show available matches as Embed"""
    try:
        matches = await fetch_pandascore_matches()
        if matches:
            match_list = "\n".join([f"{i}. {get_display_name(match['team1'])} <:VS:1428106772312227984> {get_display_name(match['team2'])}\n   *⏰ {int((match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60)}min | 🏆 {match['event']}*"
                                  for i, match in enumerate(matches[:6], 1)])
            embed = discord.Embed(
                title="🎯 **AVAILABLE CS2 MATCHES**",
                description=match_list,
                color=0x00ff00,
                timestamp=datetime.datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"🔔 Alert: {ALERT_TIME}min | 🔄 Check: every 2min")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ **No matches found**")
    except Exception as e:
        await ctx.send(f"❌ **Error:** {e}")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    """Set alert channel"""
    CHANNELS[str(ctx.guild.id)] = channel.id
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        await ctx.send(f"📡 **Alert channel set to {channel.mention}!** ✅")
    else:
        await ctx.send("⚠️ **Save failed!**")

@bot.command()
async def autosetup(ctx):
    """Auto-Subscribe Teams"""
    guild_id = str(ctx.guild.id)
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    added_teams = []
    for team in AUTO_SUBSCRIBE_TEAMS:
        if team not in TEAMS[guild_id]:
            TEAMS[guild_id].append(team)
            added_teams.append(team)
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
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
    subscribed_count = len(TEAMS.get(guild_id, [])) + len([t for t in TEMP_TEAMS if t not in TEAMS.get(guild_id, [])])
    status_content = (
        f"**🟢 STATUS:** **✅ ONLINE**\n"
        f"**⏰ UPTIME:** **{hours}h {minutes}m**\n"
        f"**🔔 ALERTS:** **✅ ACTIVE**\n"
        f"**⏱️ ALERT TIME:** **{ALERT_TIME}min**\n"
        f"**👥 SUBSCRIBED:** **{subscribed_count} TEAMS**\n"
        f"**🌐 SOURCE:** **PANDASCORE API**"
    )
    embed = discord.Embed(
        title="🤖 **BOT STATUS**",
        description=status_content,
        color=0x00ff00,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx):
    """Test alert with Embed, better spacing and centering"""
    centered_display = create_centered_teams_display("Falcons", "Team Vitality")
    
    embed = discord.Embed(
        title="🎮 **TEST ALERT** • 15 MINUTES",
        description=f"\n\n{centered_display}\n\n\n*🏆 NODWIN Clutch Series*\n*⏰ Starts in 15 minutes*\n*🕐 16:00*",
        color=0x00ff00,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    embed.set_footer(text="Test Alert | Powered by xAI")
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention}", embed=embed)
    else:
        await ctx.send(embed=embed)

@bot.command()
async def debug(ctx):
    """Debug: Test Zentrierung und Emojis"""
    centered_display = create_centered_teams_display("Team Spirit", "The Mongolz")
    await ctx.send(f"**Debug Output:**\n{centered_display}")

@bot.command()
async def ping(ctx):
    """Ping command"""
    await ctx.send('🏓 **PONG!** 🎯')

# =========================
# FLASK & STARTUP
# =========================
@app.route('/')
def home():
    return "✅ CS2 Match Bot - PANDASCORE API"

@app.route('/health')
def health():
    return jsonify({
        "status": "online", 
        "teams": sum(len(teams) for teams in TEAMS.values()) + len(TEMP_TEAMS),
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
    for guild in bot.guilds:
        guild_id = str(guild.id)
        if guild_id not in TEAMS:
            TEAMS[guild_id] = []
        for team in AUTO_SUBSCRIBE_TEAMS:
            if team not in TEAMS[guild_id]:
                TEAMS[guild_id].append(team)
                print(f"✅ Auto-subscribed {team} for guild {guild.name}")
    save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME})
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
