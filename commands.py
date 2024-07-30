import discord
import requests
import secrets
import base64
import logging
import urllib.parse
import json
import yaml
import asyncio
import uuid
from datetime import datetime, timedelta
from config import config, save_config, ADMIN_CHANNELS, tokens, states, CLIENT_ID, CLIENT_SECRET, CALLBACK_URL, CORPORATION_ID, MOON_DRILL_IDS, save_tokens, load_tokens

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
    if alert_channel_id not in ADMIN_CHANNELS:
        ADMIN_CHANNELS.append(alert_channel_id)
        config['admin_channels'] = ADMIN_CHANNELS
        save_config(config)
    
    await message.channel.send(f"Setup complete. Admin channel added.")


    # Set current channel as an admin channel
    admin_channel_id = str(message.channel.id)
    if admin_channel_id not in ADMIN_CHANNELS:
        ADMIN_CHANNELS.append(admin_channel_id)
        config['admin_channels'] = ADMIN_CHANNELS
        save_config(config)
        await message.channel.send(f"Admin channel added: {admin_channel_id}")

    # Call handle_update_moondrills
    await handle_update_moondrills(message)


async def handle_add_alert_channel(message):
    alert_channel_id = message.channel.id
    config['alert_channel_id'] = alert_channel_id
    save_config(config)
    await message.channel.send(f"Alert channel set to {alert_channel_id}")

def generate_state():
    return str(uuid.uuid4())

async def handle_authenticate(message):
    # Check if the access token is present
    if 'access_token' in tokens:
        return True
    
    # Generate the state parameter
    state = generate_state()

    # Trigger the authentication process and provide a link
    auth_url = (
        f"https://login.eveonline.com/v2/oauth/authorize/?response_type=code"
        f"&redirect_uri={CALLBACK_URL}&client_id={CLIENT_ID}"
        f"&scope=esi-search.search_structures.v1+esi-universe.read_structures.v1"
        f"+esi-assets.read_assets.v1+esi-corporations.read_structures.v1"
        f"+esi-assets.read_corporation_assets.v1+publicData&state={state}"
    )
    
    await message.channel.send(f"Please authenticate here: {auth_url}")

    # Store the state to check later
    states[state] = True

    # Wait for the authentication to be completed
    await wait_for_authentication()  # No argument needed here
    
    # Check if the token is now present
    if 'access_token' in tokens:
        return True
    else:
        return False

async def handle_setadmin(message):
    admin_channels = config.get('admin_channels', [])
    if message.channel.id in admin_channels:
        await message.channel.send("This channel is already an admin channel.")
        return
    
    admin_channels.append(message.channel.id)
    config['admin_channels'] = admin_channels
    save_config(config)
    await message.channel.send(f"Admin channel added: {message.channel.id}\nCurrent admin channels: {admin_channels}")

async def handle_showadmin(message):
    admin_channels = config.get('admin_channels', [])
    await message.channel.send(f"Current admin channels: {admin_channels}")


async def handle_update_moondrills(message):
    await message.channel.send("Updating moon drills...")
    moon_drill_ids = await get_moon_drills()
    if moon_drill_ids:
        config['metenox_moon_drill_ids'] = moon_drill_ids
        save_config(config)

        # Save structure info to YAML
        await save_structure_info_to_yaml(moon_drill_ids)

        await message.channel.send(f"Updated moon drill IDs: {moon_drill_ids}")
    else:
        await message.channel.send("No moon drills found or an error occurred.")


async def handle_structure(message):
    response = await get_structure_info()
    await message.channel.send(response)

async def handle_checkgas(message):
    # Load structure info from YAML file
    await load_structure_info_from_yaml()
    
    # Get all moon drill structure IDs from the configuration
    moon_drill_ids = config.get('metenox_moon_drill_ids', [])

    # Update moon drills and structure info if the list is empty
    if not moon_drill_ids:
        moon_drill_ids = await get_moon_drills()
        if moon_drill_ids:
            config['metenox_moon_drill_ids'] = moon_drill_ids
            save_config(config)
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

async def wait_for_authentication():
    while 'access_token' not in tokens:
        await asyncio.sleep(1)  # Wait for 1 second before checking again


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


async def handle_debug(message):
    access_token = tokens.get('access_token', 'No access token found')
    refresh_token = tokens.get('refresh_token', 'No refresh token found')
    await message.channel.send(f'Access Token: {access_token}\nRefresh Token: {refresh_token}')

async def get_moon_drills():
    access_token = await get_access_token()
    if not access_token:
        return []
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/structures/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()
    if 'error' in data:
        logging.error(f"Error fetching moon drills: {data['error']}")
        return []
    return [structure['structure_id'] for structure in data if structure['type_id'] == 35835 or 'Automatic Moon Drilling' in [service['name'] for service in structure.get('services', [])]]

async def get_structure_info():
    access_token = await get_access_token()
    if not access_token:
        return 'Failed to get access token'
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/structures/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()
    if 'error' in data:
        logging.error(f"Error fetching structure info: {data['error']}")
        return f"Error fetching structure info: {data['error']}"
    return "\n".join([f"Structure ID: {structure['structure_id']}, Name: {structure['name']}" for structure in data])

async def get_structure_assets(structure_id):
    access_token = await get_access_token()
    if not access_token:
        return None
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/assets/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()
    if 'error' in data:
        logging.error(f"Error fetching structure assets: {data['error']}")
        return None
    # Filter assets to include only those with the given structure_id
    return [asset for asset in data if asset.get('location_id') == structure_id and asset.get('location_flag') == 'StructureFuel']

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
async def get_access_token():
    # Check if we already have an access token
    if 'access_token' in tokens:
        return tokens['access_token']

    # If no access token, try to refresh it
    if 'refresh_token' not in tokens:
        return None

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
        return response_data['access_token']
    
    return None

