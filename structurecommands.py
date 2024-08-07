import yaml
import logging
import requests
import config
import aiohttp
from administration import get_access_token

CORPORATION_ID = config.get_config('corporation_id', '')

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

async def get_moon_drills():
    access_token = await get_access_token()
    if not access_token:
        logging.error("No access token available. Cannot fetch moon drills.")
        return []

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = config.get_config('corporation_id', '')
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/structures/?datasource=tranquility'

    logging.info(f"Fetching moon drills from URL: {url} with headers: {headers}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if 'error' in data:
                    logging.error(f"Error fetching moon drills: {data['error']}")
                    return []

                moon_drill_ids = [
                    structure['structure_id']
                    for structure in data
                    if structure['type_id'] == 35835 or 'Automatic Moon Drilling' in [service['name'] for service in structure.get('services', [])]
                ]

                logging.info(f"Fetched moon drills: {moon_drill_ids}")

                return moon_drill_ids
        except aiohttp.ClientError as e:
            logging.error(f"Request error: {e}")
            return []

async def load_structure_info_from_yaml():
    global structure_info
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}

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
