import discord
import requests
import logging
import yaml
import json
import uuid
import config
import moongoo
import time
from moongoo import get_moon_goo_items
from config import load_tokens, save_tokens
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(level=logging.INFO)


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
    # Setup completed
    alert_channel_id = str(message.channel.id)
    
    # Set the current channel as an admin channel
    if alert_channel_id not in config.get_config('admin_channels', []):
        admin_channels = config.get_config('admin_channels', [])
        admin_channels.append(alert_channel_id)
        config.set_config('admin_channels', admin_channels)
        config.save_config()

    await message.channel.send(f"Setup complete. Admin channel added.")
    
    # Call the update_moondrills function
    await handle_update_moondrills(message)
    
    # Call the handle_checkgas function
    await handle_checkgas(message)
    
    # Call the handle_fetch_moon_goo_assets function
    await handle_fetch_moon_goo_assets(message)

# Example placeholders for the functions called in handle_setup
async def handle_update_moondrills(message):
    # Placeholder function for handle_update_moondrills
    await message.channel.send("Updating moon drills...")

async def handle_checkgas(message):
    # Placeholder function for handle_checkgas
    await message.channel.send("Checking gas...")

async def handle_fetch_moon_goo_assets(message):
    # Placeholder function for handle_fetch_moon_goo_assets
    await message.channel.send("Fetching moon goo assets...")


    # Set current channel as an alert channel
    ##config.get_config['alert_channel_id'] = alert_channel_id
    ##config.save_config()
    
    ##await message.channel.send(f"Alert channel set to <#{alert_channel_id}>")

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

    if isinstance(all_assets_info, list):  # Handle list if returned
        logging.error("Unexpected data format received: list")
        await message.channel.send("Unexpected data format received.")
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
        logging.error('Failed to get access token')
        return 'Failed to get access token'
    
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/assets/?datasource=tranquility'
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Error occurred during request: {req_err}")
        return f"Error occurred during request: {req_err}"
    
    if isinstance(data, list):
        all_assets = {}
        for asset in data:
            structure_id = asset.get('location_id')
            if structure_id in structure_ids:
                if structure_id not in all_assets:
                    all_assets[structure_id] = []
                all_assets[structure_id].append(asset)
        return all_assets
    
    logging.error("Unexpected API response format")
    return "Unexpected API response format"

async def handle_structureassets(ctx):
    # Load structure info from YAML file
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}
        await ctx.send("Structure info file not found. Please ensure 'structure_info.yaml' is present.")
        return

    # Get all moon drill structure IDs from the configuration
    moon_drill_ids = config.get('metenox_moon_drill_ids', [])
    
    if not moon_drill_ids:
        await ctx.send("No moon drill IDs found in the configuration.")
        return

    # Fetch assets information for all moon drills
    all_assets_info = await get_all_structure_assets(moon_drill_ids)

    if isinstance(all_assets_info, str):
        await ctx.send(all_assets_info)
        return

    if not all_assets_info:
        await ctx.send("No assets found for the provided structure IDs.")
        return

    response = ""
    for structure_id, assets_info in all_assets_info.items():
        # Get structure name
        structure_name = structure_info.get(structure_id, 'Unknown Structure')

        # Prepare to aggregate asset quantities
        asset_totals = {name: 0 for name in moongoo.get_moon_goo_items().values()}

        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)
            asset_name = moongoo.get_moon_goo_items().get(type_id, 'Unknown Item')
            asset_totals[asset_name] += quantity

        # Build the response string
        response += f"**{structure_name}** (ID: {structure_id})\n"  # Structure Name and ID
        for asset_name, total_quantity in asset_totals.items():
            response += f"{asset_name}: ***{total_quantity}***\n"
        response += "\n"  # Add a newline for separation

    # Send message in chunks if necessary
    if len(response) > 2000:
        chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)

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
## maybe remove this:
async def save_moon_goo_to_yaml(moon_drill_assets):
    try:
        # Convert defaultdict to a regular dictionary
        regular_dict = {k: dict(v) for k, v in moon_drill_assets.items()}
        logging.info(f"Saving moon goo data to YAML: {regular_dict}")
        with open('metenox_goo.yaml', 'w') as file:
            yaml.dump(regular_dict, file)
    except IOError as e:
        logging.error(f"Error saving moon goo info to YAML file: {e}")
### remove this
async def load_moon_goo_from_yaml():
    try:
        with open('metenox_goo.yaml', 'r') as file:
            data = yaml.safe_load(file) or {}
            # Convert loaded data back to a regular dict
            moon_goo_items = dict(data)
            return moon_goo_items
    except FileNotFoundError:
        return {}
### end remove.


async def save_moon_goo_to_json(moon_drill_assets):
    try:
        # Convert defaultdict to a regular dictionary
        regular_dict = {k: dict(v) for k, v in moon_drill_assets.items()}
        logging.info(f"Saving moon goo data to JSON: {regular_dict}")
        with open('metenox_goo.json', 'w') as file:
            json.dump(regular_dict, file, indent=4)
    except IOError as e:
        logging.error(f"Error saving moon goo info to JSON file: {e}")

