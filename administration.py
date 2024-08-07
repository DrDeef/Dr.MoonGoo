
import aiohttp
import logging
import config
from urllib.parse import quote
from config import load_tokens, save_tokens
import base64
from datetime import datetime, timedelta


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



async def get_access_token():
    tokens = load_tokens()
    logging.info(f"Tokens loaded in get_access_token: {tokens}")

    if tokens and 'access_token' in tokens and not is_token_expired():
        logging.info("Returning existing access token.")
        return tokens['access_token']
    
    if tokens and 'refresh_token' in tokens:
        logging.info("Attempting to refresh access token.")
        new_tokens = await refresh_token()
        if new_tokens:
            save_tokens(
                new_tokens.get('access_token', tokens.get('access_token')),
                new_tokens.get('refresh_token', tokens.get('refresh_token')),
                new_tokens.get('expires_in', 3600)
            )
            logging.info(f"New tokens saved: {new_tokens}")
            return new_tokens.get('access_token')
    
    logging.error("No access token available and refresh token not found or refresh failed.")
    return None


def is_token_expired():
    tokens = load_tokens()
    if not tokens or 'created_at' not in tokens or 'expires_in' not in tokens:
        return True
    
    created_at = datetime.fromisoformat(tokens['created_at'])
    expires_in = tokens['expires_in']
    expiration_time = created_at + timedelta(seconds=expires_in)
    
    return datetime.utcnow() > expiration_time

async def refresh_token():
    tokens = config.load_tokens()
    
    if not tokens or 'refresh_token' not in tokens:
        logging.error("No refresh token found. Cannot refresh access token.")
        return {}

    refresh_token = tokens['refresh_token']
    logging.info(f"Using refresh token: {refresh_token}")

    refresh_token_encoded = quote(refresh_token)
    data = f'grant_type=refresh_token&refresh_token={refresh_token_encoded}'

    client_id = config.get_config('eve_online_client_id', '')
    client_secret = config.get_config('eve_online_secret_key', '')
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
                
                logging.info(f"Refresh response data: {response_data}")

                if 'access_token' in response_data:
                    logging.info(f"New access token: {response_data['access_token']}")
                    return response_data
                else:
                    logging.error(f'Failed to refresh access token: {response_data.get("error_description", "No error description provided.")}')
                    return {}
        except aiohttp.ClientError as e:
            logging.error(f'Exception occurred while refreshing access token: {str(e)}')
            return {}