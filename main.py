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

TEMP_VOICE_CATEGORY_ID = int(os.getenv('TEMP_VOICE_CATEGORY_ID'))
TEMP_VOICE_CHANNEL_ID = int(os.getenv('TEMP_VOICE_CHANNEL_ID'))
TEMP_VOICE_DEST_CATEGORY_ID = int(os.getenv('TEMP_VOICE_DEST_CATEGORY_ID'))
created_voice_channels = []


# Initialize bot with all intents enabled
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)
guild = None

async def update_server_guild():
    global guild
    guild = bot.get_guild(GUILD_ID)

# Command to manually update guild
@bot.command(name='update_guild')
@commands.has_role(ADMIN_ROLE_ID)  # Ensure only users with the admin role can run this command
async def update_guild(ctx):
    await ctx.send("Starting the guild update process...")
    try:
        await update_server_guild()
        await ctx.send("Guild update process completed.")
    except Exception as e:
        await ctx.send(f"An error occurred while updating guild: {e}")

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
    if not CONTRIBUTOR_ROLE_ID:
        print(f"The Contributor Role ID (CONTRIBUTOR_ROLE_ID) is not set in .env file, please set it up correctly if you wish to use this bot feature")
        return

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
                print(f"Did not find role with id {CONTRIBUTOR_ROLE_ID}, please double check your .env file")
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
        await ctx.send(f"An error occurred while updating roles: {e}")

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

#Handle TempVoice Logic whenever a member joins or leaves a voice channel
@bot.event
async def on_voice_state_update(member, before, after):
    if not is_temp_voice_configured():
        return

    # Make sure this feature only works on WinUtil Server, and only at specific channel & category
    if member.guild.id != GUILD_ID:
        return

    if  before == after:
        return

    if not before.channel == None:
        if before.channel.id in created_voice_channels:
            print(f"Found member {member.name} (member.nick) has left a Voice Channel (channel name: {before.channel.name}, channel ID: {before.channel.id}) that was created by this bot")
            # If the voice channel is empty
            if before.channel.members == []:
                try:
                    msg = f"Deleting Voice channel {before.channel.name}, because it was created by {bot.user.name}, and the voice channel is empty."
                    print(msg)
                    await before.channel.delete(reason=msg)
                    # Only remove Voice Channel upon successful deletion of Voice Channel
                    vc_index = created_voice_channels.index(before.channel.id)
                    created_voice_channels.pop(vc_index)
                except discord.Forbidden:
                    print(f"{bot.user.name} could not delete voice channel (channel name: {before.channel.name}, channel ID: {before.channel.id}), discord.Forbidden exception was thrown.")
                except discord.NotFound:
                    print(f"{bot.user.name} could not find voice channel (channel name: {before.channel.name}, channel ID: {before.channel.id}) when trying to delete it, discord.NotFound exception was thrown.")
                except discord.HTTPException:
                    print(f"{bot.user.name} could not delete voice channel (channel name: {before.channel.name}, channel ID: {before.channel.id}), failed to do so, discord.HTTPException exception was thrown.")
                except Exception as e:
                    print(f"{bot.user.name} could not delete voice channel (channel name: {before.channel.name}, channel ID: {before.channel.id}), for any reason: {e}")

                # Print the list for debug info
                print(f"Current List of Voice Channel(s): {created_voice_channels})")

    # after.channel being a None value is when a User leaves a Voice Channel
    if after.channel == None:
        return # Do an Early Return, as the next steps require after.channel to be not a None Value

    if not (after.channel.id == TEMP_VOICE_CHANNEL_ID and after.channel.category.id == TEMP_VOICE_CATEGORY_ID):
        return

    try:
        category = discord.utils.get(member.guild.categories, id=TEMP_VOICE_DEST_CATEGORY_ID)
        created_vc = await category.create_voice_channel(f"{member.nick}'s VC")
        # Only print info & add new voice channel to list if the voice channel was created successfully
        created_voice_channels.append(created_vc.id)
        print(f"Created Voice Channel, name: {created_vc.name}")
        await member.move_to(created_vc)
        print(f"Moved member {member.name} to Voice Channel {created_vc.name}")
    except Exception as e:
        print(f"An unexpected error occurred while handling VoiceTemp logic to {member.name}: {e}")

# Check for Environment Variables on Temp Voice, returns True if it's configured, else False
def is_temp_voice_configured():
    if (TEMP_VOICE_DEST_CATEGORY_ID == None or TEMP_VOICE_DEST_CATEGORY_ID) == 0 and (TEMP_VOICE_CATEGORY_ID == None or TEMP_VOICE_CATEGORY_ID == 0) and (TEMP_VOICE_CHANNEL_ID == None or TEMP_VOICE_CHANNEL_ID == 0):
        print(f"TempVoice Feature is not configured, therefore it won't work in this bot")
        return False
    return True

# A function that updates the state of Voice Channels created by this bot, while it's currently running.. and before it ran.
async def update_server_temp_voice_state():
    if not is_temp_voice_configured():
        return

    if guild == None:
        print(f"Guild is None")
        return

    if guild.id != GUILD_ID:
        return

    try:
        category = discord.utils.get(guild.categories, id=TEMP_VOICE_DEST_CATEGORY_ID)
    except Exception as e:
        print(f"An unexpected error occurred while updating VoiceTemp State: {e}")
        return

    for voice_channel in category.voice_channels:
        if voice_channel.members == []:
            try:
                msg = f"Deleting Voice channel {voice_channel.name}, because it was created by {bot.user.name}, and the voice channel is empty."
                print(msg)
                await voice_channel.delete(reason=msg)
                # This's just to make sure that the state is up-to-date
                if voice_channel.id in created_voice_channels:
                    index = created_voice_channels.index(voice_channel.id)
                    created_voice_channels.pop(index)
            except discord.Forbidden:
                print(f"{bot.user.name} could not delete voice channel (channel name: {voice_channel.name}, channel ID: {voice_channel.id}), discord.Forbidden exception was thrown.")
            except discord.NotFound:
                print(f"{bot.user.name} could not find voice channel (channel name: {voice_channel.name}, channel ID: {voice_channel.id}) when trying to delete it, discord.NotFound exception was thrown.")
            except discord.HTTPException:
                print(f"{bot.user.name} could not delete voice channel (channel name: {voice_channel.name}, channel ID: {voice_channel.id}), failed to do so, discord.HTTPException exception was thrown.")
            except Exception as e:
                print(f"{bot.user.name} could not delete voice channel (channel name: {voice_channel.name}, channel ID: {voice_channel.id}), for any reason: {e}")
        else:
            created_voice_channels.append(voice_channel.id)

# Command to manually update guild
@bot.command(name='update_temp_voice_state')
@commands.has_role(ADMIN_ROLE_ID)  # Ensure only users with the admin role can run this command
async def update_temp_voice_state(ctx):
    await ctx.send("Starting the TempVoice State update process...")
    try:
        await update_server_temp_voice_state()
        await ctx.send("TempVoice State update process completed.")
    except Exception as e:
        await ctx.send(f"An error occurred while updating TempVoice State: {e}")

# Start the periodic check on bot startup
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

    print("Updating Guild")
    await update_server_guild()

    print("Updating TempVoice State")
    await update_server_temp_voice_state()

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
