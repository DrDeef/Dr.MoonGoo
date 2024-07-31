import asyncio
from datetime import datetime, timedelta
import yaml
import requests
import config

async def run_alert_scheduler(bot):
    while True:
        alert_channel_id = config.get_config('alert_channel_id')
        if not alert_channel_id:
            await asyncio.sleep(3600)  # Sleep for an hour if no alert channel is set
            continue

        alert_channel = bot.get_channel(int(alert_channel_id))
        if alert_channel:
            await check_gas_and_send_alerts(alert_channel)

        await asyncio.sleep(3600)  # Check every hour

async def check_gas_and_send_alerts(alert_channel):
    # Load structure info from YAML file
    try:
        with open('structure_info.yaml', 'r') as file:
            structure_info = yaml.safe_load(file) or {}
    except FileNotFoundError:
        structure_info = {}

    moon_drill_ids = config.get_config('metenox_moon_drill_ids', [])
    all_assets_info = await get_all_structure_assets(moon_drill_ids)

    if isinstance(all_assets_info, str):
        await alert_channel.send(all_assets_info)
        return

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

        if magmatic_gas_days < 2 or (magmatic_gas_days == 1 and magmatic_gas_hours < 24):
            await alert_channel.send(f"**{structure_name}**: Magmatic Gas is running low!\nMagmatic Gas: ***{magmatic_gas_amount}***\nGas runs out in: {magmatic_gas_days} Days {magmatic_gas_hours} Hours")
        
        if fuel_blocks_days < 2 or (fuel_blocks_days == 1 and fuel_blocks_hours < 24):
            await alert_channel.send(f"**{structure_name}**: Fuel Blocks are running low!\nFuel Blocks: ***{fuel_blocks_amount}***\nFuel runs out in: {fuel_blocks_days} Days {fuel_blocks_hours} Hours")

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

async def get_all_structure_assets(structure_ids):
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

async def get_access_token():
    return config.tokens.get('access_token')

