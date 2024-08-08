import discord
import requests
import logging
import yaml
import json
import uuid
import config
import moongoo
import time
from structurecommands import get_all_structure_assets, get_moon_drills
from moongoo import get_moon_goo_items
from config import save_server_structures
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(level=logging.INFO)


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
    
async def handle_fetch_moon_goo_assets(ctx, structure_name=None):
    moon_goo_items = get_moon_goo_items()
    logging.info(f"Loaded moon goo items: {moon_goo_items}")

    # Define the JSON file path
    structure_info_file = 'server_structures.json'

    # Load structure info from JSON file
    try:
        with open(structure_info_file, 'r') as file:
            server_structures = json.load(file)
    except FileNotFoundError:
        server_structures = {}
        await ctx.send(f"Structure info file not found. Please ensure '{structure_info_file}' is present.")
        return
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file {structure_info_file}.")
        await ctx.send(f"Error reading '{structure_info_file}'. Please ensure the file is correctly formatted.")
        return

    # Get the server ID from the context
    server_id = str(ctx.guild.id)

    # Get all moon drill structure IDs from the configuration
    moon_drill_ids = server_structures.get(server_id, {}).get('metenox_moon_drill_ids', [])
    
    if not moon_drill_ids:
        moon_drill_ids = await get_moon_drills()
        if moon_drill_ids:
            # Update server structures with new moon drill IDs
            if server_id not in server_structures:
                server_structures[server_id] = {'metenox_moon_drill_ids': moon_drill_ids, 'structure_info': {}}
            else:
                server_structures[server_id]['metenox_moon_drill_ids'] = moon_drill_ids
            
            # Save the updated server structures to JSON
            save_server_structures(server_structures)
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
            # Filter by structure name if provided
            structure_name_in_info = server_structures.get(server_id, {}).get('structure_info', {}).get(str(structure_id), 'Unknown Structure')
            if structure_name and structure_name_in_info != structure_name:
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
        structure_name = server_structures.get(server_id, {}).get('structure_info', {}).get(str(structure_id), 'Unknown Structure')
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

    moon_drill_ids = config.get_config('metenox_moon_drill_ids', [])
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