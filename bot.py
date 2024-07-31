import discord
import logging
import threading
import base64
import requests
import uuid
import asyncio
from flask import Flask, request, render_template
from discord.ext import commands, tasks
from discord.ui import Select, View
from discord.utils import get
from scheduler import run_alert_scheduler
import config
from commands import (
    handle_setup, handle_authenticate, handle_setadmin, handle_update_moondrills,
    handle_structure, handle_checkgas, handle_structureassets, handle_debug, handle_showadmin, handle_help
)

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

# Initialize the bot with the defined intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Load tokens from file
config.load_tokens()

# Set up logging
logging.basicConfig(level=logging.INFO)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    asyncio.create_task(run_alert_scheduler(bot))

async def is_admin(ctx):
    admin_role = get(ctx.guild.roles, name=config.config.get('admin_role', 'Admin'))
    return admin_role in ctx.author.roles

@bot.command()
async def setadmin(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_setadmin(ctx.message)

@bot.command()
async def showadmin(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_showadmin(ctx.message)

@bot.command()
async def setup(ctx):
    await handle_setup(ctx.message)

@bot.command()
async def addalertchannel(ctx):
    await ctx.send("`!addalertchannel` is not implemented yet.")

@bot.command()
async def selectalertchannel(ctx):
    channels = ctx.guild.text_channels
    options = [discord.SelectOption(label=channel.name, value=str(channel.id)) for channel in channels]

    select = Select(
        placeholder="Choose a channel...",
        options=options,
        custom_id="select_alert_channel"
    )
    view = View()
    view.add_item(select)

    await ctx.send(
        "Select an alert channel:",
        view=view
    )

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.custom_id == "select_alert_channel":
        selected_channel_id = interaction.data['values'][0]
        config.config['alert_channel_id'] = selected_channel_id
        config.save_config()
        await interaction.response.send_message(f"Alert channel set to <#{selected_channel_id}>", ephemeral=True)

@bot.command()
async def gooalert(ctx):
    # Set the alert channel in the configuration
    alert_channel_id = str(ctx.channel.id)
    config.set_config('alert_channel_id', alert_channel_id)
    
    # Notify that the alert channel has been set
    await ctx.send(f"Alert channel set to <#{alert_channel_id}>")

    # Start the background scheduler
    asyncio.create_task(run_alert_scheduler(bot))  # Pass the bot instance

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f"Message received in channel ID: {message.channel.id}")

    if message.content.startswith('!setup'):
        if str(message.channel.id) in config.config.get('admin_channels', []):
            await handle_setup(message)

    elif message.content.startswith('!authenticate'):
        await handle_authenticate(message)

    elif message.content.startswith('!goohelp'):
        await handle_help(message)

    elif message.content.startswith('!setadmin'):
        if await is_admin(message):
            await handle_setadmin(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!updatemoondrills'):
        if await is_admin(message):
            await handle_update_moondrills(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!structure'):
        if await is_admin(message):
            await handle_structure(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!checkgas'):
        if await is_admin(message):
            await handle_checkgas(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!structureassets'):
        if await is_admin(message):
            await handle_structureassets(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!debug'):
        if await is_admin(message):
            await handle_debug(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!showadmin'):
        if await is_admin(message):
            await handle_showadmin(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    # Ensure to process commands
    await bot.process_commands(message)

app = Flask(__name__)

@app.route('/oauth-callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not state or state not in config.states:
        return 'Invalid state parameter.'

    del config.states[state]  # Remove state once used

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': config.config.get('eve_online_callback_url', '')
    }
    auth_str = f"{config.config.get('eve_online_client_id', '')}:{config.config.get('eve_online_secret_key', '')}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth_str}', 
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://login.eveonline.com/v2/oauth/token', data=data, headers=headers)
    response_data = response.json()

    if 'access_token' in response_data:
        config.tokens['access_token'] = response_data['access_token']
        config.tokens['refresh_token'] = response_data.get('refresh_token', config.tokens.get('refresh_token'))
        config.save_tokens()
        return render_template('oauth_callback.html')

    return 'Failed to authenticate.'

def run_flask():
    app.run(host='0.0.0.0', port=5005)

@tasks.loop(minutes=5)
async def refresh_token_task():
    await refresh_token()

async def refresh_token():
    if 'refresh_token' not in config.tokens:
        logging.error('No refresh token found. Cannot refresh access token.')
        return

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': config.tokens['refresh_token'],
        'redirect_uri': config.config.get('eve_online_callback_url', '')
    }
    auth_str = f"{config.config.get('eve_online_client_id', '')}:{config.config.get('eve_online_secret_key', '')}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth_str}', 
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://login.eveonline.com/v2/oauth/token', data=data, headers=headers)
    response_data = response.json()

    if 'access_token' in response_data:
        config.tokens['access_token'] = response_data['access_token']
        config.tokens['refresh_token'] = response_data.get('refresh_token', config.tokens['refresh_token'])  # Update refresh token if available
        config.save_tokens()  # Save tokens to a file
        logging.info('Access token refreshed successfully.')
    else:
        logging.error('Failed to refresh access token.')

if __name__ == "__main__":
    try:
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.start()

        bot.run(config.config.get('discord_bot_token', ''))
    except discord.errors.LoginFailure:
        print("Invalid token. Please check your configuration.")
