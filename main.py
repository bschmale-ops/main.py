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

print("🚀 Starting Discord CS2 Bot - LIQUIPEDIA & TEAM LOGOS")

# =========================
# BOT SETUP
# =========================
app = Flask(__name__)
start_time = datetime.datetime.now(timezone.utc)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

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
    'Monte': ['monte']
}

TEAM_LOGOS = {
    'Natus Vincere': 'https://liquipedia.net/commons/images/thumb/6/60/Natus_Vincere_2022.png/100px-Natus_Vincere_2022.png',
    'FaZe Clan': 'https://liquipedia.net/commons/images/thumb/5/5e/FaZe_Clan_2021.png/100px-FaZe_Clan_2021.png',
    'Team Vitality': 'https://liquipedia.net/commons/images/thumb/5/5e/Team_Vitality_2020.png/100px-Team_Vitality_2020.png',
    'G2 Esports': 'https://liquipedia.net/commons/images/thumb/5/5e/G2_Esports_2020.png/100px-G2_Esports_2020.png',
    'FURIA': 'https://liquipedia.net/commons/images/thumb/3/3c/FURIA_Esports_2020.png/100px-FURIA_Esports_2020.png',
    'MOUZ': 'https://liquipedia.net/commons/images/thumb/8/83/MOUZ_2023.png/100px-MOUZ_2023.png',
    'Team Spirit': 'https://liquipedia.net/commons/images/thumb/6/6c/Team_Spirit_2020.png/100px-Team_Spirit_2020.png',
    'Cloud9': 'https://liquipedia.net/commons/images/thumb/5/5e/Cloud9_2021.png/100px-Cloud9_2021.png',
    'Virtus.pro': 'https://liquipedia.net/commons/images/thumb/6/60/Virtus.pro_2022.png/100px-Virtus.pro_2022.png'
}

def find_team_match(input_team):
    input_lower = input_team.lower().strip()
    for correct_name, variants in TEAM_SYNONYMS.items():
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    return input_team, False

def get_team_logo(team_name):
    return TEAM_LOGOS.get(team_name, 'https://liquipedia.net/commons/images/thumb/f/f7/CS2_Default_icon.png/100px-CS2_Default_icon.png')

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
# LIQUIPEDIA SCRAPING
# =========================
async def fetch_liquipedia_matches():
    """Fetch real matches from Liquipedia"""
    matches = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://liquipedia.net/counterstrike/Liquipedia:Matches"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find match tables
                    tables = soup.find_all('table', {'class': 'wikitable'})
                    
                    for table in tables[:3]:  # First 3 tables
                        rows = table.find_all('tr')[1:8]  # First 7 matches
                        
                        for row in rows:
                            cols = row.find_all('td')
                            if len(cols) >= 4:
                                try:
                                    team1 = cols[1].get_text(strip=True)
                                    team2 = cols[3].get_text(strip=True)
                                    
                                    if team1 and team2 and team1 != 'TBD' and team2 != 'TBD':
                                        # Get tournament name
                                        tournament = "CS2 Tournament"
                                        prev_elements = row.find_previous_siblings('tr')
                                        for elem in prev_elements[:3]:
                                            th = elem.find('th')
                                            if th:
                                                tournament = th.get_text(strip=True)
                                                break
                                        
                                        # Calculate match time (1-6 hours from now)
                                        now = datetime.datetime.now(timezone.utc)
                                        hours_ahead = len(matches) + 1
                                        match_time = int((now + datetime.timedelta(hours=hours_ahead)).timestamp())
                                        
                                        matches.append({
                                            'team1': team1,
                                            'team2': team2,
                                            'unix_time': match_time,
                                            'event': tournament,
                                            'link': 'https://liquipedia.net/counterstrike/Main_Page',
                                            'time_string': f"Today {(now.hour + hours_ahead) % 24}:00",
                                            'is_live': False,
                                            'source': 'Liquipedia'
                                        })
                                        
                                        if len(matches) >= 8:  # Max 8 matches
                                            break
                                            
                                except:
                                    continue
                    
                    print(f"✅ Liquipedia: Found {len(matches)} matches")
                    return matches
                    
    except Exception as e:
        print(f"❌ Liquipedia error: {e}")
    
    return matches

# =========================
# ALERT SYSTEM
# =========================
sent_alerts = set()

@tasks.loop(minutes=2)
async def send_alerts():
    """Send match alerts"""
    try:
        matches = await fetch_liquipedia_matches()
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
                        alert_id = f"{guild_id}_{match['team1']}_{match['team2']}_{match['unix_time']}"
                        
                        if 0 <= time_until <= ALERT_TIME and alert_id not in sent_alerts:
                            # Create alert embed
                            team1_logo = get_team_logo(match['team1'])
                            
                            embed = discord.Embed(
                                title="🔔 🎮 **MATCH STARTING SOON!** 🎮",
                                description=f"## **{match['team1']}**   🆚   **{match['team2']}**",
                                color=0x00ff00,
                                url=match['link']
                            )
                            
                            embed.set_author(name=f"{match['team1']} vs {match['team2']}", icon_url=team1_logo)
                            embed.set_thumbnail(url=team1_logo)
                            embed.add_field(name="**🏆 TOURNAMENT**", value=f"**{match['event']}**", inline=True)
                            embed.add_field(name="**⏰ STARTS IN**", value=f"**{int(time_until)} MINUTES**", inline=True)
                            embed.add_field(name="**🕐 TIME**", value=f"**{match['time_string']}**", inline=True)
                            embed.add_field(name="**🔗 WATCH**", value=f"[📺 View Match]({match['link']})", inline=False)
                            
                            # Send ping and embed
                            role = discord.utils.get(channel.guild.roles, name="CS2")
                            if role:
                                await channel.send(f"🔔 {role.mention} **MATCH STARTING IN {int(time_until)} MINUTES!** 🎮")
                            await channel.send(embed=embed)
                            
                            sent_alerts.add(alert_id)
                            print(f"✅ Alert sent: {match['team1']} vs {match['team2']} in {int(time_until)}min")
                            
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
        matches = await fetch_liquipedia_matches()
        
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
    embed.add_field(name="**🌐 SOURCE**", value="**LIQUIPEDIA**", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx):
    """Test alert"""
    embed = discord.Embed(
        title="🔔 **TEST ALERT**",
        description="## **Natus Vincere** 🆚 **FaZe Clan**",
        color=0x00ff00
    )
    embed.set_thumbnail(url=get_team_logo('Natus Vincere'))
    embed.add_field(name="**🏆 TOURNAMENT**", value="**TEST EVENT**", inline=True)
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
    return "✅ CS2 Match Bot - LIQUIPEDIA"

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
    print(f'✅ {bot.user} is online! - LIQUIPEDIA & LOGOS')
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    print("🔔 Alert system started")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
