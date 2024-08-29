import json
import logging
import config
import aiohttp
import asyncio
from administration import get_access_token, get_latest_token
from config import save_server_structures, load_server_structures, get_config


CORPORATION_ID = config.get_config('corporation_id', '')


def add_or_update_server(server_id, moon_drill_ids, structure_info):
    # Load existing server structures
    server_structures = load_server_structures()
    
    # Update the entry for the given server ID
    server_structures[server_id] = {
        'metenox_moon_drill_ids': moon_drill_ids,
        'structure_info': structure_info
    }
    
    # Save the updated structures
    save_server_structures(server_structures, server_id)


async def update_structure_info(server_id, moon_drill_ids):
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"Failed to get access token for server {server_id}.")
        return

    headers = {'Authorization': f'Bearer {access_token}'}
    structure_info = {}

    async with aiohttp.ClientSession() as session:
        for structure_id in moon_drill_ids:
            url = f'https://esi.evetech.net/latest/universe/structures/{structure_id}/'

            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # Check for valid response
                    if 'name' in data:
                        structure_name = data['name']
                        structure_info[structure_id] = structure_name
                        logging.info(f"Fetched structure name for ID {structure_id}: {structure_name}")
                    else:
                        logging.error(f"Unexpected response format for server {server_id}, ID {structure_id}: {data}")
                        structure_info[structure_id] = 'Unknown Structure'
            except aiohttp.ClientError as e:
                logging.error(f"Request error for server {server_id}, ID {structure_id}: {e}")
                structure_info[structure_id] = 'Unknown Structure'

    # Load and update server structures
    server_structures = load_server_structures()

    if not isinstance(server_structures, dict):
        logging.error(f"Expected server_structures to be a dict, got {type(server_structures)} instead.")
        return

    server_structures[server_id] = {
        'metenox_moon_drill_ids': moon_drill_ids,
        'structure_info': structure_info
    }

    try:
        save_server_structures(server_structures, server_id)
        logging.info(f"Updated structure info for server {server_id}: {structure_info}")
    except Exception as e:
        logging.error(f"Error saving structure info to JSON file: {e}")


    
async def get_all_structure_assets(structure_ids, server_id):
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error('Failed to get access token')
        return 'Failed to get access token'
    
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{CORPORATION_ID}/assets/?datasource=tranquility'
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                
        except aiohttp.ClientError as e:
            logging.error(f"Exception occurred during request: {str(e)}")
            return f"Exception occurred during request: {e}"
        except asyncio.TimeoutError:
            logging.error("Request timed out")
            return "Request timed out"
    
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


async def get_moon_drills(server_id):
    access_token = await get_access_token(server_id, CORPORATION_ID)
    if not access_token:
        logging.error(f"No access token available for server {server_id}. Cannot fetch moon drills.")
        return []

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = get_latest_token(server_id).get('corporation_id')
    if not corporation_id:
        logging.error(f"No corporation ID available for server {server_id}.")
        return []

    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/structures/?datasource=tranquility'
    
    logging.info(f"Fetching moon drills for server {server_id} from URL: {url} with headers: {headers}")

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if 'error' in data:
                        logging.error(f"Error fetching moon drills for server {server_id}: {data['error']}")
                        return []

                    moon_drill_ids = [
                        structure['structure_id']
                        for structure in data
                        if structure['type_id'] == 35835 or 'Automatic Moon Drilling' in [service['name'] for service in structure.get('services', [])]
                    ]

                    logging.info(f"Fetched moon drills for server {server_id}: {moon_drill_ids}")
                    return moon_drill_ids
            except aiohttp.ClientError as e:
                logging.error(f"Request error for server {server_id} (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    logging.info("Retrying...")
            except asyncio.TimeoutError as e:
                logging.error(f"Request timed out for server {server_id} (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    logging.info("Retrying...")
        logging.error(f"All attempts to fetch moon drills for server {server_id} failed.")
        return []


async def get_structure_info(server_id, structure_id):
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"Failed to get access token for server {server_id}.")
        return "Failed to get access token."

    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/universe/structures/{structure_id}/'
    
    logging.info(f"Fetching structure info for server {server_id} and structure {structure_id} from URL: {url}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                # Check if 'name' key exists in the response data
                if 'name' in data:
                    structure_name = data['name']
                    logging.info(f"Successfully fetched structure info for server {server_id}, ID {structure_id}: {structure_name}")
                    return f"Structure ID: {structure_id}\nStructure Name: {structure_name}"
                else:
                    logging.error(f"Unexpected response format for server {server_id}, ID {structure_id}: {data}")
                    return f"Structure ID: {structure_id}\nError: Unexpected response format. No 'name' field found."

        except aiohttp.ClientError as e:
            logging.error(f"Request error for server {server_id}, structure ID {structure_id}: {e}")
            return f"Structure ID: {structure_id}\nError: Failed to retrieve structure info."
        except aiohttp.http_exceptions.HttpProcessingError as e:
            logging.error(f"HTTP processing error for server {server_id}, structure ID {structure_id}: {e}")
            return f"Structure ID: {structure_id}\nError: HTTP processing error."
        except Exception as e:
            logging.error(f"Unexpected error for server {server_id}, structure ID {structure_id}: {e}")
            return f"Structure ID: {structure_id}\nError: An unexpected error occurred."



async def get_structure_name(server_id, structure_id):
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"Failed to get access token for server {server_id}")
        return 'Failed to get access token'

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = get_config('corporation_id', '')
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/structures/{structure_id}/?datasource=tranquility'

    logging.info(f"Fetching structure name for server {server_id} and structure {structure_id} from URL: {url} with headers: {headers}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if 'error' in data:
                    logging.error(f"Error fetching structure name for server {server_id}: {data['error']}")
                    return f"Error fetching structure name for ID {structure_id}: {data.get('error', 'Unknown error')}"
                
                structure_name = data.get('name', 'Unknown Structure')
                return structure_name
        except aiohttp.ClientError as e:
            logging.error(f"Request error for server {server_id}: {e}")
            return 'Unknown Structure'

def load_moon_drill_ids(server_id):
    """Load moon drill IDs for a specific server from the JSON file."""
    try:
        with open('server_structures.json', 'r') as file:
            server_structures = json.load(file)
        
        return server_structures.get(server_id, {}).get('metenox_moon_drill_ids', [])
    
    except FileNotFoundError:
        logging.error("server_structures.json file not found.")
        return []
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from server_structures.json.")
        return []