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

print("🚀 Starting Discord CS2 Bot - PANDASCORE API")

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
    bot.add_view(RoleButtonsView())
    bot.add_view(MoreGamesView())
    print("✅ Role Buttons persistent gemacht!")

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
        if input_lower in [v.lower() for v in variants] or input_lower == correct_name.lower():
            return correct_name, True
    
    # 2. Dann in TEAM_DISPLAY_NAMES suchen (für Main Teams ohne Synonyms)
    for team_name in TEAM_DISPLAY_NAMES.keys():
        if input_lower == team_name.lower():
            return team_name, True
    
    return input_team, False

def get_display_name(team_name):
    """Get team name with emoji for display"""
    # Zuerst nach EXAKTEN Matches suchen
    if team_name in TEAM_DISPLAY_NAMES:
        return TEAM_DISPLAY_NAMES[team_name]
    
    # Dann nach längeren Namen suchen (G2 Ares vor G2)
    sorted_names = sorted(TEAM_DISPLAY_NAMES.keys(), key=len, reverse=True)
    
    for display_name in sorted_names:
        if display_name.upper() in team_name.upper() or team_name.upper() in display_name.upper():
            return TEAM_DISPLAY_NAMES[display_name]
    
    return TEAM_DISPLAY_NAMES.get(team_name, f"{team_name.upper()}")
def get_team_emoji(team_name):
    """Get only the emoji part - mit Regex für Emojis"""
    display = get_display_name(team_name)
    
    # Finde Custom Emojis (Format: <:name:ID>)
    import re
    emoji_match = re.search(r'<:[a-zA-Z0-9_]+:\d+>', display)
    if emoji_match:
        return emoji_match.group()
    return ""

def get_team_name_only(team_name):
    """Get only the name part - komplett nach dem Emoji"""
    display = get_display_name(team_name)
    
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
# PANDASCORE API
# =========================
async def fetch_pandascore_matches():
    matches = []
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.pandascore.co/csgo/matches/upcoming"
            headers = {'Authorization': f'Bearer {PANDASCORE_TOKEN}'}
            params = {'sort': 'begin_at', 'page[size]': 20}
            
            async with session.get(url, headers=headers, params=params, timeout=15) as response:
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
                        except:
                            continue
                    return matches
                else:
                    return []
    except Exception as e:
        print(f"❌ PandaScore error: {e}")
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
                            team1_display = get_display_name(match['team1'])
                            team2_display = get_display_name(match['team2'])
                            
                            # Teams UND VS mit # für große Schrift + LEERE ZEILE (wie in /test)
                            centered_display = (
                                f"# {team1_display}\n"
                                f"# <:VS:1428145739443208305>\n"
                                f"#  {team2_display}\n"
                                f"** **"  # Unsichtbare Zeile mit Leerzeichen zwischen **
                            )
                            
                            # Finale Formatierung mit Emojis und ABSATZ
                            match_content = (
                                f"\n{centered_display}\n\n"
                                f"**🏆 {match['event']}**\n"
                                f"**⏰ Starts in {int(time_until)} minutes{' ':>15}🕐 {match['time_string']}**"
                            )
                            
                            framed_message = create_frame(f"🎮 **MATCH ALERT • {int(time_until)} MINUTES**", match_content)
                            
                            try:
                                role = discord.utils.get(channel.guild.roles, name="CS2")
                                if role:
                                    await channel.send(f"🔔 {role.mention}\n{framed_message}")
                                else:
                                    await channel.send(framed_message)
                                
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
    """Tägliche DM um 12:30 Uhr"""
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
# BOT COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    
    correct_name, found = find_team_match(team)
    
    # TEAM VALIDIERUNG: Wenn Team nicht gefunden wurde
    if not found:
        await ctx.send(f"❌ **Team '{team}' nicht gefunden!**")
        return
    
    # Normales Subscribe
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
    """Show subscribed teams - MIT RAHMEN und FETTEN Teamnamen"""
    guild_id = str(ctx.guild.id)
    teams = TEAMS.get(guild_id, [])
    
    if teams:
        team_list = "\n".join([f"• **{get_display_name(team)}**" for team in teams])
        framed_message = create_frame("📋 SUBSCRIBED TEAMS", team_list)
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
    """Show available matches - MIT RAHMEN"""
    try:
        matches = await fetch_pandascore_matches()
        
        if matches:
            match_list = ""
            for match in matches[:6]:
                time_until = (match['unix_time'] - datetime.datetime.now(timezone.utc).timestamp()) / 60
                
                team1_emoji = get_team_emoji(match['team1'])
                team1_name = get_team_name_only(match['team1'])
                team2_emoji = get_team_emoji(match['team2'])
                team2_name = get_team_name_only(match['team2'])
                
                # Team vs Team Zeile komplett in FETT mit ** am Anfang und Ende
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
        f"🌐 SOURCE: PANDASCORE API"
    )
    
    framed_message = create_frame("🤖 BOT STATUS", status_content)
    await ctx.send(framed_message)

