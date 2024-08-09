import logging
import yaml
import json
import uuid
import config
import moongoo
import os
from moongoo_commands import handle_fetch_moon_goo_assets
from config import load_tokens, save_server_structures, load_server_structures
from datetime import datetime, timedelta
from collections import defaultdict
from structurecommands import get_all_structure_assets, get_moon_drills, update_structure_info

logging.basicConfig(level=logging.INFO)


# Access config values using the get_config function
ADMIN_CHANNELS = config.get_config('admin_channels', [])
ADMIN_ROLE = config.get_config('admin_role', 'Admin')
CLIENT_ID = config.get_config('eve_online_client_id', '')
CLIENT_SECRET = config.get_config('eve_online_secret_key', '')
CALLBACK_URL = config.get_config('eve_online_callback_url', '')
CORPORATION_ID = config.get_config('corporation_id', '')
MOON_DRILL_IDS = config.get_config('metenox_moon_drill_ids', [])


# Use the updated methods and variables from config.py
tokens = config.tokens
states = config.states



async def handle_setup(message):
    # Setup completed
    alert_channel_id = str(message.channel.id)
    
    # Set the current channel as an admin channel
    if alert_channel_id not in config.get_config('admin_channels', []):
        admin_channels = config.get_config('admin_channels', [])
        admin_channels.append(alert_channel_id)
        config.set_config('admin_channels', admin_channels)
        config.save_config()

    await message.channel.send(f"Setup complete. Admin channel added.")
    
    # Call the update_moondrills function
    await handle_update_moondrills(message)
    
    # Call the handle_checkgas function
    await handle_checkgas(message)
    
    # Call the handle_fetch_moon_goo_assets function
    await handle_fetch_moon_goo_assets(message)


async def handle_add_alert_channel(ctx):
    # Retrieve the current channel ID
    alert_channel_id = str(ctx.channel.id)

    # Update the alert channel ID in the configuration
    current_alert_channel_id = config.get_config('alert_channel_id')
    if current_alert_channel_id:
        # If there is already an alert channel set, notify the user
        await ctx.send(f"Alert channel is already set to <#{current_alert_channel_id}>")
    else:
        # Set the new alert channel ID
        config.set_config('alert_channel_id', alert_channel_id)
        config.save_config()
        await ctx.send(f"Alert channel set to <#{alert_channel_id}>")


def generate_state():
    return str(uuid.uuid4())

async def handle_authenticate(message):
    server_id = message.guild.id  # Get the server ID from the message's guild
    state = generate_state()  # Generate a new state
    states[state] = server_id  # Store the server ID associated with the state

    auth_url = (
        f"https://login.eveonline.com/v2/oauth/authorize/?response_type=code"
        f"&redirect_uri={CALLBACK_URL}&client_id={CLIENT_ID}"
        f"&scope=esi-search.search_structures.v1+esi-universe.read_structures.v1"
        f"+esi-assets.read_assets.v1+esi-corporations.read_structures.v1"
        f"+esi-assets.read_corporation_assets.v1+publicData&state={state}"
    )

    await message.channel.send(f"Please [click here]({auth_url}) to authenticate.")

    return True

async def handle_setadmin(message):
    admin_channels = config.get_config('admin_channels', [])
    if message.channel.id in admin_channels:
        await message.channel.send("This channel is already an admin channel.")
        return

    admin_channels.append(message.channel.id)
    config.get_config['admin_channels'] = admin_channels
    config.save_config()
    await message.channel.send(f"Admin channel added: {message.channel.id}\nCurrent admin channels: {admin_channels}")

async def handle_showadmin(message):
    admin_channels = config.get_config('admin_channels', [])
    await message.channel.send(f"Current admin channels: {admin_channels}")

