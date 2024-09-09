import logging
import config
from config import save_server_structures, load_server_structures
from structurecommands import get_moon_drills
from discord.ext import tasks
from administration import refresh_all_tokens

# Task to refresh all tokens
@tasks.loop(minutes=5)
async def refresh_token_task():
    try:
        await refresh_all_tokens()
    except Exception as e:
        logging.error(f"Task failed to refresh tokens!: {str(e)}")

# Task to update moon drills
@tasks.loop(minutes=30)
async def update_moondrills_task():
    try:
        # Iterate over each server configured
        server_list = config.get_config('server_list')
        if not server_list:
            logging.error("No servers found in the configuration.")
            return

        for server_id in server_list:
            try:
                # Load the corporation ID for the current server
                corporation_id = config.get_config('corporation_id', server_id)
                
                # Load the server structures from JSON using server_id and corporation_id
                server_structures = load_server_structures(server_id, corporation_id)
                if not server_structures:
                    logging.error(f"No structures found for server {server_id}.")
                    continue
                
                # Get moon drill IDs for the current server
                moon_drill_ids = await get_moon_drills(server_id)
                if moon_drill_ids:
                    logging.info(f"Moon drills updated for server {server_id}: {moon_drill_ids}")
                    
                    # Update the moon drill IDs in the server structures
                    server_structures['metenox_moon_drill_ids'] = moon_drill_ids
                    
                    # Save the updated server structures
                    save_server_structures(server_structures, server_id, corporation_id)
                else:
                    logging.error(f"No moon drills found or an error occurred for server {server_id}.")
            
            except Exception as e:
                logging.error(f"Exception occurred while updating moon drills for server {server_id}: {str(e)}")

    except Exception as e:
        logging.error(f"Exception occurred while updating moon drills: {str(e)}")

# Function to start tasks
def start_tasks(bot):
    if not refresh_token_task.is_running():
        logging.info("Starting refresh_token_task.")
        refresh_token_task.start()
    
    if not update_moondrills_task.is_running():
        logging.info("Starting update_moondrills_task.")
        update_moondrills_task.start()
