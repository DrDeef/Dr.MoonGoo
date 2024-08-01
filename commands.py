import discord
import requests
import logging
import yaml
import json
import uuid
import config
from config import load_tokens, save_tokens
from datetime import datetime, timedelta
from collections import defaultdict


# Access config values using the get_config function
ADMIN_CHANNELS = config.get_config('admin_channels', [])
ADMIN_ROLE = config.get_config('admin_role', 'Admin')
CLIENT_ID = config.get_config('eve_online_client_id', '')
CLIENT_SECRET = config.get_config('eve_online_secret_key', '')
CALLBACK_URL = config.get_config('eve_online_callback_url', '')
CORPORATION_ID = config.get_config('corporation_id', '')
MOON_DRILL_IDS = config.get_config('metenox_moon_drill_ids', [])


# Use the updated methods and variables from config.py
tokens = config.tokens
states = config.states

async def save_structure_info_to_yaml(moon_drill_ids):
    access_token = await get_access_token()
    if not access_token:
        logging.error("Failed to get access token.")
        return

    headers = {'Authorization': f'Bearer {access_token}'}
    structure_info = {}

    for structure_id in moon_drill_ids:
        # Use the new endpoint for structure details
        url = f'https://esi.evetech.net/latest/universe/structures/{structure_id}/'
        response = requests.get(url, headers=headers)
        data = response.json()

        if 'error' in data:
            logging.error(f"Error fetching structure info for ID {structure_id}: {data.get('error', 'Unknown error')}")
            structure_info[structure_id] = 'Unknown Structure'
        else:
            structure_name = data.get('name', 'Unknown Structure')
            structure_info[structure_id] = structure_name

    try:
        with open('structure_info.yaml', 'w') as file:
            yaml.dump(structure_info, file)
    except IOError as e:
        logging.error(f"Error saving structure info to YAML file: {e}")

async def load_structure_info_from_yaml():
    global structure_info
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}

async def handle_setup(message):
    # Call authenticate and check if it was successful
    if not await handle_authenticate(message):
        await message.channel.send("Authentication failed. Setup aborted.")
        return

    # Setup completed
    alert_channel_id = str(message.channel.id)
    
    # Set the current channel as an admin channel
    if alert_channel_id not in config.get_config('admin_channels', []):
        config.get_config['admin_channels'].append(alert_channel_id)
        config.save_config()
    
    await message.channel.send(f"Setup complete. Admin channel added.")

    # Set current channel as an alert channel
    config.get_config['alert_channel_id'] = alert_channel_id
    config.save_config()
    
    await message.channel.send(f"Alert channel set to <#{alert_channel_id}>")

async def handle_add_alert_channel(ctx):
    # Retrieve the current channel ID
    alert_channel_id = str(ctx.channel.id)

    # Update the alert channel ID in the configuration
    current_alert_channel_id = config.get_config('alert_channel_id')
    if current_alert_channel_id:
        # If there is already an alert channel set, notify the user
        await ctx.send(f"Alert channel is already set to <#{current_alert_channel_id}>")
    else:
        # Set the new alert channel ID
        config.set_config('alert_channel_id', alert_channel_id)
        config.save_config()
        await ctx.send(f"Alert channel set to <#{alert_channel_id}>")


def generate_state():
    return str(uuid.uuid4())

async def handle_authenticate(message):
    state = generate_state()
    states[state] = True

    auth_url = (
        f"https://login.eveonline.com/v2/oauth/authorize/?response_type=code"
        f"&redirect_uri={CALLBACK_URL}&client_id={CLIENT_ID}"
        f"&scope=esi-search.search_structures.v1+esi-universe.read_structures.v1"
        f"+esi-assets.read_assets.v1+esi-corporations.read_structures.v1"
        f"+esi-assets.read_corporation_assets.v1+publicData&state={state}"
    )

    await message.channel.send(f"Please [click here]({auth_url}) to authenticate.")

    return True

async def handle_setadmin(message):
    admin_channels = config.get_config('admin_channels', [])
    if message.channel.id in admin_channels:
        await message.channel.send("This channel is already an admin channel.")
        return

    admin_channels.append(message.channel.id)
    config.get_config['admin_channels'] = admin_channels
    config.save_config()
    await message.channel.send(f"Admin channel added: {message.channel.id}\nCurrent admin channels: {admin_channels}")

