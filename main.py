import discord
from discord.ext import commands, tasks
import requests
import time
import asyncio
import os

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Config (speichert per Server)
TEAMS = {}  # {guild_id: [team1, team2, ...]}
CHANNELS = {}  # {guild_id: channel_id}
ALERT_TIME = 5  # Default 5 Min. Vorlauf (in Minuten, änderbar)

# PandaScore Config
API_KEY = 'DEIN_PANDASCORE_API_KEY'  # Ersetze mit deinem PandaScore API-Key
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

# HLTV Scraping ersetzen durch PandaScore API
def get_upcoming_matches():
    matches = []
    url = 'https://api.pandascore.co/matches/upcoming'
    params = {
        'video_game': 'counter-strike-2',
        'filter[future]': 'true',
        'page[size': 50
    }  # 50 Matches pro Call

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for match in data:
                team1 = match.get('opponents', [{}])[0].get('opponent', {}).get('name', 'TBD')
                team2 = match.get('opponents', [{}])[1].get('opponent', {}).get('name', 'TBD')
                scheduled_at = match.get('scheduled_at')
                if scheduled_at:
                    unix_time = int(time.mktime(time.strptime(scheduled_at, '%Y-%m-%dT%H:%M:%SZ')))
                    event = match.get('tournament', {}).get('name', 'TBD')
                    link = f"https://www.hltv.org/matches/{match.get('id', '')}"
                    matches.append({
                        'team1': team1,
                        'team2': team2,
                        'unix_time': unix_time,
                        'event': event,
                        'link': link
                    })
        else:
            print(f"Fehler bei PandaScore API: {response.status_code}")
    except Exception as e:
        print(f"Fehler beim Abruf: {e}")

    print(f"Gefundene Matches: {len(matches)}")
    return matches


# Alert-Loop (checkt alle 5 Min.)
already_announced = set()

@tasks.loop(minutes=5)
async def send_alerts():
    current_time = time.time()
    matches = get_upcoming_matches()
    for guild_id, teams in TEAMS.items():
        channel_id = CHANNELS.get(guild_id)
        if not channel_id:
            continue
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        for match in matches:
            if any(team.lower() in match['team1'].lower() or team.lower() in match['team2'].lower() for team in teams):
                start_time = match['unix_time']
                time_left = (start_time - current_time) / 60  # Minuten
                match_id = f"{match['team1']} vs {match['team2']}"

                if 4 <= time_left <= 6 and match_id not in already_announced:
                    embed = discord.Embed(
                        title="🎮 Match startet bald!",
                        description=(
                            f"# :{match['team1'].lower()}: {match['team1']}\n"
                            f"# <:VS:1428145739443208305>\n"
                            f"# :{match['team2'].lower()}: {match['team2']}\n\n"
                            f"🎟️ **Event:** {match['event']}\n"
                            f"⏰ **Start:** in ca. {int(time_left)} Minuten"
                        ),
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="🔗 Link", value=match['link'], inline=False)

                    role = discord.utils.get(channel.guild.roles, name="CS-Fans")
                    if role:
                        await channel.send(f"{role.mention}", embed=embed)
                    else:
                        await channel.send(embed=embed)

                    already_announced.add(match_id)
                    print(f"✅ Match-Alert gesendet für {match_id}")


# Commands
@bot.command()
async def subscribe(ctx, *, team):
    guild_id = ctx.guild.id
    if guild_id not in TEAMS:
        TEAMS[guild_id] = []
    matches = get_upcoming_matches()
    valid_team = False
    for match in matches:
        if team.lower() in match['team1'].lower() or team.lower() in match['team2'].lower():
            valid_team = True
            break
    if valid_team or team.lower() in [
            "vitality", "falcons", "navi", "mouz", "spirit", "furia", "g2",
            "aurora", "faze", "liquid", "m80"
    ]:
        if team not in TEAMS[guild_id]:
            TEAMS[guild_id].append(team)
        await ctx.send(f"✅ Team **{team}** hinzugefügt! Der Bot checkt jetzt Matches dafür.")
    else:
        await ctx.send(f"❌ Team '{team}' nicht gefunden. Prüfe die Schreibweise!")

@bot.command()
async def unsubscribe(ctx, *, team):
    guild_id = ctx.guild.id
    if guild_id in TEAMS and team in TEAMS[guild_id]:
        TEAMS[guild_id].remove(team)
        await ctx.send(f"❌ Team **{team}** entfernt.")
    else:
        await ctx.send("⚠️ Team nicht gefunden.")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    CHANNELS[ctx.guild.id] = channel.id
    await ctx.send(f"✅ Channel für Match-Benachrichtigungen gesetzt: {channel.mention}")

@bot.command()
async def settime(ctx, minutes: int):
    global ALERT_TIME
    ALERT_TIME = minutes
    await ctx.send(f"🕒 Vorlaufzeit auf {minutes} Minuten gesetzt.")

@bot.command()
async def debug_matches(ctx):
    matches = get_upcoming_matches()
    await ctx.send(
        f"Gefundene Matches: {len(matches)}\nBeispiel: {matches[0] if matches else 'Keine'}"
    )

@bot.command()
async def testreminder(ctx):
    embed = discord.Embed(
        title="🎮 Test-Reminder",
        description=(
            "# :falcons: Falcons\n"
            "# <:VS:1428145739443208305>\n"
            "# :mouz: MOUZ\n\n"
            "🎟️ **Event:** Test Turnier\n"
            "⏰ **Start:** in ca. 5 Minuten"
        ),
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)
    print("[TEST] Reminder-Test erfolgreich gesendet.")


@bot.event
async def on_ready():
    print(f'✅ Bot läuft als {bot.user}')
    send_alerts.start()


# Starten
bot.run(os.environ['DISCORD_TOKEN'])
