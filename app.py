from discord.ext import commands, tasks
from collections import Counter
from dotenv import load_dotenv
import discord
import re
import pathlib
import os
import random
import time
import datetime
import league
import mongo

# Get Discord Key
load_dotenv()
API_KEY_1 = os.getenv("API_KEY_1")

intents = discord.Intents.default()
intents.members = True  # Subscribe to the Members intent
intents.guilds = True  # Subscribe to the Guild intent

# Initilise bot and set activity message
activity = discord.Game(name="$help")
bot = commands.Bot(command_prefix="$", intents=intents,
                   activity=activity, help_command=None)

# On startup


@bot.event
async def on_ready():
    print("Online & Ready!")
    game_check.start()  # Check for new games every 5 mins

# Message on first join


@bot.listen()
async def on_guild_join(guild):
    message = "Thank you for adding Player Tracker to your server!\nTo get started please set a channel I can send messages to.\n \
        ```$channel #bot-commands```"

    for channel in guild.text_channels:  # Get text channels
        if channel.permissions_for(guild.me).send_messages:  # Permission?
            await alert("Hello!", f"{message}", "Green", channel.id)
            mongo.new_server(guild.id, channel.id)
            break

# Check for new games played every 5 mins


@tasks.loop(minutes=5)
async def game_check():
    print(f"{datetime.datetime.now()}: Checking for new games...")

    channels = mongo.get_channels()

    for channel in channels:
        users = mongo.get_users(channel["server_id"])
        for user in users:
            for account in user["accounts"]:
                await latest(user["user_id"], account[0], account[1], account[4], account[3], channel)

    print("Next update in 5 mins")

# Commands

# Command cooldown message


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await alert("Error!", f"This command is on cooldown for {round(error.retry_after, 2)} seconds", "Red", ctx.channel.id)

# Help command


@bot.command(name='help')
@commands.cooldown(rate=1, per=5)
async def get_help(ctx):
    channel = bot.get_channel(ctx.channel.id)

    embed = discord.Embed(
        title=f"Need Help?",
        color=discord.Color.purple())

    embed.add_field(name="**Add an account to a user**",
                    value=f"```$add <@DiscordUsername> <Region> <League Username>```", inline=False)

    embed.add_field(name="**Remove an account from a user**",
                    value=f"```$remove <@DiscordUsername> <Region> <League Username>```", inline=False)

    embed.add_field(name="**View a users accounts**",
                    value=f"```$accounts <@DiscordUsername>```", inline=False)

    embed.add_field(name="**Generate a summary of a user**",
                    value=f"```$summary <@DiscordUsername>```", inline=False)

    embed.add_field(name="**Futher Support**",
                    value=f"Please join my Discord server for further support or to stay updated with Player Tracker or my other projects! https://discord.gg/wXXxJX7vaC", inline=False)

    await channel.send(embed=embed)

# Channel command


@bot.command(name='channel')
@commands.cooldown(rate=1, per=5)
async def new_channel(ctx, channel: discord.TextChannel):
    mongo.new_server(ctx.guild.id, channel.id)
    await alert("Success!", "Messages will now be sent here", "Green", channel.id)

# Add account to player


@bot.command(name='add')
@commands.cooldown(rate=1, per=2)
async def add_account(ctx, user: discord.Member, platform, *args):
    try:
        user_id = user.id
        username = args
        username = ' '.join(username)

        routing = league.get_routing(platform)
        if routing is None:
            await alert(f"Error!", f"Region not found", "Red", ctx.channel.id)

        else:
            # Gets PUUID to add store
            puuid = league.get_puuid(username, routing[0])
            if puuid[0] is True:
                await alert(f"Error!", f"The summoner cannot be found", "Red", ctx.channel.id)
            else:
                puuid = puuid[1]
                mongo.add_user(user_id, puuid, routing, ctx.guild.id)
                await alert(f"Success!", f"{username} has been added to {user.mention}!", "Green", ctx.channel.id)
    except:
        await alert(f"Error!", f"The user cannot be found", "Red", ctx.channel.id)