async def handle_showadmin(message):
    admin_channels = config.get_config('admin_channels', [])
    await message.channel.send(f"Current admin channels: {admin_channels}")

async def handle_update_moondrills(ctx):
    await ctx.send("Updating moon drills...")
    
    moon_drill_ids = await get_moon_drills()
    
    if moon_drill_ids:
        # Update the configuration with new moon drill IDs
        config.set_config('metenox_moon_drill_ids', moon_drill_ids)
        
        # Save structure info to YAML
        await save_structure_info_to_yaml(moon_drill_ids)

        await ctx.send(f"Updated moon drill IDs: {moon_drill_ids}")
    else:
        # Ensure the configuration still has an empty list if no IDs are found
        config.set_config('metenox_moon_drill_ids', [])
        await ctx.send("No moon drills found or an error occurred.")

async def get_moon_drills():
    access_token = await get_access_token()
    if not access_token:
        logging.error("No access token available. Cannot fetch moon drills.")
        return []

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = config.get_config('corporation_id', '')
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/structures/?datasource=tranquility'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            logging.error(f"Error fetching moon drills: {data['error']}")
            return []

        moon_drill_ids = [
            structure['structure_id']
            for structure in data
            if structure['type_id'] == 35835 or 'Automatic Moon Drilling' in [service['name'] for service in structure.get('services', [])]
        ]

        return moon_drill_ids
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return []


async def handle_structure(message):
    structure_id = message.content.split()[1]
    structure_info = await get_structure_info(structure_id)
    await message.channel.send(structure_info)



async def handle_checkgas(message):
    # Load structure info from YAML file
    await load_structure_info_from_yaml()

    # Get all moon drill structure IDs from the configuration
    moon_drill_ids = config.get_config('metenox_moon_drill_ids', [])

    # Update moon drills and structure info if the list is empty
    if not moon_drill_ids:
        moon_drill_ids = await get_moon_drills()
        if moon_drill_ids:
            config.set_config('metenox_moon_drill_ids', moon_drill_ids)
            await save_structure_info_to_yaml(moon_drill_ids)
        else:
            await message.channel.send("No moon drills found or an error occurred.")
            return

    # Prepare to fetch and process asset information
    gas_info = ""
    all_assets_info = await get_all_structure_assets(moon_drill_ids)

    if isinstance(all_assets_info, str):
        await message.channel.send(all_assets_info)
        return

    for structure_id, assets_info in all_assets_info.items():
        # Get structure name
        structure_name = structure_info.get(structure_id, 'Unknown Structure')

        # Prepare to aggregate asset quantities
        asset_totals = {
            'Magmatic Gas': 0,
            'Fuel Blocks': 0
        }

        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity')

            if type_id == 81143:  # Type ID for Magmatic Gas
                asset_totals['Magmatic Gas'] += quantity
            elif type_id == 4312:  # Type ID for Fuel Blocks
                asset_totals['Fuel Blocks'] += quantity

        # Calculate depletion times
        def calculate_depletion_time(amount, rate_per_hour):
            if amount <= 0 or rate_per_hour <= 0:
                return "Unknown"

            depletion_hours = amount / rate_per_hour
            depletion_time = datetime.utcnow() + timedelta(hours=depletion_hours)
            remaining_time = depletion_time - datetime.utcnow()

            days, remainder = divmod(remaining_time.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            return f"> {depletion_time.strftime('%Y-%m-%d %H:%M:%S')} UTC - {int(days)} Days {int(hours)} Hours remaining"

        magmatic_gas_amount = asset_totals['Magmatic Gas']
        fuel_blocks_amount = asset_totals['Fuel Blocks']
        
        magmatic_gas_depletion_time = calculate_depletion_time(magmatic_gas_amount, 55)  # 55 units per hour
        fuel_blocks_depletion_time = calculate_depletion_time(fuel_blocks_amount, 5)  # 5 units per hour
        
        # Format the response with Discord markdown
        gas_info += f"**{structure_name}**\n"
        gas_info += f"__Magmatic Gas__: ***{asset_totals['Magmatic Gas']}***\n"
        gas_info += f"Gas runs out in: {magmatic_gas_depletion_time}\n"
        gas_info += f"__Fuel Blocks__: ***{asset_totals['Fuel Blocks']}***\n"
        gas_info += f"Fuel runs out in: {fuel_blocks_depletion_time}\n"
        gas_info += "\n"  # Add a newline for separation

    # Send message in chunks if necessary
    if len(gas_info) > 2000:
        chunks = [gas_info[i:i + 2000] for i in range(0, len(gas_info), 2000)]
        for chunk in chunks:
            await message.channel.send(chunk)
    else:
        await message.channel.send(gas_info)


async def get_all_structure_assets(structure_ids):
    access_token = await get_access_token()
    if not access_token:
        return 'Failed to get access token'
    
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/assets/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if 'error' in data:
        logging.error(f"Error fetching structure assets: {data['error']}")
        return f"Error fetching structure assets: {data['error']}"
    
    all_assets = {}
    for structure_id in structure_ids:
        assets = [asset for asset in data if asset.get('location_id') == structure_id and asset.get('location_flag') == 'StructureFuel']
        if assets:
            all_assets[structure_id] = assets
    
    return all_assets


async def handle_structureassets(message):
    # Load structure info from YAML file
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}

    # Get all moon drill structure IDs from the configuration
    moon_drill_ids = config.get('metenox_moon_drill_ids', [])
    
    # Fetch assets information for all moon drills
    all_assets_info = await get_all_structure_assets(moon_drill_ids)

    if isinstance(all_assets_info, str):
        await message.channel.send(all_assets_info)
    else:
        response = ""
        for structure_id, assets_info in all_assets_info.items():
            # Get structure name
            structure_name = structure_info.get(structure_id, 'Unknown Structure')

            # Prepare to aggregate asset quantities
            asset_totals = {
                'Magmatic Gas': 0,
                'Fuel Blocks': 0
            }

            for asset in assets_info:
                type_id = asset.get('type_id')
                quantity = asset.get('quantity')

                if type_id == 81143:  # Type ID for Magmatic Gas
                    asset_totals['Magmatic Gas'] += quantity
                elif type_id == 4312:  # Type ID for Fuel Blocks
                    asset_totals['Fuel Blocks'] += quantity

            # Build the response string
            response += f"{structure_name}, {structure_id}\n"  # Structure Name and ID
            for asset_name, total_quantity in asset_totals.items():
                response += f"{asset_name}: {total_quantity}\n"
            response += "\n"  # Add a newline for separation

        # Send message in chunks if necessary
        if len(response) > 2000:
            chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send(response)


