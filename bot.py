import discord
import logging
import threading
import base64
import requests
import uuid
import asyncio
import datetime
from flask import Flask, request, render_template
from discord.ext import commands
from discord.ui import Select, View
from discord.utils import get
from scheduler import run_alert_scheduler
import config
import tasks 
from urllib.parse import quote
from config import get_config, save_tokens, states
from tasks import refresh_token
from commands import (
    handle_setup, handle_authenticate, handle_setadmin, handle_update_moondrills,
    handle_structure, handle_structureassets, handle_checkgas, handle_spacegoblin, handle_debug, handle_showadmin, handle_help, handle_add_alert_channel, handle_fetch_moon_goo_assets
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
    tasks.start_tasks(bot)

@bot.event
async def on_guild_join(guild):
    server_id = str(guild.id)
    config.add_server_id(server_id)
    print(f'Joined new server: {guild.name} ({server_id})')
    # You can also log this information or handle it as needed

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:  # Ensure it's a component interaction
        if interaction.data.get("custom_id") == "select_alert_channel":
            # Handle the select menu interaction
            selected_channel_id = interaction.data.get("values", [])[0]
            server_id = str(interaction.guild.id)  # Get the server ID
            
            # Save the alert channel ID with the server ID in your configuration or JSON file
            alert_channels = config.load_alert_channels()
            alert_channels[server_id] = selected_channel_id
            config.save_alert_channels(alert_channels)

            # Notify the user that the alert channel has been set
            await interaction.response.send_message(f"Alert channel set to <#{selected_channel_id}>")

            # Start the background scheduler (only start it if it's not already running)
            if not any(task.get_name() == f"alert_scheduler_{server_id}" for task in asyncio.all_tasks()):
                asyncio.create_task(run_alert_scheduler(bot, server_id), name=f"alert_scheduler_{server_id}")


async def is_admin(ctx):
    # Get the list of admin roles from the config
    admin_roles = config.config.get('admin_role', [])

    # Check if any of the roles in admin_roles are present in the user's roles
    return any(get(ctx.guild.roles, name=role_name) in ctx.author.roles for role_name in admin_roles)


@bot.command()
async def showadmin(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_showadmin(ctx.message)


@bot.command()
async def selectalertchannel(ctx):
    channels = ctx.guild.text_channels
    if not channels:
        await ctx.send("No text channels found in this server.")
        return

    # Limit the number of options to 25
    options = [discord.SelectOption(label=channel.name, value=str(channel.id)) for channel in channels[:25]]

    if not options:
        await ctx.send("No text channels available for selection.")
        return

    select = Select(
        placeholder="Choose a channel...",
        options=options,
        custom_id="select_alert_channel"
    )
    
    view = View()

    async def select_callback(interaction: discord.Interaction):
        if interaction.user != ctx.author:
            await interaction.response.send_message("You are not allowed to use this menu.", ephemeral=True)
            return
        
        selected_channel_id = interaction.data.get("values", [])[0]  # Get the selected channel ID

        # Save the alert channel ID with the server ID in your configuration or JSON file
        alert_channels = config.load_alert_channels()
        server_id = str(ctx.guild.id)
        alert_channels[server_id] = selected_channel_id
        config.save_alert_channels(alert_channels)

        # Respond to the interaction with a confirmation message
        await interaction.response.send_message(f"Alert channel set to <#{selected_channel_id}>", ephemeral=True)

        # Start the background scheduler (only start it if it's not already running)
        if not any(task.get_name() == f"alert_scheduler_{server_id}" for task in asyncio.all_tasks()):
            asyncio.create_task(run_alert_scheduler(bot, server_id), name=f"alert_scheduler_{server_id}")

    select.callback = select_callback
    view.add_item(select)

    await ctx.send(
        "Select an alert channel:",
        view=view
    )

@bot.command()
async def GooAlert(ctx):
    # Set the alert channel in the configuration
    alert_channel_id = str(ctx.channel.id)
    config.set_config('alert_channel_id', alert_channel_id)
    
    # Notify that the alert channel has been set
    await ctx.send(f"Alert channel set to <#{alert_channel_id}>")

    # Start the background scheduler
    asyncio.create_task(run_alert_scheduler(bot))  # Pass the bot instance


@bot.command()
async def authenticate(ctx):
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await handle_authenticate(ctx)

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
    if not await is_admin(ctx):
        await ctx.send("You are not authorized to use this command.")
        return
    await ctx.send("Running System Check and updating Data... Please Wait")
    
    # Call the function to update the YAML file, passing the ctx argument
    await handle_setup(ctx)

@bot.command()
async def goohelp(ctx):
    await handle_help(ctx)

@bot.command()
async def spacegoblin(ctx):
    await handle_spacegoblin(ctx)

#@bot.command()
#async def structure(ctx, *, structure_id: str):
#    await handle_structure(ctx)

#@bot.command()
#async def structureassets(ctx):
#    await handle_structureassets(ctx)

@app.route('/oauth-callback')
def oauth_callback():
    # Extract the code and state from the query parameters
    code = request.args.get('code')
    state = request.args.get('state')

    if not code or not state:
        return "Missing code or state parameter", 400

    # Retrieve server_id from state
    server_id = states.pop(state, None)
    if not server_id:
        return "Invalid or expired state", 400

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
    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Request error: {e}", 500

    if 'access_token' not in response_data:
        return f"Error obtaining tokens: {response_data.get('error_description', 'Unknown error')}", 500

    # Extract tokens and expiration information
    access_token = response_data['access_token']
    refresh_token = response_data.get('refresh_token', None)
    expires_in = response_data.get('expires_in', None)

    # Save the tokens for the specific server_id
    save_tokens(server_id, access_token, refresh_token, expires_in)

    return render_template('oauth_callback.html')

    
#### bot start, do not edit!
if __name__ == "__main__":
    try:
        config.load_config()
        config.load_tokens()  # Ensure tokens are loaded
        server_ids = config.get_all_server_ids()
        print("Server IDs:", server_ids)

        flask_thread = threading.Thread(target=run_flask)
        flask_thread.start()

        bot.run(config.config.get('discord_bot_token', ''))
    except discord.errors.LoginFailure:
        print("Invalid Discord - Bot token. Please check your configuration.")
