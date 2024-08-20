
import aiohttp
import logging
import config
from config import tokens,get_config, load_tokens
from urllib.parse import quote
from config import save_tokens
import base64
import json
import requests
from datetime import datetime, timedelta


logging.basicConfig(level=logging.INFO)


# Access config values using the get_config function
ADMIN_CHANNELS = config.get_config('admin_channels', [])
ADMIN_ROLE = config.get_config('admin_role', 'Admin')
CLIENT_ID = config.get_config('eve_online_client_id', '')
CLIENT_SECRET = config.get_config('eve_online_secret_key', '')
CALLBACK_URL = config.get_config('eve_online_callback_url', '')
CORPORATION_ID = config.get_config('corporation_id', '')


# Use the updated methods and variables from config.py
tokens = config.tokens
states = config.states


def is_token_valid(created_at, expires_in):
    token_creation_time = datetime.fromisoformat(created_at[:-1])  # Removing 'Z' before parsing
    expiration_time = token_creation_time + timedelta(seconds=expires_in)
    return datetime.utcnow() < expiration_time

async def get_access_token(server_id):
    tokens = config.load_tokens()
    server_tokens = tokens.get(server_id, {}).get('tokens', [])
    
    if not server_tokens:
        logging.error(f"No tokens found for server {server_id}.")
        return None
    
    # Sort tokens by creation time, most recent first
    server_tokens = sorted(server_tokens, key=lambda x: x['created_at'], reverse=True)
    latest_token = server_tokens[0]
    
    access_token = latest_token.get('access_token')
    expires_in = latest_token.get('expires_in')
    created_at = latest_token.get('created_at')

    # Check if the token is still valid
    if is_token_valid(created_at, expires_in):
        return access_token
    else:
        logging.info(f"Access token for server {server_id} is expired, attempting to refresh.")
        # Refresh the token if expired
        new_token_data = await refresh_token(server_id)
        return new_token_data.get('access_token') if new_token_data else None




def is_token_expired(server_id):
    tokens = config.get_server_tokens(server_id)
    if not tokens or 'created_at' not in tokens or 'expires_in' not in tokens:
        return True
    
    created_at = datetime.fromisoformat(tokens['created_at'])
    expires_in = tokens['expires_in']
    expiration_time = created_at + timedelta(seconds=expires_in)
    
    return datetime.utcnow() > expiration_time

async def refresh_token(server_id):
    tokens = config.get_server_tokens(server_id)
    
    if not tokens or 'refresh_token' not in tokens:
        logging.error(f"No refresh token found for server {server_id}. Cannot refresh access token.")
        return {}

    refresh_token = tokens['refresh_token']
    ##debugenable logging.info(f"Using refresh token for server {server_id}: {refresh_token}")

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
                
                ###debug logging.info(f"Refresh response data for server {server_id}: {response_data}")

                if 'access_token' in response_data:
                    ###debug logging.info(f"New access token for server {server_id}: {response_data['access_token']}")
                    save_tokens(server_id, response_data['access_token'], response_data.get('refresh_token', refresh_token), response_data.get('expires_in', 3600))
                    return response_data
                else:
                    logging.error(f'Failed to refresh access token for server {server_id}: {response_data.get("error_description", "No error description provided.")}')
                    return {}
        except aiohttp.ClientError as e:
            logging.error(f'Exception occurred while refreshing access token for server {server_id}: {str(e)}')
            return {}


def get_character_info(access_token):
    url = 'https://esi.evetech.net/verify/'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving character info: {e}")
        return None

def get_corporation_id(character_id, access_token):
    """Retrieve the corporation ID associated with the character."""
    url = f'https://esi.evetech.net/latest/characters/{character_id}/'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        character_info = response.json()

        corporation_id = character_info.get('corporation_id')
        if corporation_id:
            logging.info(f"Corporation ID: {corporation_id}")
        else:
            logging.error("Corporation ID not found in the response.")
        
        return corporation_id

    except requests.exceptions.RequestException as e:
        logging.error(f"Error retrieving corporation ID: {e}")
        return None
    
def get_latest_token(server_id):
    tokens = load_tokens()

    if server_id in tokens and 'tokens' in tokens[server_id]:
        # Sort tokens by creation time, most recent first
        sorted_tokens = sorted(tokens[server_id]['tokens'], key=lambda x: x['created_at'], reverse=True)
        return sorted_tokens[0]  # Return the latest token

    logging.error(f"No tokens found for server {server_id}.")
    return None