async def handle_update_moondrills(ctx):
    server_id = str(ctx.guild.id)  # Get server_id from the context
    await ctx.send("Updating moon drills... Please wait.... \n \n")

    # Fetch the new moon drill IDs
    moon_drill_ids = await get_moon_drills(server_id)

    if moon_drill_ids:
        # Load existing server structures
        server_structures = load_server_structures()

        # Debugging output
        print(f"Type of server_structures: {type(server_structures)}")
        print(f"Contents of server_structures: {server_structures}")

        # Ensure server_structures is a dictionary
        if not isinstance(server_structures, dict):
            logging.error(f"Expected server_structures to be a dict, got {type(server_structures)} instead.")
            await ctx.send("An internal error occurred. Please try again later.")
            return

        # Update the server's moon drill IDs
        if server_id not in server_structures:
            server_structures[server_id] = {'metenox_moon_drill_ids': moon_drill_ids, 'structure_info': {}}
        else:
            server_structures[server_id]['metenox_moon_drill_ids'] = moon_drill_ids

        # Save the updated server structures to JSON
        try:
            save_server_structures(server_structures, server_id)
        except ValueError as ve:
            logging.error(f"Error in save_server_structures: {ve}")
            await ctx.send("Failed to save server structures. Please try again later.")
            return

        # Fetch and update structure information
        try:
            await update_structure_info(server_id, moon_drill_ids)
        except Exception as e:
            logging.error(f"Error updating structure info: {e}")
            await ctx.send("Failed to update structure information. Please try again later.")
            return

        # Reload the updated structure info
        server_structures = load_server_structures()
        structure_info = server_structures.get(server_id, {}).get('structure_info', {})

        # Prepare the response with structure names and IDs
        response_message = "Metenox Moondrills successfully updated.\n"
        for moon_drill_id in moon_drill_ids:
            structure_name = structure_info.get(str(moon_drill_id), 'Unknown Structure')
            response_message += f"{moon_drill_id} - {structure_name}\n"

        await ctx.send(response_message)
    else:
        # Ensure the server entry is present with an empty list if no IDs are found
        server_structures = load_server_structures()

        # Debugging output
        print(f"Type of server_structures: {type(server_structures)}")
        print(f"Contents of server_structures: {server_structures}")

        if not isinstance(server_structures, dict):
            logging.error(f"Expected server_structures to be a dict, got {type(server_structures)} instead.")
            await ctx.send("An internal error occurred. Please try again later.")
            return

        if server_id not in server_structures:
            server_structures[server_id] = {'metenox_moon_drill_ids': [], 'structure_info': {}}
        else:
            server_structures[server_id]['metenox_moon_drill_ids'] = []

        # Save the updated server structures to JSON
        try:
            await save_server_structures(server_structures, server_id)
        except ValueError as ve:
            logging.error(f"Error in save_server_structures: {ve}")
            await ctx.send("Failed to save server structures. Please try again later.")

        await ctx.send("No moon drills found or an error occurred.")


async def handle_structure(ctx):
    # Extract the structure ID from the command arguments
    if len(ctx.args) < 1:
        await ctx.send("Please provide a structure ID.")
        return
    
    structure_id = ctx.args[0]
    
    # Load existing server structures
    server_structures = load_server_structures()
    
    # Check if the structure ID is present in the structure_info of any server
    structure_info = 'Structure info not found.'
    for server_data in server_structures.values():
        if structure_id in server_data.get('structure_info', {}):
            structure_info = server_data['structure_info'][structure_id]
            break
    
    await ctx.send(structure_info if structure_info != 'Structure info not found.' else f"Structure ID {structure_id} not found.")

