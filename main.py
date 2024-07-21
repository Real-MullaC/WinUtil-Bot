import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiohttp

# Load environment variables from .env file
load_dotenv()

# Load environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))
GITHUB_REPO_OWNER = 'ChrisTitusTech'
GITHUB_REPO_NAME = 'WinUtil'
CONTRIBUTOR_ROLE_ID = int(os.getenv('CONTRIBUTOR_ROLE_ID'))
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID'))
WEB_SERVER_URL = os.getenv('WEB_SERVER_URL')
AUTHORIZATION_URL = 'https://discord.com/oauth2/authorize?client_id=1264587568117448811&response_type=code&redirect_uri=http%3A%2F%2Fbotworks.callums.live%2Fapi%2Foauth2%2Fcallback&scope=identify+connections'

# Initialize bot with all intents enabled
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Event when a user joins the server
@bot.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID:
        return

    print(f"New member joined: {member.name}")

    # Send DM to new member asking them to link their GitHub account
    try:
        await member.send(
            f"Welcome to the server, {member.name}! Please link your GitHub account to get the Contributor role. "
            f"Click this link to authorize: {AUTHORIZATION_URL}"
        )
        print(f"DM sent to {member.name}")
    except discord.Forbidden:
        print(f"Failed to DM {member.name}. They may have DMs disabled.")

async def fetch_github_username(member):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{WEB_SERVER_URL}/api/github/username/{member.id}") as response:
            if response.status == 200:
                data = await response.json()
                return data.get('github_username')
            else:
                print(f"Failed to fetch GitHub username for {member.name}. HTTP Status: {response.status}")
                return None

async def check_github_contributor(github_username):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contributors") as response:
            if response.status == 200:
                contributors = await response.json()
                return any(contributor['login'] == github_username for contributor in contributors)
            else:
                print(f"Failed to check GitHub contributors. HTTP Status: {response.status}")
                return False

async def handle_contributor(member, github_username):
    try:
        await member.send(f"Your Discord username has been updated to {github_username} and you have been given the Contributor role.")
        await member.edit(nick=github_username)
        
        role = discord.utils.get(member.guild.roles, id=CONTRIBUTOR_ROLE_ID)
        if role:
            await member.add_roles(role)
        else:
            print(f"Contributor role with ID {CONTRIBUTOR_ROLE_ID} not found.")
    except discord.Forbidden:
        print(f"Failed to DM {member.name}. They may have DMs disabled.")
    except Exception as e:
        print(f"Failed to handle contributor for {member.name}. Error: {e}")

@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def update_all_users(ctx):
    if ctx.guild.id != GUILD_ID:
        return

    print(f"Updating all users in the server...")
    for member in ctx.guild.members:
        if not member.bot:
            try:
                github_username = await fetch_github_username(member)
                if github_username:
                    is_contributor = await check_github_contributor(github_username)
                    if is_contributor:
                        await handle_contributor(member, github_username)
                    else:
                        await member.send(
                            f"Hi {member.name}, it looks like your GitHub account is not linked as a contributor to the repository. "
                            f"Please check your GitHub account or link it again. Click this link to authorize: {AUTHORIZATION_URL}"
                        )
                else:
                    await member.send(
                        f"Hi {member.name}, we couldn't find your GitHub username. Please link your GitHub account to get the Contributor role. "
                        f"Click this link to authorize: {AUTHORIZATION_URL}"
                    )
            except discord.Forbidden:
                print(f"Failed to DM {member.name}. They may have DMs disabled.")
            except Exception as e:
                print(f"An error occurred with user {member.name}: {e}")

    await ctx.send("All users have been updated.")

# Error handler for the update_all_users command
@update_all_users.error
async def update_all_users_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command.")
    else:
        await ctx.send(f"An error occurred: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)