async def get_structure_name(structure_id):
    # Mock implementation - replace with actual API call or data retrieval
    # Assuming you have a method to get structure names by ID
    access_token = await get_access_token()
    if not access_token:
        return 'Failed to get access token'
    
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/structures/{structure_id}/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if 'error' in data:
        logging.error(f"Error fetching structure name: {data['error']}")
        return 'Unknown Structure'
    
    return data.get('name', 'Unknown Structure')

async def handle_help(message):
    await message.channel.send(
        "Hello My Name is Dr. MoonGoo, here are some basic commands.\n\n"
        "**Common commands:**\n"
        "**!authenticate**: Authenticate the bot against the EvE Online ESI API\n"
        "**!updatemoondrills**: Update your Moondrill Structures\n"
        "**!checkgas**: Prints the amount of Magmatic Gas and Fuel Blocks within the Moondrill with the date/time when it runs out.\n"
        "When setup with !GooAlert I will send you a message in a channel where you run the command if fuel runs out within the next 48 hours\n\n"
        "Feel free to open a GitHub issue here: https://github.com/DrDeef/Dr.MoonGoo"
    )


async def handle_debug(message):
    token_data = load_tokens()  # This needs to be a function in your code

    access_token = token_data.get('access_token', 'No access token found')
    refresh_token = token_data.get('refresh_token', 'No refresh token found')

    await message.channel.send("Debug information: ...")
    await message.channel.send(f'Access Token: {access_token}\nRefresh Token: {refresh_token}')


async def get_structure_info(structure_id):
    access_token = await get_access_token()
    if not access_token:
        return "Failed to get access token."

    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/universe/structures/{structure_id}/'
    response = requests.get(url, headers=headers)
    data = response.json()

    if 'error' in data:
        return f"Error fetching structure info for ID {structure_id}: {data.get('error', 'Unknown error')}"
    
    structure_name = data.get('name', 'Unknown Structure')
    return f"Structure ID: {structure_id}\nStructure Name: {structure_name}"

