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
from bs4 import BeautifulSoup
import socket

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
    'M80': ['m80']
}

TEAM_LOGOS = {
    'Natus Vincere': 'https://liquipedia.net/commons/images/thumb/6/60/Natus_Vincere_2022.png/150px-Natus_Vincere_2022.png',
    'FaZe Clan': 'https://liquipedia.net/commons/images/thumb/5/5e/FaZe_Clan_2021.png/150px-FaZe_Clan_2021.png',
    'Team Vitality': 'https://liquipedia.net/commons/images/thumb/5/5e/Team_Vitality_2020.png/150px-Team_Vitality_2020.png',
    'G2 Esports': 'https://liquipedia.net/commons/images/thumb/5/5e/G2_Esports_2020.png/150px-G2_Esports_2020.png',
    'FURIA': 'https://liquipedia.net/commons/images/thumb/3/3c/FURIA_Esports_2020.png/150px-FURIA_Esports_2020.png',
    'MOUZ': 'https://liquipedia.net/commons/images/thumb/8/83/MOUZ_2023.png/150px-MOUZ_2023.png',
    'Team Spirit': 'https://liquipedia.net/commons/images/thumb/6/6c/Team_Spirit_2020.png/150px-Team_Spirit_2020.png',
    'Cloud9': 'https://liquipedia.net/commons/images/thumb/5/5e/Cloud9_2021.png/150px-Cloud9_2021.png',
    'Virtus.pro': 'https://liquipedia.net/commons/images/thumb/6/60/Virtus.pro_2022.png/150px-Virtus.pro_2022.png',
    'The Mongolz': 'https://liquipedia.net/commons/images/thumb/4/47/TheMongolz_allmode.png/150px-TheMongolz_allmode.png',
    '9z Team': 'https://liquipedia.net/commons/images/thumb/f/f2/9z_Team_2021.png/150px-9z_Team_2021.png',
    '3DMAX': 'https://liquipedia.net/commons/images/thumb/4/4a/3DMAX_2024.png/150px-3DMAX_2024.png',
    'Betera Esports': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png',
    'SPARTA': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png',
    'Falcons': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png',
    'Astralis': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png',
    'Aurora': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png',
    'Liquid': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png',
    'M80': 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png'
}

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    return input_team, False

def get_team_logo(team_name):
    """Find logo with better team name matching"""
    if team_name in TEAM_LOGOS:
        return TEAM_LOGOS[team_name]
    
    team_lower = team_name.lower()
    for logo_team, logo_url in TEAM_LOGOS.items():
        if (team_lower in logo_team.lower() or 
            logo_team.lower() in team_lower or
            any(word in team_lower for word in logo_team.lower().split())):
            return logo_url
    
    return 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png'

def create_centered_teams_display(team1, team2):
    """Erstelle perfekt zentrierte Team-Anzeige mit Fields"""
    # Verwende Discord Fields für die Zentrierung
    display_parts = []
    
    # Team 1 oben - FETT und groß
    display_parts.append({
        "name": "\u200b",
        "value": f"**{team1}**",
        "inline": False
    })
    
    # VS in der Mitte
    display_parts.append({
        "name": "\u200b", 
        "value": "**🆚**",
        "inline": False
    })
    
    # Team 2 unten - FETT und groß
    display_parts.append({
        "name": "\u200b",
        "value": f"**{team2}**", 
        "inline": False
    })
    
    return display_parts

# =========================
# DATA MANAGEMENT
# =========================
DATA_FILE = "bot_data.json"

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}
    except:
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 30}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

# Load initial data
data = load_data()
TEAMS = data.get("TEAMS", {})
CHANNELS = data.get("CHANNELS", {})
ALERT_TIME = data.get("ALERT_TIME", 30)

print(f"📊 Loaded: {len(TEAMS)} servers, {sum(len(teams) for teams in TEAMS.values())} teams")