# Remove account from player


@bot.command(name='remove')
@commands.cooldown(rate=1, per=2)
async def remove_account(ctx, user: discord.Member, platform, *args):
    try:
        routing = league.get_routing(platform)
        if routing is None:
            await alert(f"Error!", f"Region not found", "Red", ctx.channel.id)
        else:
            user_id = user.id
            username = args
            username = ' '.join(username)

            # Gets PUUID to add store
            puuid = league.get_puuid(username, routing[0])
            if puuid[0] is True:
                await alert(f"Error!", f"The summoner cannot be found", "Red", ctx.channel.id)

            else:
                puuid = puuid[1]
                mongo.remove_account(int(user_id), puuid, ctx.guild.id)
                await alert(f"Success!", f"{username} has been removed from {user.mention}!", "Green", ctx.channel.id)
    except:
        await alert(f"Error!", f"The user cannot be found", "Red", ctx.channel.id)

# List all accounts of a user


@bot.command(name='accounts')
@commands.cooldown(rate=1, per=5)
async def get_accounts(ctx, user: discord.Member):
    try:
        accounts = mongo.get_accounts(
            user.id, ctx.guild.id)  # Gets PUUID to add store
        if len(accounts) == 0:
            await alert(f"Error!", f"The user has no accounts", "Red", ctx.channel.id)
        else:
            embed = discord.Embed(
                title=f"{user.name}'s accounts",
                color=discord.Color.green())

            all_accounts = {}
            for account in accounts:
                res = league.get_username(account[0], account[2])
                name = res["name"]
                region = account[4]

                if region in all_accounts:
                    all_accounts[region].append(name)

                else:
                    all_accounts[region] = [name]

            for region in all_accounts.keys():
                usernames = "\n".join(all_accounts[region])
                embed.add_field(
                    name=f"{region.upper()}", value=f"{usernames}", inline=False)

            channel = bot.get_channel(ctx.channel.id)
            await channel.send(embed=embed)

    except:
        await alert(f"Error!", f"The user cannot be found", "Red", ctx.channel.id)

# Get latest match


async def latest(user, puuid, last_match, platform, region, channel):
    server_id = channel["server_id"]
    channel = bot.get_channel(channel['channel'])

    user = await bot.fetch_user(user)

    # Request all matches in past hour
    matches = league.latest_matches(puuid, region, int(time.time() - 3600))

    if matches[0] is True:
        await alert("Error!", f"{matches[1]} {matches[2]}", "Red", channel)

    # If match has been played lately
    if matches[0] is False and len(matches[1]) != 0:
        # Get Match ID
        matches = matches[1]
        match = matches[0].split('_')
        match_id = match[1]

        if match_id != last_match:
            mongo.update_match(user.id, puuid, match_id, server_id)

            # Get data from match
            res = league.latest_match(puuid, region, matches)

            # Set variables from the response
            win = res["win"]
            kda = res["kda"]
            total_cs = res["total_cs"]
            average_cs = res["average_cs"]
            game_lengh = res["game_lengh"]
            champ = res["champ"]
            posistion = res["posistion"]

            # Embed colour if win or not
            if win is True:
                embed_color = discord.Color.green()
                victory = "Victory"
                win = "won"
            else:
                embed_color = discord.Color.red()
                victory = "Defeat"
                win = "lost"

            # Get champion icon for embed
            path_to_file = pathlib.Path(__file__).parent.resolve()
            champ_icons = os.listdir(
                f"{path_to_file}/images")  # Path to images
            icon_id = []
            for icon in champ_icons:
                icon = re.split('[_.]', icon)
                if icon[0] == champ:
                    icon_id.append(icon[1])

            icon_id = random.choice(icon_id)  # Pick random icon

            # Embed message
            embed = discord.Embed(
                title=f"{user.name} just {win} a game!",
                description=f"[Click here view the match.](https://www.leagueofgraphs.com/match/{platform}/{match_id})",
                color=embed_color)

            embed.set_author(name=f"{victory}!")

            file = discord.File(
                f"{path_to_file}/images/{champ}_{icon_id}.jpg", filename="image.png")
            embed.set_thumbnail(url="attachment://image.png")

            embed.add_field(name="**Champion**",
                            value=f"{champ}", inline=True)

            embed.add_field(name="**Role**",
                            value=f"{posistion}", inline=True)

            embed.add_field(name="\u200b", value="\u200b", inline=True)

            embed.add_field(name="**KDA**",
                            value=f"{kda[0]}/{kda[1]}/{kda[2]}", inline=True)

            embed.add_field(name="**CS**",
                            value=f"{total_cs} Total CS\n{average_cs} CS/MIN", inline=True)

            embed.add_field(name="\u200b", value="\u200b", inline=True)

            embed.set_footer(
                text=f"Match length: {game_lengh[0]}:{game_lengh[1]:02}")

            # Return the embed
            await channel.send(file=file, embed=embed)