async def get_access_token():
    tokens = load_tokens()
    
    # Check if there's a valid token already
    if 'access_token' in tokens and not is_token_expired():
        return tokens['access_token']
    
    # Refresh the token if expired or missing
    if 'refresh_token' in tokens:
        new_tokens = await refresh_access_token()
        # Save the new tokens
        with open('tokens.json', 'w') as file:
            json.dump(new_tokens, file, indent=4)
        return new_tokens['access_token']
    
    # Handle the case where no refresh token is available
    return None

def is_token_expired():
    """Check if the stored token is expired."""
    tokens = load_tokens()
    if not tokens:
        # No tokens found
        return True

    created_at_str = tokens.get('created_at')
    expires_in = tokens.get('expires_in')

    if not created_at_str or expires_in is None:
        # Missing token details
        return True

    created_at = datetime.fromisoformat(created_at_str)
    expiration_time = created_at + timedelta(seconds=expires_in)

    # Compare the current time with the expiration time
    return datetime.utcnow() > expiration_time

async def refresh_access_token():
    # Implement your logic to refresh the access token using the refresh token
    refresh_url = 'https://login.eveonline.com/v2/oauth/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(refresh_url, headers=headers, data=data)
    response_data = response.json()

    if 'access_token' in response_data:
        # Save new tokens
        tokens['access_token'] = response_data['access_token']
        tokens['refresh_token'] = response_data.get('refresh_token', tokens['refresh_token'])
        return tokens['access_token']
    else:
        # Handle error
        return None

## new moongoo "feature"

async def save_moon_goo_to_yaml(moon_drill_assets):
    try:
        with open('metenox_goo.yaml', 'w') as file:
            yaml.dump(moon_drill_assets, file)
    except IOError as e:
        logging.error(f"Error saving moon goo info to YAML file: {e}")

async def load_moon_goo_from_yaml():
    try:
        with open('metenox_goo.yaml', 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}

async def get_moon_drill_assets():
    access_token = await get_access_token()
    if not access_token:
        logging.error("No access token available. Cannot fetch moon drill assets.")
        return {}

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = config.get_config('corporation_id', '')
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/assets/?datasource=tranquility'

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return {}

async def handle_fetch_moon_goo_assets(ctx, structure_name=None):
    await ctx.send("Fetching moon goo assets...")

    moon_drill_ids = config.get_config('metenox_moon_drill_ids', [])
    if not moon_drill_ids:
        moon_drill_ids = await get_moon_drills()
        if not moon_drill_ids:
            await ctx.send("No moon drills found or an error occurred.")
            return
        config.set_config('metenox_moon_drill_ids', moon_drill_ids)

    all_assets_info = await get_all_structure_assets(moon_drill_ids)
    if isinstance(all_assets_info, str):
        await ctx.send(all_assets_info)
        return

    moon_goo_items = moongoo.get_moon_goo_items()
    moon_drill_assets = defaultdict(dict)

    for structure_id, assets in all_assets_info.items():
        for asset in assets:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)
            if type_id in moon_goo_items:
                moon_drill_assets[structure_id][moon_goo_items[type_id]] = moon_drill_assets[structure_id].get(moon_goo_items[type_id], 0) + quantity

    await save_moon_goo_to_yaml(moon_drill_assets)

    if structure_name:
        await show_moon_goo_for_structure(ctx, structure_name, moon_drill_assets)
    else:
        await show_all_moon_goo(ctx, moon_drill_assets)

async def show_moon_goo_for_structure(ctx, structure_name, moon_drill_assets):
    structure_info = await load_structure_info_from_yaml()
    for structure_id, assets in moon_drill_assets.items():
        if structure_info.get(structure_id) == structure_name:
            await ctx.send(f"**{structure_name}**:")
            for item, quantity in assets.items():
                await ctx.send(f"**{item}**: {quantity}")
            return

    await ctx.send(f"No data found for structure: {structure_name}")

async def show_all_moon_goo(ctx, moon_drill_assets):
    structure_info = await load_structure_info_from_yaml()
    response = ""

    for structure_id, assets in moon_drill_assets.items():
        structure_name = structure_info.get(structure_id, 'Unknown Structure')
        response += f"**{structure_name}**:\n"
        for item, quantity in assets.items():
            response += f"**{item}**: {quantity}\n"
        response += "\n"

    # Send message in chunks if necessary
    if len(response) > 2000:
        chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)