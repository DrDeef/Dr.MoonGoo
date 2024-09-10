import aiohttp
import asyncio
import logging
import json
import requests
import pandas as pd 
from moongoo import get_moon_goo_items

API_URL = "https://evetycoon.com/api/v1/market/stats/10000002"
SAVE_FILE = "market_stats.json"
REGION_ID = '10000002'  # Region ID for The Forge
MOON_GOO_ITEMS_FILE = 'metenox_goo.json'  # File with moon goo items

async def fetch_market_stats():
    try:
        moon_goo_items = get_moon_goo_items()  # Get the type IDs of moon goo items
        market_stats = {}

        for type_id in moon_goo_items.keys():
            url = f"{API_URL}/{type_id}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                market_stats[type_id] = {
                    "buyVolume": data["buyVolume"],
                    "sellVolume": data["sellVolume"],
                    "buyOrders": data["buyOrders"],
                    "sellOrders": data["sellOrders"],
                    "buyAvgFivePercent": data["buyAvgFivePercent"],
                    "sellAvgFivePercent": data["sellAvgFivePercent"]
                }
            else:
                logging.error(f"Failed to fetch data for type_id {type_id}: {response.status_code}")

        # Save market stats to a JSON file, replacing the old file
        with open(SAVE_FILE, 'w') as f:
            json.dump(market_stats, f, indent=4)

        logging.info(f"Market stats updated and saved to {SAVE_FILE}")

    except Exception as e:
        logging.error(f"Failed to fetch market stats: {str(e)}")

async def calculate_market_data():
    try:
        # Load moon goo items
        with open(MOON_GOO_ITEMS_FILE, 'r') as file:
            moon_goo_items = json.load(file)
        
        if not moon_goo_items:
            logging.error("No moon goo items found.")
            return
        
        market_data = {}
        
        async def process_item(type_id, item_name):
            stats = await fetch_market_stats(type_id)
            if stats:
                market_data[item_name] = {
                    'buyVolume': stats.get('buyVolume'),
                    'sellVolume': stats.get('sellVolume'),
                    'buyOrders': stats.get('buyOrders'),
                    'sellOrders': stats.get('sellOrders'),
                    'buyOutliers': stats.get('buyOutliers'),
                    'sellOutliers': stats.get('sellOutliers'),
                    'buyThreshold': stats.get('buyThreshold'),
                    'sellThreshold': stats.get('sellThreshold'),
                    'buyAvgFivePercent': stats.get('buyAvgFivePercent'),
                    'sellAvgFivePercent': stats.get('sellAvgFivePercent')
                }
        
        # Run tasks for all moon goo items
        tasks = [process_item(type_id, item_name) for type_id, item_name in moon_goo_items.items()]
        await asyncio.gather(*tasks)
        
        # Save market data to JSON file
        with open('market_data.json', 'w') as file:
            json.dump(market_data, file, indent=4)
        
        logging.info("Market data calculation complete and saved to 'market_data.json'.")
    
    except Exception as e:
        logging.error(f"Exception occurred during market data calculation: {str(e)}")

# Command to calculate moon goo amounts and display in Excel-like format
async def calculate_moon_goo_values(ctx):
    try:
        # Load moon goo assets from MongoDB or JSON
        moon_goo_data = await get_moon_goo_items(ctx.guild.id)  # Load moon goo data by server ID
        if not moon_goo_data:
            await ctx.send("No moon goo data available.")
            return

        # Load market stats from JSON
        with open('market_stats.json', 'r') as market_file:
            market_stats = json.load(market_file)

        # Initialize data structure for storing results
        result_data = []

        # Process moon goo amounts and calculate values
        for station, items in moon_goo_data.items():
            for item_name, quantity in items.items():
                # Get the item type ID (Assume you have a mapping of item_name to type_id)
                type_id = get_type_id_from_name(item_name)

                # Fetch market stats for this item
                market_info = market_stats.get(str(type_id), {})
                buy_price = market_info.get('buyAvgFivePercent', 0)
                sell_price = market_info.get('sellAvgFivePercent', 0)

                # Calculate total values
                total_buy_value = buy_price * quantity
                total_sell_value = sell_price * quantity

                # Append the data for this station and item
                result_data.append({
                    'Station': station,
                    'Item': item_name,
                    'Quantity': quantity,
                    'Buy Price (Unit)': buy_price,
                    'Sell Price (Unit)': sell_price,
                    'Total Buy Value': total_buy_value,
                    'Total Sell Value': total_sell_value
                })

        # Convert the results to a DataFrame for a tabular display (Excel-like)
        df = pd.DataFrame(result_data)

        # Print the table in an Excel-like format in chunks
        result_str = df.to_string(index=False)
        await send_message_in_chunks(ctx, result_str)

        # Save the results to a file (replacing the old one)
        df.to_csv('moon_goo_value_report.csv', index=False)
        await ctx.send("Moon goo value report has been generated and saved to 'moon_goo_value_report.csv'.")

    except Exception as e:
        logging.error(f"Error calculating moon goo values: {str(e)}")
        await ctx.send("An error occurred while calculating moon goo values.")

# Utility function to send large messages in chunks (Discord message limit workaround)
async def send_message_in_chunks(ctx, message, chunk_size=2000):
    for i in range(0, len(message), chunk_size):
        await ctx.send(message[i:i + chunk_size])

# Utility to get item type_id from the name (This assumes you have some mapping function)
def get_type_id_from_name(item_name):
    moon_goo_items = get_moon_goo_items()  # Load moon goo item ID mapping
    return moon_goo_items.get(item_name)