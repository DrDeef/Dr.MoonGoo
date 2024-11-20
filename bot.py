import discord
import logging
import threading
import requests
import asyncio
import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from discord.ext import commands
from discord.ui import Select, View
from discord.utils import get
from scheduler import run_alert_scheduler
import config
import tasks
from moongoo_commands import load_moon_goo_from_json
from datetime import datetime
from administration import get_character_info, get_corporation_id
from commands import (
    handle_mongo_pricing, handle_setup, handle_authenticate, handle_update_moondrills, handle_checkgas, handle_spacegoblin, handle_showadmin, handle_help, handle_fetch_moon_goo_assets, handle_structure_pricing
)

# FastAPI setup
app = FastAPI()

# Serve static files (e.g., images)
app.mount("/images", StaticFiles(directory="images"), name="images")

# Fetch the configuration values
CALLBACK_URL = config.get_config('eve_online_callback_url')
CLIENT_ID = config.get_config('eve_online_client_id')
CLIENT_SECRET = config.get_config('eve_online_secret_key')

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

# Initialize the bot with the defined intents
bot = commands.Bot(command_prefix='!', intents=intents)

bot_start_time = datetime.utcnow()

# Load tokens and server IDs from file
tokens = config.load_all_tokens()
server_ids = config.get_all_server_ids()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    tasks.start_tasks(bot)

@bot.event
async def on_guild_join(guild):
    server_id = str(guild.id)
    config.add_server_id(server_id)
    print(f'Joined new server: {guild.name} ({server_id})')

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id', '')
        if custom_id == 'select_alert_channel':
            selected_channel_id = interaction.data.get("values", [])[0]
            server_id = str(interaction.guild.id)

            alert_channels = config.load_alert_channels()
            alert_channels[server_id] = selected_channel_id
            config.save_alert_channels(alert_channels)

            await interaction.response.send_message(f"Alert channel set to <#{selected_channel_id}>")

            # Start alert scheduler if not already running
            if not any(task.get_name() == f"alert_scheduler_{server_id}" for task in asyncio.all_tasks()):
                asyncio.create_task(run_alert_scheduler(bot, server_id), name=f"alert_scheduler_{server_id}")

        elif custom_id == 'select_structure':
            selected_structure_name = interaction.data['values'][0]
            moon_goo_data = await load_moon_goo_from_json(str(interaction.guild.id))

            if selected_structure_name in moon_goo_data:
                await handle_structure_pricing(interaction, selected_structure_name)
            else:
                await interaction.response.send_message("Selected structure not found in the moon goo data.")

# FastAPI route handlers
@app.get('/oauth-callback')
async def oauth_callback(code: str = None, state: str = None):
    if not code or not state:
        return "Missing code or state parameter", 400

    server_id = config.states.pop(state, None)
    if not server_id:
        return "Invalid or expired state", 400

    token_url = 'https://login.eveonline.com/v2/oauth/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CALLBACK_URL,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Request error: {e}", 500

    if 'access_token' not in response_data:
        return f"Error obtaining tokens: {response_data.get('error_description', 'Unknown error')}", 500

    access_token = response_data['access_token']
    refresh_token = response_data.get('refresh_token', None)
    expires_in = response_data.get('expires_in', None)

    character_info = get_character_info(access_token)
    if not character_info:
        return "Failed to retrieve character info", 500

    character_id = character_info.get('CharacterID')
    if not character_id:
        return "Character ID not found in the character info", 500

    corporation_id = get_corporation_id(character_id, access_token)
    if corporation_id is None:
        return "Failed to retrieve corporation ID", 500

    created_at = datetime.utcnow().isoformat() + "Z"

    config.save_token(server_id, corporation_id, access_token, refresh_token, expires_in, created_at, character_id)

    return HTMLResponse(content="<h1>OAuth Callback Successful!</h1>")

@app.get('/terms-of-service')
async def tos():
    return HTMLResponse(content="<h1>Terms of Service</h1>")

@app.get('/about')
async def about():
    return HTMLResponse(content="<h1>About Us</h1>")

@app.get('/privacy-policy')
async def privacy():
    return HTMLResponse(content="<h1>Privacy Policy</h1>")

# Run FastAPI with Uvicorn
if __name__ == "__main__":
    try:
        config.load_config()
        tokens = config.load_all_tokens()
        server_ids = config.get_all_server_ids()
        print("Server IDs:", server_ids)

        # Start the FastAPI app using Uvicorn
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=5005)

        bot.run(config.get_config('discord_bot_token', ''))
    except discord.errors.LoginFailure:
        print("Invalid Discord - Bot token. Please check your configuration.")