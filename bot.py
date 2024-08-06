import discord
import logging
import threading
import base64
import requests
import uuid
import asyncio
import datetime
from flask import Flask, request, render_template
from discord.ext import commands, tasks
from discord.ui import Select, View
from discord.utils import get
from scheduler import run_alert_scheduler
import config
from urllib.parse import quote
from config import get_config
from tasks import refresh_token, refresh_token_task
from commands import (
    handle_setup, handle_authenticate, handle_setadmin, handle_update_moondrills,
    handle_structure, handle_checkgas, handle_debug, handle_showadmin, handle_help, handle_add_alert_channel, handle_fetch_moon_goo_assets
)

# Fetch the configuration values
CALLBACK_URL = get_config('eve_online_callback_url')
CLIENT_ID = get_config('eve_online_client_id')
CLIENT_SECRET = get_config('eve_online_secret_key')

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

# Initialize the bot with the defined intents
bot = commands.Bot(command_prefix='!', intents=intents)

app = Flask(__name__)

def run_flask():
    app.run(host='127.0.0.1', port=5005, ssl_context=None)

# Load tokens from file
config.load_tokens()

# Set up logging
logging.basicConfig(level=logging.INFO)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    refresh_token_task.start()  # Start the refresh token task
    asyncio.create_task(run_alert_scheduler(bot))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.custom_id == "select_alert_channel":
        selected_channel_id = interaction.data['values'][0]
        config.config['alert_channel_id'] = selected_channel_id
        config.save_config()
        await interaction.response.send_message(f"Alert channel set to <#{selected_channel_id}>", ephemeral=True)


async def is_admin(ctx):
    admin_role = get(ctx.guild.roles, name=config.config.get('admin_role', 'Admin'))
    return admin_role in ctx.author.roles

@bot.command()
async def setadminchannel(ctx):
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
    await handle_add_alert_channel(ctx)  # Call the handler function

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

@bot.command()
async def refreshToken(ctx):
    # Notify the user that the refresh process is starting
    await ctx.send("Attempting to refresh access token...")
    
    # Call the refresh_token function
    await refresh_token()
    
    # Notify the user that the refresh process has been attempted
    await ctx.send("Token refresh attempted. Check logs for details.")



@bot.command()
async def gooalert(ctx):
    # Set the alert channel in the configuration
    alert_channel_id = str(ctx.channel.id)
    config.set_config('alert_channel_id', alert_channel_id)
    
    # Notify that the alert channel has been set
    await ctx.send(f"Alert channel set to <#{alert_channel_id}>")

    # Start the background scheduler
    asyncio.create_task(run_alert_scheduler(bot))  # Pass the bot instance

@bot.command()
async def debug(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_debug(ctx.message)

@bot.command()
async def authenticate(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_authenticate(ctx)

@bot.command()
async def setadmin(ctx):
    await handle_setadmin(ctx)

@bot.command()
async def updatemoondrills(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_update_moondrills(ctx)

@bot.command()
async def checkGoo(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    """Updates the moon goo items in the metenox_goo.yaml file."""
    await ctx.send("Collecting your MoonGoo information. This may take a moment...")
    
    # Call the function to update the YAML file, passing the ctx argument
    await handle_fetch_moon_goo_assets(ctx)


@bot.command()
async def checkGas(ctx):
    await ctx.send("Checking the Fuel Gauges of your Drills! This may take a moment...")
    
    # Call the function to update the YAML file, passing the ctx argument
    await handle_checkgas(ctx)

@bot.command()
async def getMeGoo(ctx):
    await ctx.send("Checking the Fuel Gauges of your Drills! This may take a moment...")
    
    # Call the function to update the YAML file, passing the ctx argument
    await handle_setup(ctx)

@bot.command()
async def goohelp(ctx):
    await handle_help(ctx)


@bot.command()
async def structure(ctx):
    await handle_structure(ctx)


@app.route('/oauth-callback')
def oauth_callback():
    # Extract the code from the query parameters
    code = request.args.get('code')
    state = request.args.get('state')

    if not code or not state:
        return "Missing code or state parameter", 400

    # Exchange the code for tokens
    token_url = 'https://login.eveonline.com/v2/oauth/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CALLBACK_URL,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(token_url, headers=headers, data=data)
    response_data = response.json()

    if 'access_token' not in response_data:
        return f"Error obtaining tokens: {response_data.get('error_description', 'Unknown error')}", 500

    # Extract tokens and expiration information
    access_token = response_data['access_token']
    refresh_token = response_data.get('refresh_token', None)
    expires_in = response_data.get('expires_in', None)

    # Save the tokens
    config.save_tokens(access_token, refresh_token, expires_in)

    return render_template('oauth_callback.html')



    
#### bot start, do not edit!
if __name__ == "__main__":
    try:
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.start()

        bot.run(config.config.get('discord_bot_token', ''))
    except discord.errors.LoginFailure:
        print("Invalid Discord - Bot token. Please check your configuration.")