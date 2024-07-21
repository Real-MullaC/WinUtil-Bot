import discord
from discord.ext import commands
from discord.ui import Button, View
import requests
import time
from threading import Thread
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the token from environment variables
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if DISCORD_BOT_TOKEN is None:
    raise ValueError("No token found in environment variables. Please set DISCORD_BOT_TOKEN.")

REPO_OWNER = 'ChrisTitusTech'
REPO_NAME = 'WinUtil'
CONTRIBUTOR_ROLE_NAME = 'Contributor'
CONTRIBUTOR_ROLE_ID = 1258696483189030973
GITHUB_API_URL = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contributors'

# Caching contributors list and rate limit status
contributors_cache = []
rate_limit_reset_time = 0
CHECK_INTERVAL = 3600  # Check every hour

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to update contributors cache
def update_contributors():
    global contributors_cache, rate_limit_reset_time

    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        contributors_cache = response.json()
        rate_limit_reset_time = time.time() + 3600
        print("Contributors list updated.")
    else:
        print(f"Failed to fetch contributors: {response.status_code}")
        if 'X-RateLimit-Reset' in response.headers:
            rate_limit_reset_time = int(response.headers['X-RateLimit-Reset'])
        print(f"Rate limit reset time: {rate_limit_reset_time}")

# Function to check if a user is a contributor
def is_contributor(github_username):
    for contributor in contributors_cache:
        if contributor['login'].lower() == github_username.lower():
            return True
    return False

# Function to get GitHub username from connected accounts
async def get_github_username(member):
    try:
        user = await bot.fetch_user(member.id)
        connections = await user.fetch_connections()
        for connection in connections:
            if connection.type == 'github':
                return connection.name
    except Exception as e:
        print(f"Failed to fetch GitHub username for {member}: {e}")
    return None

# View for the button
class ResetButtonView(View):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    @discord.ui.button(label="Reset Username", style=discord.ButtonStyle.primary)
    async def reset_username(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.user.id)
        if member:
            original_nickname = member.display_name.split(" ")[0]
            await member.edit(nick=original_nickname)
            await interaction.response.send_message(f"Your username has been reset to {original_nickname}.", ephemeral=True)
        else:
            await interaction.response.send_message("Unable to find your member data.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    update_contributors()
    # Start the polling thread
    polling_thread = Thread(target=poll_github)
    polling_thread.start()

@bot.event
async def on_member_join(member):
    if member.bot:
        return

    current_time = time.time()
    if current_time > rate_limit_reset_time:
        update_contributors()
    
    github_username = await get_github_username(member)
    if github_username:
        print(f"GitHub username for {member} is {github_username}.")
        if is_contributor(github_username):
            contributor_role = discord.utils.get(member.guild.roles, name=CONTRIBUTOR_ROLE_NAME)
            if contributor_role:
                await member.add_roles(contributor_role)
            await member.edit(nick=github_username)
            await member.send(
                f"Welcome, {github_username}! Your nickname has been changed to your GitHub username and you have been given the Contributor role. If you want to reset your username, click the button below.",
                view=ResetButtonView(member)
            )
        else:
            print(f"{github_username} is not a contributor.")
    else:
        print(f"No GitHub username found for {member}.")

@bot.command(name='update_all_users')
@commands.has_role(CONTRIBUTOR_ROLE_ID)
async def update_all_users(ctx):
    """Command to manually update all users in the server."""
    await ctx.send("Updating all users...")  # Add a confirmation message
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the required role to use this command.")
        return

    # Get the contributor role object
    contributor_role = discord.utils.get(ctx.guild.roles, name=CONTRIBUTOR_ROLE_NAME)
    if contributor_role is None:
        await ctx.send(f"Role '{CONTRIBUTOR_ROLE_NAME}' not found.")
        return

    # Iterate over all members in the server
    updated_users = 0
    for member in ctx.guild.members:
        if member.bot:
            continue

        github_username = await get_github_username(member)
        if github_username:
            print(f"Processing {member}. GitHub username: {github_username}")
            if is_contributor(github_username):
                try:
                    if contributor_role:
                        await member.add_roles(contributor_role)
                    await member.edit(nick=github_username)
                    await member.send(
                        f"Your nickname has been changed to your GitHub username and you have been given the Contributor role. If you want to reset your username, click the button below.",
                        view=ResetButtonView(member)
                    )
                    updated_users += 1
                except discord.Forbidden:
                    print(f"Insufficient permissions to update {member}.")
                except Exception as e:
                    print(f"Failed to update {member}: {e}")
            else:
                print(f"{github_username} is not a contributor.")
        else:
            print(f"No GitHub username found for {member}.")

    await ctx.send(f"Update complete. {updated_users} users were updated.")

def poll_github():
    while True:
        current_time = time.time()
        if current_time > rate_limit_reset_time:
            update_contributors()
        time.sleep(CHECK_INTERVAL)

bot.run(DISCORD_BOT_TOKEN)
