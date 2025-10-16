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

# Team Display Names mit ALLEN Emoji-IDs
TEAM_DISPLAY_NAMES = {
    # Original Teams
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
    
    # Neue Teams
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
    'NINJAS IN PYJAMAS': '<:nip:1428264779507830824> NINJAS IN PYJAMAS',
    'NINJAS IN PYJAMAS IMPACT': '<:nip:1428264779507830824> NINJAS IN PYJAMAS IMPACT',
    'paiN': '<:pain:1428264796012417077> PAIN',
    'SAW': '<:saw:1428264807496417341> SAW',
    'TYLOO': '<:tyloo:1428264914367021198> TYLOO',
    'Virtus.pro': '<:virtuspro:1428266203474034748> VIRTUS.PRO',
    'Legacy': '<:legacy:1428269690001821766> LEGACY',
    
    # Neue Teams aus Matches
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
    'Natus Vincere': ['navi'],
    'FaZe Clan': ['faze'], 
    'Team Vitality': ['vitality'],
    'G2 Esports': ['g2'],
    'MOUZ': ['mouz'],
    'Team Spirit': ['spirit'],
    'FURIA': ['furia'],
    'Falcons': ['falcons'],
    'Astralis': ['astralis'],
    'Aurora': ['aurora'],
    'Liquid': ['liquid'],
    'M80': ['m80'],
    'Complexity': ['complexity', 'col'],
    'Heroic': ['heroic'],
    'Fnatic': ['fnatic'],
    'Virtus.pro': ['virtus pro', 'vp'],
    'Ninjas in Pyjamas': ['nip', 'ninjas in pyjamas', 'ninjas in pyjamas impact', 'ninjas in pyjamas'],
    'NINJAS IN PYJAMAS': ['nip impact', 'ninjas impact'],
    'paiN': ['pain'],
    'Legacy': ['legacy']
}

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    return input_team, False

def get_display_name(team_name):
    return TEAM_DISPLAY_NAMES.get(team_name, f"{team_name.upper()}")

def center_vs(team1, team2, separator="<:VS:1428145739443208305>"):
    """Einfache Zentrierung"""
    team1_line = f"#{team1:^27}"[:29]
    vs_line = f"#{separator:^27}"[:29]
    team2_line = f"#{team2:^27}"[:29]
    return f"{team1_line}\n{vs_line}\n{team2_line}\n#\n#"

def create_frame(title, content):
    rahmen_laenge = 29
    linie = "━" * rahmen_laenge
    return f"{linie}\n{title}\n{linie}\n{content}\n{linie}"

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
    except:
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved data to {DATA_FILE}: {len(TEAMS)} servers")
        return True
    except Exception as e:
        print(f"❌ Save error: {e}")
        return False

# Load initial data
data = load_data()
TEAMS = data.get("TEAMS", {})
CHANNELS = data.get("CHANNELS", {})
ALERT_TIME = data.get("ALERT_TIME", 30)

print(f"📊 Loaded: {len(TEAMS)} servers, {sum(len(teams) for teams in TEAMS.values())} teams")

# =========================
# PANDASCORE API
# =========================
async def fetch_pandascore_matches():
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
                                        german_tz = timezone(timedelta(hours=2))
                                        local_dt = match_dt.astimezone(german_tz)
                                        time_string = local_dt.strftime("%H:%M")
                                        
                                        league = match_data.get('league', {})
                                        event = league.get('name', 'CS2 Tournament')
                                        
                                        matches.append({
                                            'team1': team1, 'team2': team2, 'unix_time': unix_time,
                                            'event': event, 'time_string': time_string
                                        })
                                        print(f"✅ Found: {team1} vs {team2} at {time_string}")
                        except:
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
# ALERT SYSTEM
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    try:
        matches = await fetch_pandascore_matches()
        current_time = datetime.datetime.now(timezone.utc).timestamp()
        
        print(f"🔍 Checking {len(matches)} matches for alerts...")
        
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
                        match['team2'].lower() in team_variants or
                        any(variant in match['team1'].lower() for variant in team_variants) or
                        any(variant in match['team2'].lower() for variant in team_variants)):
                        
                        time_until = (match['unix_time'] - current_time) / 60
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}"
                        
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            print(f"🚨 SENDING ALERT for {match['team1']} vs {match['team2']}!")
                            
                            centered_display = center_vs(get_display_name(match['team1']), get_display_name(match['team2']))
                            
                            match_content = (
                                f"\n{centered_display}\n"
                                f"# 🏆 {match['event']}\n"
                                f"# ⏰ Starts in {int(time_until)} minutes{' ' * 15}🕐 {match['time_string']}"
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
                                
                                sent_alerts.add(alert_id)
                                print(f"✅ Alert sent: {match['team1']} vs {match['team2']} in {int(time_until)}min")
                                
                                if len(sent_alerts) > 50:
                                    sent_alerts.clear()
                                    
                            except Exception as e:
                                print(f"❌ Failed to send message: {e}")
                            break
        
    except Exception as e:
        print(f"❌ Alert error: {e}")

# =========================
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    correct_name, found = find_team_match(team)
    
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
        team_list = "\n".join([f"• {get_display_name(team)}" for team in teams])
        framed_message = create_frame("📋 **SUBSCRIBED TEAMS**", team_list)
        await ctx.send(framed_message)
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
    centered_display = center_vs(get_display_name("Falcons"), get_display_name("Team Vitality"))
    
    test_content = (
        f"\n{centered_display}\n"
        f"# 🏆 NODWIN Clutch Series\n"
        f"# ⏰ Starts in 15 minutes{' ' * 15}🕐 16:00"
    )
    
    framed_message = create_frame("🎮 **TEST ALERT** • 15 MINUTES", test_content)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention}\n{framed_message}")
    else:
        await ctx.send(framed_message)

@bot.command()
async def ping(ctx):
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
    
    for guild in bot.guilds:
        guild_id = str(guild.id)
        
        if guild_id not in TEAMS:
            TEAMS[guild_id] = []
        
        for team in AUTO_SUBSCRIBE_TEAMS:
            if team not in TEAMS[guild_id]:
                TEAMS[guild_id].append(team)
                print(f"✅ Auto-subscribed {team} for guild {guild.name}")
    
    if save_data():
        print("✅ Auto-subscribe data saved successfully!")
    
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    print("🔔 Alert system started!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