# =========================
# PANDASCORE API - MIT FINALEM ZEITZONEN-FIX!
# =========================
async def fetch_pandascore_matches():
    """Fetch real matches from PandaScore API"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.pandascore.co/csgo/matches/upcoming"
            headers = {
                'Authorization': f'Bearer {PANDASCORE_TOKEN}',
                'Accept': 'application/json'
            }
            
            params = {
                'sort': 'begin_at',
                'page[size]': 20
            }
            
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
                                    # ✅ FINALER ZEITZONEN-FIX!
                                    begin_at = match_data.get('begin_at')
                                    if begin_at:
                                        match_dt = datetime.datetime.fromisoformat(begin_at.replace('Z', '+00:00'))
                                        unix_time = int(match_dt.timestamp())
                                        # ✅ Deutsche Zeitzone (CET/CEST)
                                        german_tz = timezone(timedelta(hours=2))  # Sommerzeit
                                        local_dt = match_dt.astimezone(german_tz)
                                        time_string = local_dt.strftime("%H:%M")
                                    else:
                                        continue
                                    
                                    league = match_data.get('league', {})
                                    event = league.get('name', 'CS2 Tournament')
                                    
                                    matches.append({
                                        'team1': team1,
                                        'team2': team2,
                                        'unix_time': unix_time,
                                        'event': event,
                                        'time_string': time_string,
                                        'is_live': False,
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
# ALERT SYSTEM - PERFEKTE ZENTRIERUNG MIT FELDS!
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Send match alerts - MIT FIELDS FÜR ZENTRIERUNG!"""
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
                    
                    if (match['team1'].lower() in team_variants or 
                        match['team2'].lower() in team_variants or
                        any(variant in match['team1'].lower() for variant in team_variants) or
                        any(variant in match['team2'].lower() for variant in team_variants)):
                        
                        time_until = (match['unix_time'] - current_time) / 60
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}"
                        
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            print(f"🚨 SENDING ALERT for {match['team1']} vs {match['team2']}!")
                            
                            # ✅ PERFEKT ZENTRIERTES EMBED MIT FIELDS
                            team1_logo = get_team_logo(match['team1'])
                            
                            embed = discord.Embed(
                                title=f"🎮 **MATCH STARTING IN {int(time_until)} MINUTES!** 🎮",
                                color=0x00ff00
                            )
                            
                            # Teams zentriert mit Fields
                            centered_parts = create_centered_teams_display(match['team1'], match['team2'])
                            for part in centered_parts:
                                embed.add_field(
                                    name=part["name"],
                                    value=part["value"],
                                    inline=part["inline"]
                                )
                            
                            # Tournament Info - normale Schrift
                            embed.add_field(
                                name="🏆 TOURNAMENT", 
                                value=f"{match['event']}", 
                                inline=True
                            )
                            
                            embed.add_field(
                                name="⏰ STARTS IN", 
                                value=f"{int(time_until)} MINUTES", 
                                inline=True
                            )
                            
                            embed.add_field(
                                name="🕐 TIME", 
                                value=f"{match['time_string']}", 
                                inline=True
                            )
                            
                            embed.set_thumbnail(url=team1_logo)
                            embed.set_footer(text="CS2 Match Alert • PandaScore API")
                            
                            try:
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 {role.mention} **MATCH STARTING IN {int(time_until)} MINUTES!** 🎮")
                                else:
                                    await channel.send(f"🔔 **MATCH STARTING IN {int(time_until)} MINUTES!** 🎮")
                                
                                await channel.send(embed=embed)
                                
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
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    """Subscribe to a team for alerts"""
    guild_id = str(ctx.guild.id)
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    correct_name, found = find_team_match(team)
    
    if correct_name not in TEAMS[guild_id]:
        TEAMS[guild_id].append(correct_name)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"✅ **{correct_name}** added for alerts! 🎯")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send(f"⚠️ **{correct_name}** already subscribed!")

@bot.command()
async def unsubscribe(ctx, *, team):
    """Unsubscribe from a team"""
    guild_id = str(ctx.guild.id)
    correct_name, found = find_team_match(team)
    
    if guild_id in TEAMS and correct_name in TEAMS[guild_id]:
        TEAMS[guild_id].remove(correct_name)
        if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
            await ctx.send(f"❌ **{correct_name}** removed from alerts!")
        else:
            await ctx.send("⚠️ **Save failed!**")
    else:
        await ctx.send(f"❌ **Team {correct_name} not found!**")

