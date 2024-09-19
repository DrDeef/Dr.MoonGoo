import logging
import config
from config import save_server_structures, load_server_structures
from structurecommands import get_moon_drills
from discord.ext import tasks
from administration import refresh_all_tokens
import os
from mongodatabase import collect_moon_goo_data_and_save
from market_calculation import fetch_market_stats_for_items
import json

# Task to refresh all tokens
@tasks.loop(minutes=5)
async def refresh_token_task():
    try:
        await refresh_all_tokens()
    except Exception as e:
        logging.error(f"Task failed to refresh tokens!: {str(e)}")

@tasks.loop(hours=6)
async def fetch_market_stats_task():
    try:
        await fetch_market_stats_for_items()
    except Exception as e:
        logging.error(f"Exception in fetch_market_stats_task: {str(e)}")

@tasks.loop(minutes=60)
async def save_data_to_mongodb_task():
    try:
        # Load all server IDs (assuming these are stored in a config or accessible in some other way)
        all_server_ids = [f.split('_')[0] for f in os.listdir('.') if f.endswith("_structures.json")]
        unique_server_ids = list(set(all_server_ids))

        for server_id in unique_server_ids:
            # Check if MongoDB integration is enabled for this server
            use_mongodb = config.get_config("use_mongodb", server_id)
            
            if use_mongodb:
                logging.info(f"Starting moon goo data collection for server {server_id}.")
                
                # Collect and save moon goo data to MongoDB
                await collect_moon_goo_data_and_save(server_id)
            else:
                logging.info(f"MongoDB integration is disabled for server {server_id}. Skipping MongoDB save.")
                
    except Exception as e:
        logging.error(f"Exception occurred in save_data_to_mongodb_task: {str(e)}")


# Task to update moon drills
@tasks.loop(minutes=30)
async def update_moondrills_task():
    try:
        # Get server IDs from structure files
        all_server_ids = {f.split('_')[0] for f in os.listdir('.') if f.endswith("_structures.json")}
        
        for server_id in all_server_ids:
            try:
                # Collect all structure files for the server (e.g., {server_id}_{corporation_id}_structures.json)
                structure_files = [f for f in os.listdir('.') if f.startswith(f"{server_id}_") and f.endswith("_structures.json")]

                if not structure_files:
                    logging.debug(f"No structure info files found for server {server_id}.")
                    continue

                # Loop through each corporation's structure file
                for structure_file in structure_files:
                    # Extract corporation ID from the file name (assuming format {server_id}_{corporation_id}_structures.json)
                    corporation_id = structure_file.replace(f"{server_id}_", "").replace("_structures.json", "")

                    # Load the structure info for the corporation from JSON
                    try:
                        with open(structure_file, 'r') as file:
                            server_structures = json.load(file)
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        logging.error(f"Error loading or parsing {structure_file}: {e}")
                        continue
                    
                    # Get moon drill structure IDs for the current server
                    moon_drill_ids = await get_moon_drills(server_id)
                    
                    if moon_drill_ids:
                        logging.debug(f"Moon drills updated for server {server_id} and corporation {corporation_id}: {moon_drill_ids}")

                        # Update the moon drill IDs in the server structures
                        server_structures['metenox_moon_drill_ids'] = moon_drill_ids

                        # Save the updated server structures back to the JSON file
                        save_server_structures(server_structures, server_id, corporation_id)
                    else:
                        logging.debug(f"No moon drills found or an error occurred for server {server_id} and corporation {corporation_id}.")
            
            except Exception as e:
                logging.debug(f"Exception occurred while updating moon drills for server {server_id}: {str(e)}")

    except Exception as e:
        logging.debug(f"Exception occurred while updating moon drills: {str(e)}")

    pass

# Function to start tasks
def start_tasks(bot):
    if not refresh_token_task.is_running():
        logging.info("Starting refresh_token_task.")
        refresh_token_task.start()
    if not update_moondrills_task.is_running():
        logging.info("Starting update_moondrills_task.")
        update_moondrills_task.start()
    if not save_data_to_mongodb_task.is_running():
        logging.info("Starting save_data_to_mongodb_task.")
        save_data_to_mongodb_task.start()
    if not fetch_market_stats_task.is_running():
        logging.info("Starting fetch_market_stats_task.")
        fetch_market_stats_task.start()