# tasks.py
import asyncio
import logging
import requests
import base64
import config
import commands
import aiohttp
from commands import handle_update_moondrills
from discord.ext import tasks
from urllib.parse import quote

# Define the refresh_token function
async def refresh_token():
    if not config.tokens.get('refresh_token'):
        logging.error("No refresh token found. Cannot refresh access token.")
        return

    refresh_token = config.tokens['refresh_token']
    refresh_token_encoded = quote(refresh_token)
    data = f'grant_type=refresh_token&refresh_token={refresh_token_encoded}'

    client_id = config.config.get('eve_online_client_id', '')
    client_secret = config.config.get('eve_online_secret_key', '')
    auth_str = f"{client_id}:{client_secret}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        'Authorization': f'Basic {b64_auth_str}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'login.eveonline.com'
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post('https://login.eveonline.com/v2/oauth/token', data=data, headers=headers) as response:
                response.raise_for_status()
                response_data = await response.json()

                logging.debug(f"Response data: {response_data}")

                if 'access_token' in response_data:
                    config.tokens['access_token'] = response_data['access_token']
                    config.tokens['refresh_token'] = response_data.get('refresh_token', config.tokens['refresh_token'])

                    access_token = response_data['access_token']
                    refresh_token = response_data.get('refresh_token', config.tokens['refresh_token'])
                    expires_in = response_data['expires_in']

                    config.save_tokens(access_token, refresh_token, expires_in)
                    logging.info('Access token refreshed successfully.')
                else:
                    error_description = response_data.get('error_description', 'No error description provided.')
                    logging.error(f'Failed to refresh access token: {error_description}')

        except aiohttp.ClientError as e:
            logging.error(f'Exception occurred while refreshing access token: {str(e)}')
        except ValueError:
            logging.error('Error decoding the response JSON.')

# Periodic task to refresh token every 5 minutes
@tasks.loop(minutes=5)
async def refresh_token_task():
    await refresh_token()


# Periodic task to update moon drills every 5 minutes
@tasks.loop(minutes=30)
async def update_moondrills_task(ctx):
    await handle_update_moondrills(ctx)


config.load_config()
config.load_tokens()