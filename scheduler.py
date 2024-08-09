import asyncio
from datetime import datetime, timedelta
import yaml
import requests
import config
import logging
from administration import get_access_token
import json
import os
import discord
from discord.ui import Select, View

# Configure logging
logging.basicConfig(level=logging.INFO)

# File to store alert channels
ALERT_CHANNELS_FILE = 'alert_channels.json'

# Dictionary to track the last alert time for each structure
last_alert_times = {
    'magmatic_gas': {},
    'fuel_blocks': {}
}



# Scheduler function to check alerts for all servers
async def run_alert_scheduler(bot, server_id):
    while True:
        alert_channels = config.load_alert_channels()
        alert_channel_id = alert_channels.get(server_id)
        if not alert_channel_id:
            await asyncio.sleep(3600)  # Sleep for an hour if no alert channel is set
            continue

        alert_channel = bot.get_channel(int(alert_channel_id))
        if alert_channel:
            await check_gas_and_send_alerts(bot, alert_channel, server_id)

        await asyncio.sleep(3600)  # Check every hour

# Function to check gas and send alerts for a specific server
async def check_gas_and_send_alerts(bot, alert_channel, server_id):
    # Load structure info from YAML file
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}

    moon_drill_ids = config.get_config('metenox_moon_drill_ids', server_id)
    all_assets_info = await get_all_structure_assets_for_server(moon_drill_ids, server_id)

    if isinstance(all_assets_info, str):
        await alert_channel.send(all_assets_info)
        return

    current_time = datetime.utcnow()

    for structure_id, assets_info in all_assets_info.items():
        structure_name = structure_info.get(structure_id, 'Unknown Structure')
        asset_totals = {'Magmatic Gas': 0, 'Fuel Blocks': 0}

        for asset in assets_info:
            type_id = asset.get('type_id')
            quantity = asset.get('quantity')
            if type_id == 81143:  # Magmatic Gas
                asset_totals['Magmatic Gas'] += quantity
            elif type_id == 4312:  # Fuel Blocks
                asset_totals['Fuel Blocks'] += quantity

        magmatic_gas_amount = asset_totals['Magmatic Gas']
        fuel_blocks_amount = asset_totals['Fuel Blocks']

        magmatic_gas_depletion_time, magmatic_gas_days, magmatic_gas_hours = calculate_depletion_time(magmatic_gas_amount, 55)
        fuel_blocks_depletion_time, fuel_blocks_days, fuel_blocks_hours = calculate_depletion_time(fuel_blocks_amount, 5)

        # Magmatic Gas alert logic
        if magmatic_gas_days < 2 or (magmatic_gas_days == 1 and magmatic_gas_hours < 24):
            if structure_name not in last_alert_times['magmatic_gas']:
                last_alert_times['magmatic_gas'][structure_name] = {
                    '48h': None,
                    '24h': None
                }
            
            # Check 48h alert
            if magmatic_gas_days == 2 and (last_alert_times['magmatic_gas'][structure_name]['48h'] is None or 
                                           current_time - last_alert_times['magmatic_gas'][structure_name]['48h'] >= timedelta(days=1)):
                await alert_channel.send(f"**{structure_name}**: Magmatic Gas is running low!\nMagmatic Gas: ***{magmatic_gas_amount}***\nGas runs out in: {magmatic_gas_days} Days {magmatic_gas_hours} Hours")
                last_alert_times['magmatic_gas'][structure_name]['48h'] = current_time
            
            # Check 24h alert
            elif magmatic_gas_days == 1 and (last_alert_times['magmatic_gas'][structure_name]['24h'] is None or 
                                             current_time - last_alert_times['magmatic_gas'][structure_name]['24h'] >= timedelta(days=1)):
                await alert_channel.send(f"**{structure_name}**: Magmatic Gas is running low!\nMagmatic Gas: ***{magmatic_gas_amount}***\nGas runs out in: {magmatic_gas_days} Days {magmatic_gas_hours} Hours")
                last_alert_times['magmatic_gas'][structure_name]['24h'] = current_time

        # Fuel Blocks alert logic
        if fuel_blocks_days < 2 or (fuel_blocks_days == 1 and fuel_blocks_hours < 24):
            if structure_name not in last_alert_times['fuel_blocks']:
                last_alert_times['fuel_blocks'][structure_name] = {
                    '48h': None,
                    '24h': None
                }

            # Check 48h alert
            if fuel_blocks_days == 2 and (last_alert_times['fuel_blocks'][structure_name]['48h'] is None or 
                                          current_time - last_alert_times['fuel_blocks'][structure_name]['48h'] >= timedelta(days=1)):
                await alert_channel.send(f"**{structure_name}**: Fuel Blocks are running low!\nFuel Blocks: ***{fuel_blocks_amount}***\nFuel runs out in: {fuel_blocks_days} Days {fuel_blocks_hours} Hours")
                last_alert_times['fuel_blocks'][structure_name]['48h'] = current_time
            
            # Check 24h alert
            elif fuel_blocks_days == 1 and (last_alert_times['fuel_blocks'][structure_name]['24h'] is None or 
                                            current_time - last_alert_times['fuel_blocks'][structure_name]['24h'] >= timedelta(days=1)):
                await alert_channel.send(f"**{structure_name}**: Fuel Blocks are running low!\nFuel Blocks: ***{fuel_blocks_amount}***\nFuel runs out in: {fuel_blocks_days} Days {fuel_blocks_hours} Hours")
                last_alert_times['fuel_blocks'][structure_name]['24h'] = current_time