async def load_moon_goo_from_json():
    try:
        with open('metenox_goo.json', 'r') as file:
            data = json.load(file) or {}
            # Convert loaded data back to a regular dict
            moon_goo_items = dict(data)
            return moon_goo_items
    except FileNotFoundError:
        return {}
    
## go here dave!

async def handle_fetch_moon_goo_assets(ctx, structure_name=None):
    moon_goo_items = get_moon_goo_items()
    logging.info(f"Loaded moon goo items: {moon_goo_items}")
    
    # Load structure info from YAML file
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}
        await ctx.send("Structure info file not found. Please ensure 'structure_info.yaml' is present.")
        return

    # Get all moon drill structure IDs from the configuration
    moon_drill_ids = config.get_config('metenox_moon_drill_ids', [])
    
    if not moon_drill_ids:
        moon_drill_ids = await get_moon_drills()
        if moon_drill_ids:
            config.set('metenox_moon_drill_ids', moon_drill_ids)
            await save_structure_info_to_json(moon_drill_ids)
        else:
            await ctx.send("No moon drills found or an error occurred.")
            return

    moon_drill_assets = defaultdict(lambda: defaultdict(int))
    
    async def fetch_and_aggregate_assets(ids):
        all_assets_info = await get_all_structure_assets(ids)
        if isinstance(all_assets_info, str):
            await ctx.send(all_assets_info)
            return

        for structure_id, assets_info in all_assets_info.items():
            if structure_name and structure_info.get(structure_id) != structure_name:
                continue

            for asset in assets_info:
                type_id = asset.get('type_id')
                quantity = asset.get('quantity', 0)
                
                if type_id in moon_goo_items:
                    item_name = moon_goo_items[type_id]
                    moon_drill_assets[structure_id][item_name] += quantity

    # Fetch all assets in chunks to avoid timeout issues
    chunk_size = 100  # Adjust this as needed
    for i in range(0, len(moon_drill_ids), chunk_size):
        await fetch_and_aggregate_assets(moon_drill_ids[i:i + chunk_size])

    if not moon_drill_assets:
        await ctx.send("No moon goo data found.")
        return

    # Prepare response message
    response_message = ""
    for structure_id, assets in moon_drill_assets.items():
        structure_name = structure_info.get(structure_id, 'Unknown Structure')
        response_message += f"**{structure_name} (ID: {structure_id})**\n"
        
        for item_name, total_quantity in assets.items():
            response_message += f"__{item_name}__: ***{total_quantity}***\n"
        response_message += "\n"  # Add a newline for separation

    # Save the aggregated moon drill assets to JSON
    try:
        save_data = {structure_id: dict(data) for structure_id, data in moon_drill_assets.items()}
        with open('metenox_goo.json', 'w') as file:
            json.dump(save_data, file, indent=4)  # Save as JSON
        logging.info(f"Saved aggregated moon goo data to JSON: {save_data}")
    except IOError as e:
        logging.error(f"Error saving moon goo info to JSON file: {e}")

    # Send message in chunks if necessary
    if len(response_message) > 2000:
        chunks = [response_message[i:i + 2000] for i in range(0, len(response_message), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response_message)


async def update_moon_goo_items_in_json():
    moon_goo_items = get_moon_goo_items()
    logging.info(f"Loaded moon goo items: {moon_goo_items}")

    moon_drill_ids = get_config('metenox_moon_drill_ids', [])
    logging.info(f"Loaded moon drill IDs: {moon_drill_ids}")
    
    all_assets_info = await get_all_structure_assets(moon_drill_ids)
    
    if isinstance(all_assets_info, str):
        logging.error(all_assets_info)
        return
    
    logging.info(f"Fetched assets info: {all_assets_info}")

    aggregated_data = defaultdict(dict)
    
    for structure_id, assets_info in all_assets_info.items():
        structure_name = f"Station {structure_id}"
        
        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)
            
            if type_id in moon_goo_items:
                item_name = moon_goo_items[type_id]
                if item_name in aggregated_data[structure_name]:
                    aggregated_data[structure_name][item_name] += quantity
                else:
                    aggregated_data[structure_name][item_name] = quantity
    
    if not aggregated_data:
        logging.info("No moon goo data found.")
    else:
        try:
            with open('metenox_goo.json', 'w') as file:
                json.dump(aggregated_data, file, indent=4)
            logging.info("Moon goo items updated successfully!")
        except IOError as e:
            logging.error(f"Error saving moon goo info to JSON file: {e}")

async def fetch_and_aggregate_assets(ids):
    all_assets_info = await get_all_structure_assets(ids)
    
    if isinstance(all_assets_info, str):  # Handle errors as strings
        await ctx.send(all_assets_info)
        return

    if not isinstance(all_assets_info, dict):  # Ensure it's a dict
        logging.error(f"Unexpected data format: {type(all_assets_info)}")
        await ctx.send("Unexpected data format received.")
        return

    for structure_id, assets_info in all_assets_info.items():
        if structure_name and structure_info.get(structure_id) != structure_name:
            continue

        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)
            
            if type_id in moon_goo_items:
                item_name = moon_goo_items[type_id]
                moon_drill_assets[structure_id][item_name] += quantity
