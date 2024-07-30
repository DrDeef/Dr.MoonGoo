import discord
import logging
import threading
from flask import Flask, request, render_template
from discord.ext import commands, tasks
import base64
import requests
from config import (
    DISCORD_BOT_TOKEN, ADMIN_CHANNELS, CALLBACK_URL, CLIENT_ID, CLIENT_SECRET,
    states, tokens, save_tokens, load_tokens
)
from commands import (
    handle_setup, handle_authenticate, handle_setadmin, handle_update_moondrills,
    handle_structure, handle_checkgas, handle_structureassets, handle_debug
)

# Load tokens from file
load_tokens()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    refresh_token_task.start()  # Start the token refresh task

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!setup'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_setup(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!authenticate'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_authenticate(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!setadmin'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_setadmin(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!updatemoondrills'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_update_moondrills(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!structure'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_structure(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!checkgas'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_checkgas(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!structureassets'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_structureassets(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

    elif message.content.startswith('!debug'):
        if str(message.channel.id) in ADMIN_CHANNELS:
            await handle_debug(message)
        else:
            await message.channel.send("You are not authorized to use this command.")

app = Flask(__name__)

@app.route('/oauth-callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not state or state not in states:
        return 'Invalid state parameter.'

    del states[state]  # Remove state once used

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CALLBACK_URL
    }
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth_str}', 
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://login.eveonline.com/v2/oauth/token', data=data, headers=headers)
    response_data = response.json()

    if 'access_token' in response_data:
        tokens['access_token'] = response_data['access_token']
        tokens['refresh_token'] = response_data.get('refresh_token', tokens.get('refresh_token'))
        save_tokens()
        return render_template('oauth_callback.html')

    return 'Failed to authenticate.'

def run_flask():
    app.run(host='0.0.0.0', port=5005)

@tasks.loop(minutes=5)
async def refresh_token_task():
    await refresh_token()

async def refresh_token():
    if 'refresh_token' not in tokens:
        logging.error('No refresh token found. Cannot refresh access token.')
        return

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token'],
        'redirect_uri': CALLBACK_URL
    }
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth_str}', 
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://login.eveonline.com/v2/oauth/token', data=data, headers=headers)
    response_data = response.json()

    if 'access_token' in response_data:
        tokens['access_token'] = response_data['access_token']
        tokens['refresh_token'] = response_data.get('refresh_token', tokens['refresh_token'])  # Update refresh token if available
        save_tokens()  # Save tokens to a file
        logging.info('Access token refreshed successfully.')
    else:
        logging.error('Failed to refresh access token.')

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

client.run(DISCORD_BOT_TOKEN)
