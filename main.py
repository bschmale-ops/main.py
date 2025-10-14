import os
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import datetime
import json
import re

print("🚀 Starting Discord CS2 Bot...")

# =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

TEAMS = {}
CHANNELS = {}
ALERT_TIME = 5
DATA_FILE = "bot_data.json"


def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 5}
    except:
        return {"TEAMS": {}, "CHANNELS": {}, "ALERT_TIME": 5}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# Daten laden
data = load_data()
TEAMS = {}
CHANNELS = {}
ALERT_TIME = data.get("ALERT_TIME", 5)

for guild_id_str, teams in data.get("TEAMS", {}).items():
    TEAMS[int(guild_id_str)] = teams

for guild_id_str, channel_id in data.get("CHANNELS", {}).items():
    CHANNELS[int(guild_id_str)] = channel_id

print(f"📊 Loaded: {len(TEAMS)} teams, {len(CHANNELS)} channels")


# =========================
# MATCH FUNCTIONS
# =========================
async def get_upcoming_matches():
    """Holt CS2 Matches"""
    matches = []

    # Erstelle Demo-Matches für Test
    demo_teams = [('Natus Vincere', 'FaZe Clan'), ('Vitality', 'G2 Esports'),
                  ('MOUZ', 'Spirit'), ('FURIA', 'Falcons')]

    for i, (team1, team2) in enumerate(demo_teams):
        match_time = datetime.datetime.utcnow() + datetime.timedelta(hours=i +
                                                                     1)
        matches.append({
            'team1': team1,
            'team2': team2,
            'unix_time': int(match_time.timestamp()),
            'event': 'CS2 Tournament',
            'link': 'https://www.hltv.org/matches'
        })

    return matches


# =========================
# ALERT SYSTEM
# =========================
@tasks.loop(minutes=5)
async def send_alerts():
    try:
        now = int(datetime.datetime.utcnow().timestamp())
        matches = await get_upcoming_matches()

        for guild_id, teams in TEAMS.items():
            channel_id = CHANNELS.get(guild_id)
            if not channel_id:
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            for match in matches:
                if any(team.lower() in (match['team1'] +
                                        match['team2']).lower()
                       for team in teams):
                    time_left = (match['unix_time'] - now) / 60
                    if ALERT_TIME - 1 <= time_left <= ALERT_TIME + 1:
                        embed = discord.Embed(
                            title="⚔️ Match Alert",
                            description=
                            f"{match['team1']} vs {match['team2']} startet bald!",
                            color=0x00ff00)
                        embed.add_field(name="Event",
                                        value=match['event'],
                                        inline=True)
                        embed.add_field(name="Start in",
                                        value=f"{int(time_left)} Minuten",
                                        inline=True)
                        embed.add_field(name="Link",
                                        value=match['link'],
                                        inline=False)
                        await channel.send(embed=embed)

                        # Rolle pingen
                        role = discord.utils.get(channel.guild.roles,
                                                 name="CS2")
                        if role:
                            await channel.send(f"📢 {role.mention}")

        print(f"✅ Checked {len(matches)} matches")
    except Exception as e:
        print(f"❌ Alert error: {e}")


# =========================
# COMMANDS
# =========================
@bot.command()
async def subscribe(ctx, *, team):
    guild_id = ctx.guild.id
    TEAMS.setdefault(guild_id, [])
    if team not in TEAMS[guild_id]:
        TEAMS[guild_id].append(team)
        save_data({
            "TEAMS": TEAMS,
            "CHANNELS": CHANNELS,
            "ALERT_TIME": ALERT_TIME
        })
        await ctx.send(f"✅ Team '{team}' hinzugefügt!")
    else:
        await ctx.send(f"⚠️ '{team}' ist bereits abonniert.")


@bot.command()
async def unsubscribe(ctx, *, team):
    guild_id = ctx.guild.id
    if team in TEAMS.get(guild_id, []):
        TEAMS[guild_id].remove(team)
        save_data({
            "TEAMS": TEAMS,
            "CHANNELS": CHANNELS,
            "ALERT_TIME": ALERT_TIME
        })
        await ctx.send(f"❌ Team '{team}' entfernt!")
    else:
        await ctx.send("Team nicht gefunden.")


@bot.command()
async def list_teams(ctx):
    guild_id = ctx.guild.id
    teams = TEAMS.get(guild_id, [])
    if teams:
        team_list = "\n".join([f"✅ {team}" for team in teams])
        await ctx.send(f"**Abonnierte Teams:**\n{team_list}")
    else:
        await ctx.send("❌ Noch keine Teams abonniert.")


@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    CHANNELS[ctx.guild.id] = channel.id
    save_data({"TEAMS": TEAMS, "CHANNELS": CHANNELS, "ALERT_TIME": ALERT_TIME})
    await ctx.send(f"📡 Channel auf {channel.mention} gesetzt!")


@bot.command()
async def ping(ctx):
    await ctx.send('pong 🏓')


@bot.command()
async def status(ctx):
    await ctx.send(f'🤖 Bot läuft! {len(TEAMS)} Teams überwacht.')


# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    print(f'✅ {bot.user} ist online!')
    if not send_alerts.is_running():
        send_alerts.start()
        print("🔄 Alert system started")


# =========================
# START BOT
# =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN nicht gefunden!")
