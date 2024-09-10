import pymongo
import logging
from datetime import datetime
from collections import defaultdict
import os
import yaml
import json
from bson import ObjectId
from administration import get_access_token, fetch_corporation_name
from structurecommands import get_all_structure_assets, get_moon_drills, get_structure_name
from moongoo import get_moon_goo_items
from moongoo_commands import load_moon_goo_from_json
from config import save_server_structures, get_config
import config
import requests

# Load MongoDB config from MongoDB-config.yaml
def load_mongodb_config():
    with open('MongoDB-config.yaml', 'r') as file:
        config_data = yaml.safe_load(file)
        return config_data['mongodb']

# MongoDB connection setup
def get_mongo_client():
    mongodb_config = load_mongodb_config()
    username = mongodb_config.get("username")
    password = mongodb_config.get("password")
    uri = mongodb_config.get("uri").replace("<db_password>", password)
    client = pymongo.MongoClient(uri)
    return client

# Function to save to MongoDB
def save_to_mongodb(data, collection_name, server_id):
    try:
        client = get_mongo_client()
        db = client[load_mongodb_config()['database']]
        collection = db[f"{collection_name}_{server_id}"]

        # Add a timestamp to the data
        data_with_timestamp = {
            "timestamp": datetime.utcnow(),
            "data": data
        }

        collection.insert_one(data_with_timestamp)
        logging.info(f"Data successfully saved to MongoDB in {collection_name}_{server_id}.")
    except Exception as e:
        logging.error(f"Failed to save data to MongoDB: {str(e)}")
    finally:
        client.close()

# Async function to collect gas data
async def collect_gas_data(server_id):
    try:
        # Fetch the access token for the server
        access_token = await get_access_token(server_id)
        if not access_token:
            return 'Failed to get access token'

        headers = {'Authorization': f'Bearer {access_token}'}
        corporation_id = config.get_config("corporation_id", server_id)
        url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/assets/?datasource=tranquility'
        response = requests.get(url, headers=headers)
        data = response.json()

        if 'error' in data:
            return f"Error fetching gas data: {data['error']}"

        # Process and extract gas-related assets
        gas_data = {}
        for asset in data:
            if asset.get('location_flag') == 'StructureFuel' and asset.get('type_id') == 81143:  # Magmatic Gas ID
                gas_data[asset.get('location_id')] = {
                    "quantity": asset.get('quantity'),
                    "structure_name": config.get_structure_name(asset.get('location_id'), server_id)  # Function to get structure name
                }

        return gas_data

    except Exception as e:
        logging.error(f"Failed to collect gas data for server {server_id}: {str(e)}")
        return None

# Async function to collect goo data
async def collect_goo_data(server_id):
    try:
        # Load moon goo items dynamically from JSON file
        moon_goo_items = await load_moon_goo_from_json()
        logging.info(f"Loaded moon goo items: {moon_goo_items}")

        # Fetch the access token for the server
        access_token = await get_access_token(server_id)
        if not access_token:
            return 'Failed to get access token'

        headers = {'Authorization': f'Bearer {access_token}'}
        corporation_id = get_config("corporation_id", server_id)
        url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/assets/?datasource=tranquility'
        response = requests.get(url, headers=headers)
        data = response.json()

        if 'error' in data:
            return f"Error fetching goo data: {data['error']}"

        # Initialize data structure for storing goo-related assets
        goo_data = defaultdict(lambda: defaultdict(int))

        # Loop through assets and check for goo type IDs
        for asset in data:
            location_flag = asset.get('location_flag')
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)
            location_id = asset.get('location_id')

            if location_flag == 'StructureFuel' and type_id in moon_goo_items:
                structure_name = get_structure_name(location_id, server_id)  # Function to get structure name
                item_name = moon_goo_items[type_id]  # Get item name from moon goo items
                goo_data[structure_name][item_name] += quantity

        return goo_data

    except Exception as e:
        logging.error(f"Failed to collect goo data for server {server_id}: {str(e)}")
        return None

async def collect_moon_goo_data_and_save(server_id, structure_name=None):
    moon_goo_items = get_moon_goo_items()
    logging.info(f"Loaded moon goo items: {moon_goo_items}")

    # Collect all structure files for the server
    structure_files = [f for f in os.listdir('.') if f.startswith(f"{server_id}_") and f.endswith("_structures.json")]

    if not structure_files:
        logging.error(f"No structure info files found for server {server_id}.")
        return

    moon_drill_assets = defaultdict(lambda: defaultdict(int))

    async def fetch_and_aggregate_assets(ids, corporation_id, corp_name):
        all_assets_info = await get_all_structure_assets(ids, server_id)
        if isinstance(all_assets_info, str):
            logging.error(all_assets_info)
            return

        for structure_id, assets_info in all_assets_info.items():
            structure_name_in_info = server_structures.get('structure_info', {}).get(str(structure_id), f"Unknown Structure (ID: {structure_id})")
            
            if structure_name and structure_name_in_info != structure_name:
                continue

            for asset in assets_info:
                type_id = asset.get('type_id')
                quantity = asset.get('quantity', 0)

                if type_id in moon_goo_items:
                    item_name = moon_goo_items[type_id]
                    moon_drill_assets[f"{corp_name} - {structure_name_in_info}"][item_name] += quantity

    for structure_file in structure_files:
        corporation_id = structure_file.replace(f"{server_id}_", "").replace("_structures.json", "")
        corp_name = await fetch_corporation_name(corporation_id)

        try:
            with open(structure_file, 'r') as file:
                server_structures = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading or parsing {structure_file}: {e}")
            continue

        moon_drill_ids = server_structures.get('metenox_moon_drill_ids', [])

        if not moon_drill_ids:
            moon_drill_ids = await get_moon_drills(server_id)
            if moon_drill_ids:
                server_structures['metenox_moon_drill_ids'] = moon_drill_ids
                save_server_structures(server_structures, server_id, corporation_id)
            else:
                logging.error(f"No moon drills found for corporation {corporation_id} or an error occurred.")
                continue

        chunk_size = 100
        for i in range(0, len(moon_drill_ids), chunk_size):
            await fetch_and_aggregate_assets(moon_drill_ids[i:i + chunk_size], corporation_id, corp_name)

    if not moon_drill_assets:
        logging.info("mongodb Error: No moon goo data found.")
        return

    # Save the aggregated moon drill assets to MongoDB
    save_to_mongodb(moon_drill_assets, "moon_goo_data", server_id)