# Helper function to handle alerts
async def handle_alerts(alert_channel, structure_name, alert_type, days, hours, amount, current_time):
    if days < 2 or (days == 1 and hours < 24):
        if structure_name not in last_alert_times[alert_type]:
            last_alert_times[alert_type][structure_name] = {
                '48h': None,
                '24h': None
            }

        # Check 48h alert
        if days == 2 and (last_alert_times[alert_type][structure_name]['48h'] is None or 
                          current_time - last_alert_times[alert_type][structure_name]['48h'] >= timedelta(days=1)):
            await alert_channel.send(f"**{structure_name}**: {alert_type.replace('_', ' ').title()} is running low!\n{alert_type.replace('_', ' ').title()}: ***{amount}***\nRuns out in: {days} Days {hours} Hours")
            last_alert_times[alert_type][structure_name]['48h'] = current_time

        # Check 24h alert
        elif days == 1 and (last_alert_times[alert_type][structure_name]['24h'] is None or 
                            current_time - last_alert_times[alert_type][structure_name]['24h'] >= timedelta(days=1)):
            await alert_channel.send(f"**{structure_name}**: {alert_type.replace('_', ' ').title()} is running low!\n{alert_type.replace('_', ' ').title()}: ***{amount}***\nRuns out in: {days} Days {hours} Hours")
            last_alert_times[alert_type][structure_name]['24h'] = current_time

# Helper function for structure alerts

async def get_all_structure_assets_for_server(structure_ids, server_id):
    access_token = await get_access_token(server_id)
    if not access_token:
        return 'Failed to get access token'
    
    headers = {'Authorization': f'Bearer {access_token}'}
    corporation_id = config.get_config("corporation_id", server_id)
    url = f'https://esi.evetech.net/latest/corporations/{corporation_id}/assets/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()

    if 'error' in data:
        return f"Error fetching structure assets: {data['error']}"
    
    all_assets = {}
    for structure_id in structure_ids:
        assets = [asset for asset in data if asset.get('location_id') == structure_id and asset.get('location_flag') == 'StructureFuel']
        if assets:
            all_assets[structure_id] = assets
    
    return all_assets


# Function to calculate depletion time
def calculate_depletion_time(amount, rate_per_hour):
    if amount <= 0 or rate_per_hour <= 0:
        return "Unknown", 0, 0

    depletion_hours = amount / rate_per_hour
    depletion_time = datetime.utcnow() + timedelta(hours=depletion_hours)
    remaining_time = depletion_time - datetime.utcnow()

    days, remainder = divmod(remaining_time.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return depletion_time, int(days), int(hours)

# Function to get all structure assets for a specific server
async def get_all_structure_assets(structure_ids, server_id):
    access_token = await get_access_token()
    if not access_token:
        return 'Failed to get access token'
    
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://esi.evetech.net/latest/corporations/{config.get_config("corporation_id")}/assets/?datasource=tranquility'
    response = requests.get(url, headers=headers)
    data = response.json()

    if 'error' in data:
        return f"Error fetching structure assets: {data['error']}"
    
    all_assets = {}
    for structure_id in structure_ids:
        assets = [asset for asset in data if asset.get('location_id') == structure_id and asset.get('location_flag') == 'StructureFuel']
        if assets:
            all_assets[structure_id] = assets
    
    return all_assets

# Function to load server structures
def load_server_structures():
    server_structures_file = 'server_structures.json'
    if os.path.exists(server_structures_file):
        with open(server_structures_file, 'r') as file:
            return json.load(file)
    return {}