@bot.command()
async def test(ctx):
    """Test alert - MIT RAHMEN und korrekter Formatierung"""
    team1_display = get_display_name("Falcons")
    team2_display = get_display_name("Team Vitality")
    
    # Teams UND VS mit # für große Schrift + LEERE ZEILE
    centered_display = (
        f"# {team1_display}\n"
        f"# <:VS:1428145739443208305>\n"
        f"#  {team2_display}\n"
        f"** **"  # Unsichtbare Zeile mit Leerzeichen zwischen **
    )
    
    # Tournament und Zeit OHNE # aber FETT mit Emojis
    test_content = (
        f"\n{centered_display}\n\n"
        f"**🏆 NODWIN Clutch Series**\n"
        f"**⏰ Starts in 15 minutes{' ':>15}🕐 16:00**"
    )
    
    framed_message = create_frame("🎮 **TEST ALERT • 15 MINUTES**", test_content)
    
    role = discord.utils.get(ctx.guild.roles, name="CS2")
    if role:
        await ctx.send(f"🔔 {role.mention}\n{framed_message}")
    else:
        await ctx.send(framed_message)
        
@bot.command()
async def ping(ctx):
    await ctx.send('🏓 **PONG!** 🎯')

# =========================
# DEBUG COMMANDS
# =========================
@bot.command()
async def debug(ctx, *, team):
    """Debug command um Team-Namen zu checken"""
    display = get_display_name(team)
    emoji = get_team_emoji(team)
    name_only = get_team_name_only(team)
    
    await ctx.send(
        f"**Input:** {team}\n"
        f"**Display:** {display}\n"
        f"**Emoji:** {emoji}\n"
        f"**Name Only:** {name_only}"
    )

@bot.command()
async def rawmatches(ctx):
    """Zeigt rohe PandaScore Daten"""
    matches = await fetch_pandascore_matches()
    
    if not matches:
        await ctx.send("❌ **No matches found**")
        return
        
    for match in matches[:3]:  # Nur erste 3 Matches
        await ctx.send(
            f"**Team1:** `{match['team1']}`\n"
            f"**Team2:** `{match['team2']}`\n"
            f"**Event:** {match['event']}\n"
            f"**Time:** {match['time_string']}\n"
            f"---"
        )