# Get a summary over multiple games


@commands.cooldown(rate=1, per=30)
@bot.command(name='summary')
async def summary(ctx, user: discord.Member):
    accounts = mongo.get_accounts(user.id, ctx.guild.id)
    start_time = int(time.time() - 604800)
    res = league.accounts_summary(accounts, start_time)

    total_matches = res["total_matches"]
    winrate = res["winrate"]
    kda = res["average_kda"]
    average_cs = res["average_cs"]
    average_csm = res["average_csm"]
    avg_cs_at_10 = res["10min_cs"]

    # Embed colour if WE greater than 50
    if winrate >= 50:
        embed_color = discord.Color.green()
    else:
        embed_color = discord.Color.red()

    counted = Counter(res["champs"])
    counted = counted.most_common(3)
    top_champ = counted[0][0]
    champ_list = top_champ
    path_to_file = pathlib.Path(__file__).parent.resolve()

    for champ in counted[1:]:
        champ_list = champ_list + ", " + champ[0]

    champ_icons = os.listdir(f"{path_to_file}/images")

    icon_id = []
    for icon in champ_icons:
        icon = re.split('[_.]', icon)
        if icon[0] == top_champ:
            icon_id.append(icon[1])

    icon_id = random.choice(icon_id)

    counted = Counter(res["posistions"])
    counted = counted.most_common(2)
    top_role = counted[0][0]
    roles = top_role

    for role in counted[1:]:
        roles = roles + ", " + role[0]

    embed = discord.Embed(
        title=f"{user.name}'s 7 Day Summary",
        color=embed_color)

    file = discord.File(
        f"{path_to_file}/images/{top_champ}_{icon_id}.jpg", filename="image.png")
    embed.set_thumbnail(url="attachment://image.png")

    embed.add_field(name="**Total Matches**",
                    value=f"{total_matches}", inline=False)

    embed.add_field(name="**Winrate**", value=f"{winrate}%", inline=False)

    embed.add_field(name="**Top Champs**", value=f"{champ_list}", inline=False)

    embed.add_field(name="**Roles**", value=f"{roles}", inline=False)

    embed.add_field(name="**Average KDA**",
                    value=f"{kda[0]}/{kda[1]}/{kda[2]}", inline=False)

    embed.add_field(name="**Average CS**",
                    value=f"{average_cs} Total CS\n{average_csm} CS/MIN\n{avg_cs_at_10} CS @ 10m", inline=False)

    await ctx.send(file=file, embed=embed)

# Alert message to send errors/success messages etc


async def alert(title, message, color, channel):
    channel = bot.get_channel(channel)
    # Set color for embed
    if color == 'Green':
        color = discord.Color.green()
    elif color == 'Red':
        color = discord.Color.red()

    # Create embed
    embed = discord.Embed(
        title=f"{title}",
        description=f"{message}",
        color=color)

    # Return the embed
    await channel.send(embed=embed)

if __name__ == '__main__':
    bot.run(API_KEY_1)
