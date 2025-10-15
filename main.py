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

print("🚀 Starting Discord CS2 Bot - PANDASCORE API")

# =========================
# BOT SETUP
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# =========================
# CONFIGURATION
# =========================
PANDASCORE_TOKEN = "NFG_fJz5qyUGHaWJmh-CcIeGELtI5prmh-YHWNibDTqDXR-p6sM"

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
    'TheMongolz': ['the mongolz', 'the mongolz', 'mongolz'],
    '9z Team': ['9z', '9z team'],
    'G2 Ares': ['g2 ares', 'g2'],
    'MANA eSports': ['mana', 'mana esports'],
    '3DMAX': ['3dmax'],
    'Lynn Vision': ['lynn vision', 'lynn'],
    'Team Novaq': ['novaq'],
    'AMKAL ESPORTS': ['amkal'],
    'ARCRED': ['arcred'],
    '500': ['500'],
    'AM Gaming': ['am gaming'],
    'Dynamo Eclot': ['dynamo eclot'],
    'm0nesy team': ['m0nesy']
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
    'TheMongolz': 'https://liquipedia.net/commons/images/thumb/4/47/TheMongolz_allmode.png/150px-TheMongolz_allmode.png',
    '9z Team': 'https://liquipedia.net/commons/images/thumb/f/f2/9z_Team_2021.png/150px-9z_Team_2021.png',
    'G2 Ares': 'https://liquipedia.net/commons/images/thumb/5/5e/G2_Esports_2020.png/150px-G2_Esports_2020.png',
    '3DMAX': 'https://liquipedia.net/commons/images/thumb/4/4a/3DMAX_2024.png/150px-3DMAX_2024.png'
}

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    return input_team, False

def get_team_logo(team_name):
    """Find logo with better team name matching"""
    # Direct match
    if team_name in TEAM_LOGOS:
        return TEAM_LOGOS[team_name]
    
    # Fuzzy match for similar names
    team_lower = team_name.lower()
    for logo_team, logo_url in TEAM_LOGOS.items():
        if (team_lower in logo_team.lower() or 
            logo_team.lower() in team_lower or
            any(word in team_lower for word in logo_team.lower().split())):
            return logo_url
    
    # Fallback to default CS2 logo
    return 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/150px-CS2_Default_icon.png'

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
# PANDASCORE API
# =========================
async def fetch_pandascore_matches():
    """Fetch real matches from PandaScore API"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Upcoming matches
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
                                    # Parse match time
                                    begin_at = match_data.get('begin_at')
                                    if begin_at:
                                        match_dt = datetime.datetime.fromisoformat(begin_at.replace('Z', '+00:00'))
                                        unix_time = int(match_dt.timestamp())
                                        time_string = match_dt.strftime("%H:%M")
                                    else:
                                        continue
                                    
                                    # Get tournament info
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
# ALERT SYSTEM - FIXED CHANNEL PING!
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Send match alerts - FIXED CHANNEL PING!"""
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
                    
                    # DEBUG: Print matching attempt
                    print(f"🔍 Checking {subscribed_team} vs {match['team1']} / {match['team2']}")
                    
                    if (match['team1'].lower() in team_variants or 
                        match['team2'].lower() in team_variants or
                        any(variant in match['team1'].lower() for variant in team_variants) or
                        any(variant in match['team2'].lower() for variant in team_variants)):
                        
                        time_until = (match['unix_time'] - current_time) / 60
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}"
                        
                        print(f"🎯 Match found! {match['team1']} vs {match['team2']} in {time_until:.1f}min (Alert: {ALERT_TIME}min)")
                        
                        # ✅ FIXED: Bessere Time-Window Prüfung
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            print(f"🚨 SENDING ALERT for {match['team1']} vs {match['team2']}!")
                            
                            # Create alert embed
                            team1_logo = get_team_logo(match['team1'])
                            
                            embed = discord.Embed(
                                title="\n🔔 🎮 **MATCH STARTING SOON!** 🎮\n",
                                description=f"\n## **{match['team1']}**\n\n   🆚   \n\n## **{match['team2']}**\n",
                                color=0x00ff00
                            )
                            
                            embed.set_author(name=f"\n{match['team1']} vs {match['team2']}\n", icon_url=team1_logo)
                            embed.set_thumbnail(url=team1_logo)
                            
                            embed.add_field(name="\n**🏆 TOURNAMENT**", value=f"\n**{match['event']}**\n", inline=True)
                            embed.add_field(name="\n**⏰ STARTS IN**", value=f"\n**{int(time_until)} MINUTES**\n", inline=True)
                            embed.add_field(name="\n**🕐 TIME**", value=f"\n**{match['time_string']}**\n", inline=True)
                            
                            # ✅ FIXED: SICHERER CHANNEL PING!
                            try:
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    ping_msg = await channel.send(f"\n🔔 {role.mention} **MATCH STARTING IN {int(time_until)} MINUTES!** 🎮\n")
                                    print(f"✅ Role ping sent: {ping_msg.id}")
                                else:
                                    ping_msg = await channel.send(f"\n🔔 **MATCH STARTING IN {int(time_until)} MINUTES!** 🎮\n")
                                    print(f"✅ Ping sent: {ping_msg.id}")
                                
                                embed_msg = await channel.send(embed=embed)
                                print(f"✅ Embed sent: {embed_msg.id}")
                                
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
# BOT COMMANDS (ENGLISH)
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
async def status(ctx):
    """Show bot status"""
    uptime = datetime.datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(title="🤖 **BOT STATUS**", color=0x00ff00)
    embed.add_field(name="**🟢 STATUS**", value="**✅ ONLINE**", inline=True)
    embed.add_field(name="**⏰ UPTIME**", value=f"**{hours}h {minutes}m**", inline=True)
    embed.add_field(name="**🔔 ALERTS**", value="**✅ ACTIVE**", inline=True)
    embed.add_field(name="**⏱️ ALERT TIME**", value=f"**{ALERT_TIME}min**", inline=True)
    embed.add_field(name="**👥 TEAMS**", value=f"**{sum(len(teams) for teams in TEAMS.values())}**", inline=True)
    embed.add_field(name="**🌐 SOURCE**", value="**PANDASCORE API**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx):
    """Test alert"""
    embed = discord.Embed(
        title="\n🔔 **TEST ALERT**\n",
        description=f"\n## **Natus Vincere**\n\n   🆚   \n\n## **FaZe Clan**\n",
        color=0x00ff00
    )
    embed.set_thumbnail(url=get_team_logo('Natus Vincere'))
    embed.set_author(name="\nNatus Vincere vs FaZe Clan\n", icon_url=get_team_logo('Natus Vincere'))
    embed.add_field(name="\n**🏆 TOURNAMENT**", value="\n**TEST EVENT**\n", inline=True)
    embed.add_field(name="**⏰ STARTS IN**", value="**15 MINUTES**", inline=True)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention} **TEST ALERT!** 🎮")
    await ctx.send(embed=embed)

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
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    print("🔔 FIXED Alert system started - DEBUG MODE ACTIVE!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
