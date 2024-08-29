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
        # Load server structures from JSON file
        server_structures = load_server_structures()
        if not server_structures:
            logging.error("No server structures found.")
            return

        # Iterate over each server ID in the server structures
        for server_id, data in server_structures.items():
            try:
                # Get the moon drill IDs for the current server
                moon_drill_ids = await get_moon_drills(server_id)
                
                if moon_drill_ids:
                    logging.info(f"Moon drills updated for server {server_id}: {moon_drill_ids}")

                    # Update the moon drill IDs in the server structures
                    server_structures[server_id]['metenox_moon_drill_ids'] = moon_drill_ids
                    
                    # Save the updated server structures to the JSON file
                    save_server_structures(server_structures, server_id)
                else:
                    logging.error(f"No moon drills found or an error occurred for server {server_id}.")
            
            except Exception as e:
                logging.error(f"Exception occurred while updating moon drills for server {server_id}: {str(e)}")

    except Exception as e:
        logging.error(f"Exception occurred while loading server structures: {str(e)}")



# Function to start tasks
def start_tasks(bot):
    if not refresh_token_task.is_running():
        logging.info("Starting refresh_token_task.")
        refresh_token_task.start()
    
    ###if not update_moondrills_task.is_running():
    ###    logging.info("Starting update_moondrills_task.")
    ###    update_moondrills_task.start()