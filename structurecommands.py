import json
import logging
import config
import aiohttp
import asyncio
from administration import get_access_token
from config import save_server_structures, load_server_structures

CORPORATION_ID = config.get_config('corporation_id', '')

## new function
def add_or_update_server(server_id, moon_drill_ids, structure_info):
    # Load existing server structures
    server_structures = load_server_structures()
    
    # Update the entry for the given server ID
    server_structures[server_id] = {
        'metenox_moon_drill_ids': moon_drill_ids,
        'structure_info': structure_info
    }
    
    # Save the updated structures
    save_server_structures(server_structures)


async def update_structure_info(server_id, moon_drill_ids):
    """Fetch and update structure information in the JSON file."""
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"Failed to get access token for server {server_id}.")
        return

    headers = {'Authorization': f'Bearer {access_token}'}
    structure_info = {}

    # Ensure moon_drill_ids is a list
    if not isinstance(moon_drill_ids, list):
        logging.error(f"Expected moon_drill_ids to be a list, got {type(moon_drill_ids)} instead.")
        return

    async with aiohttp.ClientSession() as session:
        for structure_id in moon_drill_ids:
            url = f'https://esi.evetech.net/latest/universe/structures/{structure_id}/'

            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if 'error' in data:
                        logging.error(f"Error fetching structure info for server {server_id}, ID {structure_id}: {data.get('error', 'Unknown error')}")
                        structure_info[structure_id] = 'Unknown Structure'
                    else:
                        structure_name = data.get('name', 'Unknown Structure')
                        structure_info[structure_id] = structure_name
            except aiohttp.ClientError as e:
                logging.error(f"Request error for server {server_id}, ID {structure_id}: {e}")
                structure_info[structure_id] = 'Unknown Structure'

    # Load existing server structures
    server_structures = load_server_structures()

    # Ensure server_structures is a dictionary
    if not isinstance(server_structures, dict):
        logging.error(f"Expected server_structures to be a dict, got {type(server_structures)} instead.")
        return

    # Update the structure information for the server
    if server_id not in server_structures:
        server_structures[server_id] = {'metenox_moon_drill_ids': moon_drill_ids, 'structure_info': structure_info}
    else:
        server_structures[server_id]['structure_info'] = structure_info

    # Save the updated server structures to JSON
    try:
        save_server_structures(server_structures, server_id)  # Note: This should not be await unless it's async
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
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"No access token available for server {server_id}. Cannot fetch moon drills.")
        return []

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = config.get_config('corporation_id', '')
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/structures/?datasource=tranquility'

    ###debug logging.info(f"Fetching moon drills for server {server_id} from URL: {url} with headers: {headers}")

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):  # Retry up to 3 times
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

                    ### debug logging.info(f"Fetched moon drills for server {server_id}: {moon_drill_ids}")

                    return moon_drill_ids
            except aiohttp.ClientError as e:
                logging.error(f"Request error for server {server_id} (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    logging.info("Retrying...")
            except aiohttp.ServerTimeoutError as e:
                logging.error(f"Request timed out for server {server_id} (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    logging.info("Retrying...")
        logging.error(f"All attempts to fetch moon drills for server {server_id} failed.")
        return [...]


async def get_structure_info(server_id, structure_id):
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"Failed to get access token for server {server_id}")
        return "Failed to get access token."

    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/universe/structures/{structure_id}/'
    
    logging.info(f"Fetching structure info for server {server_id} and structure {structure_id} from URL: {url} with headers: {headers}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if 'error' in data:
                    logging.error(f"Error fetching structure info for server {server_id}: {data['error']}")
                    return f"Error fetching structure info for ID {structure_id}: {data.get('error', 'Unknown error')}"
                
                structure_name = data.get('name', 'Unknown Structure')
                return f"Structure ID: {structure_id}\nStructure Name: {structure_name}"
        except aiohttp.ClientError as e:
            logging.error(f"Request error for server {server_id}: {e}")
            return 'Unknown Structure'


async def get_structure_name(server_id, structure_id):
    access_token = await get_access_token(server_id)
    if not access_token:
        logging.error(f"Failed to get access token for server {server_id}")
        return 'Failed to get access token'

    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = config.get_config('corporation_id', '')
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/structures/{structure_id}/?datasource=tranquility'

    logging.info(f"Fetching structure name for server {server_id} and structure {structure_id} from URL: {url} with headers: {headers}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if 'error' in data:
                    logging.error(f"Error fetching structure name for server {server_id}: {data['error']}")
                    return 'Unknown Structure'

                return data.get('name', 'Unknown Structure')
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