# =========================
# ROLE BUTTONS SYSTEM
# =========================
class RoleButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    # REIHE 0: CS2
    @discord.ui.button(label="CS 2", emoji="<:cs2:1298250987483697202>", style=discord.ButtonStyle.secondary, custom_id="role_cs2", row=0)
    async def cs2_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "CS 2")
    
    # REIHE 1: Valorant
    @discord.ui.button(label="Valorant", emoji="<:valorant:1298251760720150550>", style=discord.ButtonStyle.secondary, custom_id="role_valorant", row=1)
    async def valorant_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Valorant")
    
    # REIHE 2: LEER (Absatz) - Keine Buttons
    
    # REIHE 3: TEXT-Button (Disabled Button als Überschrift)
    @discord.ui.button(label="🎮 Other Games", style=discord.ButtonStyle.secondary, custom_id="text_other_games", row=3, disabled=True)
    async def text_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # Keine Aktion, nur Text
    
    # REIHE 4: Erste 5 andere Spiele
    @discord.ui.button(label="League of Legends", emoji="<:lol:1298252270240272416>", style=discord.ButtonStyle.secondary, custom_id="role_lol", row=4)
    async def lol_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "League of Legends")
    
    @discord.ui.button(label="Apex Legends", emoji="<:apex:1298251721184772119>", style=discord.ButtonStyle.secondary, custom_id="role_apex", row=4)
    async def apex_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Apex Legends")
    
    @discord.ui.button(label="Call of Duty", emoji="<:cod:1298251740965109770>", style=discord.ButtonStyle.secondary, custom_id="role_cod", row=4)
    async def cod_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Call of Duty")
    
    @discord.ui.button(label="Diablo 4", emoji="<:d4:1304002853253152799>", style=discord.ButtonStyle.secondary, custom_id="role_diablo", row=4)
    async def diablo_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Diablo 4")
    
    @discord.ui.button(label="Tibia", emoji="<:tibia:1305455884201103393>", style=discord.ButtonStyle.secondary, custom_id="role_tibia", row=4)
    async def tibia_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Tibia")

    async def assign_role(self, interaction: discord.Interaction, role_name: str):
        await interaction.response.defer(ephemeral=True)
        
        try:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                role = await interaction.guild.create_role(name=role_name, mentionable=True, color=discord.Color.blue())
            
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.followup.send(f"❌ {role_name} Rolle entfernt!", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"✅ {role_name} Rolle hinzugefügt!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)

# ZWEITER VIEW FÜR RESTLICHE SPIELE
class MoreGamesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    # REIHE 0: Weitere 5 Spiele
    @discord.ui.button(label="PUBG", emoji="<:pubg:1305772146861277255>", style=discord.ButtonStyle.secondary, custom_id="role_pubg", row=0)
    async def pubg_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "PUBG")
    
    @discord.ui.button(label="Rust", emoji="<:rust:1305456246996078614>", style=discord.ButtonStyle.secondary, custom_id="role_rust", row=0)
    async def rust_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Rust")
    
    @discord.ui.button(label="Fortnite", emoji="<:fortnite:1305772894336450571>", style=discord.ButtonStyle.secondary, custom_id="role_fortnite", row=0)
    async def fortnite_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Fortnite")
    
    @discord.ui.button(label="Rainbow Six Siege", emoji="<:r6:1305774806083305515>", style=discord.ButtonStyle.secondary, custom_id="role_r6", row=0)
    async def r6_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Rainbow Six Siege")
    
    @discord.ui.button(label="Overwatch", emoji="<:overwatch:1305773706471276554>", style=discord.ButtonStyle.secondary, custom_id="role_overwatch", row=0)
    async def overwatch_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Overwatch")
    
    # REIHE 1: Letzte 2 Spiele
    @discord.ui.button(label="World of Warcraft", emoji="<:wow:1305809271992352809>", style=discord.ButtonStyle.secondary, custom_id="role_wow", row=1)
    async def wow_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "World of Warcraft")
    
    @discord.ui.button(label="Halo 2", emoji="<:halo2:1305775045204770846>", style=discord.ButtonStyle.secondary, custom_id="role_halo", row=1)
    async def halo_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "Halo 2")

    async def assign_role(self, interaction: discord.Interaction, role_name: str):
        await interaction.response.defer(ephemeral=True)
        
        try:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                role = await interaction.guild.create_role(name=role_name, mentionable=True, color=discord.Color.blue())
            
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.followup.send(f"❌ {role_name} Rolle entfernt!", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"✅ {role_name} Rolle hinzugefügt!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)

# =========================
# ROLE BUTTONS COMMAND
# =========================
@bot.command()
async def createroles(ctx):
    """Erstelle die Game-Role Buttons in diesem Channel"""
    embed = discord.Embed(
        title="🎮 **Choose Your Games**",
        description="Click the buttons to add/remove game roles\nYou will be pinged for matches of your selected games!\n\n** **",
        color=0x5865F2
    )
    
    await ctx.send(embed=embed, view=RoleButtonsView())
    await ctx.send(view=MoreGamesView())

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
    
    save_data()
    
    await asyncio.sleep(2)
    if not send_alerts.is_running():
        send_alerts.start()
    if not daily_dm_reminder.is_running():
        daily_dm_reminder.start()
    print("🔔 Alert system started!")
    print("⏰ Daily DM reminder started!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