@bot.command()
async def list(ctx):
    """Show subscribed teams"""
    guild_id = str(ctx.guild.id)
    teams = TEAMS.get(guild_id, [])
    
    if teams:
        team_list = "\n".join([f"• **{team}**" for team in teams])
        embed = discord.Embed(
            title="📋 **SUBSCRIBED TEAMS**",
            description=team_list,
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ **No teams subscribed yet!**")

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
    """Show available matches"""
    try:
        matches = await fetch_pandascore_matches()
        
        embed = discord.Embed(
            title="🎯 **AVAILABLE CS2 MATCHES**",
            color=0x0099ff
        )
        
        if matches:
            match_list = ""
            for i, match in enumerate(matches[:6], 1):
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                match_list += f"{i}. **{match['team1']}** 🆚 **{match['team2']}**\n"
                match_list += f"   ⏰ **{int(time_until)}min** | 🏆 **{match['event']}**\n\n"
            
            embed.description = match_list
        else:
            embed.description = "❌ **No matches found**"
        
        embed.set_footer(text=f"🔔 Alert: {ALERT_TIME}min | 🔄 Check: every 2min")
        await ctx.send(embed=embed)
        
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
    """Auto-Setup für Channel und Teams"""
    guild_id = str(ctx.guild.id)
    
    # Auto-Set Channel
    channel_found = None
    for channel in ctx.guild.text_channels:
        if 'hltv' in channel.name.lower() or '💡' in channel.name:
            channel_found = channel
            break
    
    if channel_found:
        CHANNELS[guild_id] = channel_found.id
        channel_msg = f"📡 **Auto-channel set to {channel_found.mention}!**"
    else:
        channel_msg = "❌ **No HLTV channel found!**"
    
    # Auto-Subscribe Teams
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    added_teams = []
    for team in AUTO_SUBSCRIBE_TEAMS:
        if team not in TEAMS[guild_id]:
            TEAMS[guild_id].append(team)
            added_teams.append(team)
    
    if save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME}):
        if added_teams:
            teams_msg = f"✅ **Auto-subscribed {len(added_teams)} teams!**"
        else:
            teams_msg = "✅ **Teams already subscribed!**"
    else:
        teams_msg = "⚠️ **Save failed!**"
    
    await ctx.send(f"{channel_msg}\n{teams_msg}")

@bot.command()
async def status(ctx):
    """Show bot status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    guild_id = str(ctx.guild.id)
    subscribed_count = len(TEAMS.get(guild_id, []))
    
    embed = discord.Embed(title="🤖 **BOT STATUS**", color=0x00ff00)
    embed.add_field(name="**🟢 STATUS**", value="**✅ ONLINE**", inline=True)
    embed.add_field(name="**⏰ UPTIME**", value=f"**{hours}h {minutes}m**", inline=True)
    embed.add_field(name="**🔔 ALERTS**", value="**✅ ACTIVE**", inline=True)
    embed.add_field(name="**⏱️ ALERT TIME**", value=f"**{ALERT_TIME}min**", inline=True)
    embed.add_field(name="**👥 SUBSCRIBED**", value=f"**{subscribed_count} TEAMS**", inline=True)
    embed.add_field(name="**🌐 SOURCE**", value="**PANDASCORE API**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx):
    """Test alert with perfect centering"""
    # ✅ PERFEKT ZENTRIERTES TEST EMBED
    embed = discord.Embed(
        title="🎮 **TEST MATCH STARTING IN 15 MINUTES!** 🎮",
        color=0x00ff00
    )
    
    # Teams zentriert mit Fields
    centered_parts = create_centered_teams_display("BETERA ESPORTS", "SPARTA")
    for part in centered_parts:
        embed.add_field(
            name=part["name"],
            value=part["value"],
            inline=part["inline"]
        )
    
    # Tournament Info - normale Schrift
    embed.add_field(
        name="🏆 TOURNAMENT", 
        value="NODWIN Clutch Series", 
        inline=True
    )
    
    embed.add_field(
        name="⏰ STARTS IN", 
        value="15 MINUTES", 
        inline=True
    )
    
    embed.add_field(
        name="🕐 TIME", 
        value="16:00", 
        inline=True
    )
    
    embed.set_thumbnail(url=get_team_logo('BETERA ESPORTS'))
    embed.set_footer(text="CS2 Match Alert • PandaScore API")
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention} **TEST ALERT!** 🎮")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Ping command"""
    await ctx.send('🏓 **PONG!** 🎯')

# =========================
# FLASK & STARTUP - AUTO SETUP!
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
    
    # Auto-Setup für alle Server
    for guild in bot.guilds:
        guild_id = str(guild.id)
        
        # Auto-Subscribe Teams
        if guild_id not in TEAMS:
            TEAMS[guild_id] = []
        
        for team in AUTO_SUBSCRIBE_TEAMS:
            if team not in TEAMS[guild_id]:
                TEAMS[guild_id].append(team)
                print(f"✅ Auto-subscribed {team} for guild {guild.name}")
        
        # Auto-Set Channel falls vorhanden
        if guild_id not in CHANNELS:
            for channel in guild.text_channels:
                if 'hltv' in channel.name.lower() or '💡' in channel.name:
                    CHANNELS[guild_id] = channel.id
                    print(f"✅ Auto-channel set to #{channel.name} for guild {guild.name}")
                    break
    
    # Daten speichern
    save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME})
    
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    print("🔔 AUTO-SETUP COMPLETE! Alert system started!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
