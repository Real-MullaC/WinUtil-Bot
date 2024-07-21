import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the Discord bot token from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Set up bot with appropriate intents
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name='get_github')
async def get_github(ctx, member: discord.Member = None):
    """Command to check if a user has a GitHub account linked and fetch the username."""
    if member is None:
        member = ctx.author  # Default to the command author if no member is specified
    
    try:
        # Fetch user connections
        connections = await member.fetch_connections()
        
        github_username = None
        for connection in connections:
            if connection['type'] == 'github':
                github_username = connection['name']
                break
        
        if github_username:
            await ctx.send(f"{member.display_name} has a GitHub account linked: `{github_username}`")
        else:
            await ctx.send(f"{member.display_name} does not have a GitHub account linked.")
    
    except discord.HTTPException as e:
        await ctx.send(f"Failed to fetch connections for {member.display_name}. Error: {e}")

bot.run(DISCORD_TOKEN)