async def handle_checkgas(ctx):
    server_id = str(ctx.guild.id)  # Get the server ID from the context

    # Load server structures from JSON file
    server_structures = load_server_structures()

    if server_id not in server_structures:
        await ctx.send(".")
        return

    structure_info = server_structures[server_id].get('structure_info', {})
    moon_drill_ids = server_structures[server_id].get('metenox_moon_drill_ids', [])

    # Update moon drills and structure info if the list is empty
    if not moon_drill_ids:
        moon_drill_ids = await get_moon_drills(server_id)
        if moon_drill_ids:
            server_structures[server_id]['metenox_moon_drill_ids'] = moon_drill_ids
            # Save structure info in the JSON file
            await update_structure_info(server_id, moon_drill_ids)
            save_server_structures(server_structures)
            await ctx.send(f"Metenox Moondrills successfully updated.\n > Moondrill-ID's: \n > {moon_drill_ids}")
        else:
            await ctx.send("No moon drills found or an error occurred.")
            return

    # Prepare to fetch and process asset information
    gas_info = ""
    all_assets_info = await get_all_structure_assets(moon_drill_ids, server_id)

    if isinstance(all_assets_info, str):
        await ctx.send(all_assets_info)
        return

    if isinstance(all_assets_info, list):  # Handle list if returned
        logging.error("Unexpected data format received: list")
        await ctx.send("Unexpected data format received.")
        return

    for structure_id, assets_info in all_assets_info.items():
        # Ensure structure_id is treated as string when accessing structure_info
        structure_name = structure_info.get(str(structure_id), 'Unknown Structure')

        # Prepare to aggregate asset quantities
        asset_totals = {
            'Magmatic Gas': 0,
            'Fuel Blocks': 0
        }

        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)

            if type_id == 81143:  # Type ID for Magmatic Gas
                asset_totals['Magmatic Gas'] += quantity
            elif type_id in [4312, 4246, 4247, 4051]:  # Type IDs for Fuel Blocks
                asset_totals['Fuel Blocks'] += quantity

        # Calculate depletion times
        def calculate_depletion_time(amount, rate_per_hour):
            if amount <= 0 or rate_per_hour <= 0:
                return "Unknown"

            depletion_hours = amount / rate_per_hour
            depletion_time = datetime.utcnow() + timedelta(hours=depletion_hours)
            remaining_time = depletion_time - datetime.utcnow()

            days, remainder = divmod(remaining_time.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)

            return f"> {depletion_time.strftime('%Y-%m-%d %H:%M:%S')} UTC - {int(days)} Days {int(hours)} Hours remaining"

        magmatic_gas_amount = asset_totals['Magmatic Gas']
        fuel_blocks_amount = asset_totals['Fuel Blocks']
        
        magmatic_gas_depletion_time = calculate_depletion_time(magmatic_gas_amount, 55)  # 55 units per hour
        fuel_blocks_depletion_time = calculate_depletion_time(fuel_blocks_amount, 5)  # 5 units per hour
        
        # Format the response with Discord markdown
        gas_info += f"**{structure_name}**\n"
        gas_info += f"__Magmatic Gas__: ***{magmatic_gas_amount}***\n"
        gas_info += f"Gas runs out in: {magmatic_gas_depletion_time}\n"
        gas_info += f"__Fuel Blocks__: ***{fuel_blocks_amount}***\n"
        gas_info += f"Fuel runs out in: {fuel_blocks_depletion_time}\n"
        gas_info += "\n"  # Add a newline for separation

    # Send message in chunks if necessary
    if len(gas_info) > 2000:
        chunks = [gas_info[i:i + 2000] for i in range(0, len(gas_info), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(gas_info)



async def handle_structureassets(ctx):
    # Define the JSON file path
    server_structures_file = 'server_structures.json'

    # Load structure info from JSON file
    try:
        with open(server_structures_file, 'r') as file:
            server_structures = json.load(file)
    except FileNotFoundError:
        logging.error(f"File {server_structures_file} not found.")
        await ctx.send(f"Server structures file not found. Please ensure '{server_structures_file}' is present.")
        return
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file {server_structures_file}.")
        await ctx.send(f"Error reading '{server_structures_file}'. Please ensure the file is correctly formatted.")
        return

    # Get the server ID from the context
    server_id = str(ctx.guild.id)
    
    # Check if the server ID is in the loaded data
    if server_id not in server_structures:
        await ctx.send(f"No data found for server ID {server_id}.")
        return
    
    # Access moon drill structure IDs from the server structures
    moon_drill_ids = server_structures[server_id].get('metenox_moon_drill_ids', [])
    
    if not moon_drill_ids:
        await ctx.send("No moon drill IDs found for the server.")
        return

    # Fetch assets information for all moon drills
    all_assets_info = await get_all_structure_assets(moon_drill_ids, server_id)

    if isinstance(all_assets_info, str):
        await ctx.send(all_assets_info)
        return

    if not all_assets_info:
        await ctx.send("No assets found for the provided structure IDs.")
        return

    response = ""
    for structure_id, assets_info in all_assets_info.items():
        # Get structure name from server structures
        structure_name = server_structures[server_id]['structure_info'].get(str(structure_id), 'Unknown Structure')

        # Prepare to aggregate asset quantities
        asset_totals = {name: 0 for name in moongoo.get_moon_goo_items().values()}

        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity', 0)
            asset_name = moongoo.get_moon_goo_items().get(type_id, 'Unknown Item')
            asset_totals[asset_name] += quantity

        # Build the response string
        response += f"**{structure_name}** (ID: {structure_id})\n"  # Structure Name and ID
        for asset_name, total_quantity in asset_totals.items():
            response += f"{asset_name}: ***{total_quantity}***\n"
        response += "\n"  # Add a newline for separation

    # Send message in chunks if necessary
    if len(response) > 2000:
        chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)



async def handle_debug(message):
    token_data = load_tokens()  # This needs to be a function in your code

    access_token = token_data.get('access_token', 'No access token found')
    refresh_token = token_data.get('refresh_token', 'No refresh token found')

    await message.channel.send("Debug information: ...")
    await message.channel.send(f'Access Token: {access_token}\nRefresh Token: {refresh_token}')

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



async def handle_spacegoblin(message):
    await message.channel.send(
        "**Guess who is a good Spacegoblin?**.\n\n"
        "Not you, since you are not an Evil Space Goblin\n"
        ";....;"
    )
