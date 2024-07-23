import discord
from discord.ext import commands, tasks
import os
import aiohttp
import json
import Functions.Discord.embed as EmbedBuilder
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file
load_dotenv()

# Load environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))

CONTRIBUTOR_ROLE_ID = int(os.getenv('CONTRIBUTOR_ROLE_ID'))
WEB_SERVER_URL = os.getenv('WEB_SERVER_URL')
CHECK_INTERVAL = 10  # Time in seconds to wait between checks
ADMIN_ROLE_ID = os.getenv('ADMIN_ROLE_ID')
AUTHORIZATION_URL = "https://discord.com/oauth2/authorize?client_id=1264587568117448811&response_type=code&redirect_uri=http%3A%2F%2Fbotworks.callums.live%2Fapi%2Foauth2%2Fcallback&scope=identify+connections"

# Initialize bot with all intents enabled
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Function to fetch user records from the web server
async def fetch_user_records():
    url = f"{WEB_SERVER_URL}/api/user_records"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"Failed to fetch user records. HTTP Status: {response.status}")
                    return {}
        except Exception as e:
            print(f"An error occurred while fetching user records: {e}")
            return {}

# Function to update user roles based on records
async def update_user_roles():
    user_records = await fetch_user_records()  # Fetch user records from the web server
    required_guild = 0
    for guild in bot.guilds:
        if guild.id == GUILD_ID:
            required_guild = guild
            break

    for member in required_guild.members:
        await asyncio.sleep(delay=2)
        if member.bot:
            continue

        user_record = user_records.get(str(member.id))
        if not user_record:
            continue

        new_nickname = user_record.get('github_username')
        try:
            await member.edit(nick=new_nickname)
            print(f"Updated nickname of {member.name} to {new_nickname} [TEMPORARY]")
        except Exception as e:
            print(f"An unexpected error occurred while updating {member.name}: {e}")

        if not (user_record.get('contributor') and user_record.get('contributor') == True):
            continue
        try:
            role = discord.utils.get(guild.roles, id=CONTRIBUTOR_ROLE_ID)
            if not role:
                continue
            if role not in member.roles:
                await member.add_roles(role)
                # Only print message if the role was added
                print(f"Added 'Contributor' role to {member.name}")
        except discord.Forbidden:
            print(f"Permission error while updating {member.name}.")
        except discord.HTTPException as e:
            print(f"HTTP error occurred while updating {member.name}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while updating {member.name}: {e}")

# Command to manually update roles
@bot.command(name='update_roles')
@commands.has_role(ADMIN_ROLE_ID)  # Ensure only users with the admin role can run this command
async def update_roles(ctx):
    await ctx.send("Starting the role update process...")
    try:
        await update_user_roles()
        await ctx.send("Role update process completed.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Periodically check for updates
@tasks.loop(seconds=CHECK_INTERVAL)
async def periodic_check():
    await update_user_roles()

# Event when a user joins the server
@bot.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID:
        return

    print(f"New member joined: {member.name}")


    embed = EmbedBuilder.DefaultEmbed(title="Github Linking", description="Are you a contributor? Link your github account to get your role! ")
    view = discord.ui.View()
    button = discord.ui.Button(label="Link", style=discord.ButtonStyle.link, url=AUTHORIZATION_URL)
    view.add_item(button)

    # Send DM to new member asking them to link their GitHub account
    try:
        
        await member.send(embed = embed, view = view)
        print(f"DM sent to {member.name}")
    except discord.Forbidden:
        print(f"Failed to DM {member.name}. They may have DMs disabled.")
    except Exception as e:
        print(f"An unexpected error occurred while sending DM to {member.name}: {e}")

# Start the periodic check on bot startup
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    periodic_check.start()

@bot.command(name="link")
async def link(ctx: commands.Context):
    embed = EmbedBuilder.DefaultEmbed(title="Github Linking", description="Are you a contributor? Link your github account to get your role! ")
    view = discord.ui.View()
    button = discord.ui.Button(label="Link", style=discord.ButtonStyle.link, url=AUTHORIZATION_URL)
    view.add_item(button)

    # Send DM to new member asking them to link their GitHub account
    user = ctx.author
    try:
        await user.send(embed = embed, view = view)
        await ctx.send("Please check your dms.")
    except discord.Forbidden:
        print(f"{ctx.author.name}´s DMs are most likely closed!")

if __name__ == "__main__":
    bot.run(TOKEN)