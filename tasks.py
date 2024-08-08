import logging
import config
from config import save_server_structures
from structurecommands import get_moon_drills
from discord.ext import tasks
from administration import refresh_token


# Periodic task to refresh token every 5 minutes
@tasks.loop(minutes=5)
async def refresh_token_task():
    server_id = config.get_config('server_id')  # Retrieve the server_id from your configuration

    if not server_id:
        logging.error("Server ID not found in the configuration.")
        return

    response = await refresh_token(server_id)
    if response:
        logging.info(f"Access token refreshed successfully for server {server_id}.")
    else:
        logging.error(f"Failed to refresh access token for server {server_id}.")


# Periodic task to update moon drills every 30 minutes
@tasks.loop(minutes=30)
async def update_moondrills_task():
    server_id = 'your_server_id_here'  # Set your server ID here or get it dynamically

    if not server_id:
        logging.error("Server ID not found.")
        return

    moon_drill_ids = await get_moon_drills(server_id)
    
    if moon_drill_ids:
        logging.info(f"Moon drills updated for server {server_id}: {moon_drill_ids}")

        # Save the updated moon drill IDs to the JSON file
        await save_server_structures(moon_drill_ids, server_id)
    else:
        logging.error(f"No moon drills found or an error occurred for server {server_id}.")


# Load configuration and tokens
config.load_config()
config.load_tokens()

# Function to start tasks
def start_tasks(bot):
    if not refresh_token_task.is_running():
        refresh_token_task.start()
    if not update_moondrills_task.is_running():
        update_moondrills_task.start()