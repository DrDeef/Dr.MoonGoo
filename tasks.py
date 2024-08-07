import logging
import config
from structurecommands import get_moon_drills, save_structure_info_to_yaml
from discord.ext import tasks
from administration import refresh_token


# Periodic task to refresh token every 5 minutes
@tasks.loop(minutes=5)
async def refresh_token_task():
    await refresh_token()

# Periodic task to update moon drills every 30 minutes
@tasks.loop(minutes=30)
async def update_moondrills_task():
    moon_drill_ids = await get_moon_drills()
    if moon_drill_ids:
        logging.info(f"Moon drills updated: {moon_drill_ids}")
        # Update the configuration with new moon drill IDs
        config.set_config('metenox_moon_drill_ids', moon_drill_ids)
        # Optionally, save the updated moon drill IDs to a file
        await save_structure_info_to_yaml(moon_drill_ids)
    else:
        logging.error("No moon drills found or an error occurred.")

# Load configuration and tokens
config.load_config()
config.load_tokens()

# Function to start tasks
def start_tasks(bot):
    if not refresh_token_task.is_running():
        refresh_token_task.start()
    if not update_moondrills_task.is_running():
        update_moondrills_task.start()