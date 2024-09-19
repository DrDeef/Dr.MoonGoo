import aiohttp
import logging
import config
from config import get_config, load_token, save_token
from urllib.parse import quote
import base64
from datetime import datetime, timedelta, timezone
import json
import os
import requests

logging.basicConfig(level=logging.INFO)

# Access config values using the get_config function
ADMIN_CHANNELS = get_config('admin_channels', [])
ADMIN_ROLE = get_config('admin_role', 'Admin')
CLIENT_ID = get_config('eve_online_client_id', '')
CLIENT_SECRET = get_config('eve_online_secret_key', '')
CALLBACK_URL = get_config('eve_online_callback_url', '')
CORPORATION_ID = get_config('corporation_id', '')

def is_token_valid(created_at, expires_in):
    try:
        token_creation_time = datetime.fromisoformat(created_at[:-1])  # Removing 'Z' before parsing
        expiration_time = token_creation_time + timedelta(seconds=expires_in)
        return datetime.utcnow() < expiration_time
    except Exception as e:
        logging.error(f"Error checking token validity: {e}")
        return False

def is_token_expired(created_at, expires_in):
    # Convert created_at to an aware datetime object
    created_at = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
    
    # Calculate the expiration time
    expiration_time = created_at + timedelta(seconds=expires_in)
    
    # Get the current UTC time as an aware datetime object
    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    
    # Compare the current time with the expiration time
    return current_time > expiration_time

def get_access_token(server_id, corporation_id):
    """Retrieve access token for a specific server and corporation."""
    token_data = load_token(server_id, corporation_id)
    
    if not token_data:
        logging.error(f"No token data found for server {server_id}, corporation {corporation_id}.")
        return None
    
    # Ensure token is not expired
    if is_token_expired(token_data['created_at'], token_data['expires_in']):
        logging.info(f"Token expired for server {server_id}, corporation {corporation_id}.")
        # Handle token refresh logic here
        # e.g., call refresh_token(server_id, corporation_id)
        return None
    
    return token_data['access_token']

async def refresh_token(server_id, corporation_id):
    """Refresh the access token for a specific server and corporation."""
    token_data = config.load_token(server_id, corporation_id)
    if not token_data:
        logging.error(f"No token data found for server ID {server_id}, corporation ID {corporation_id}.")
        return {}

    refresh_token = token_data.get('refresh_token')
    if not refresh_token:
        logging.error(f"No refresh token available for server ID {server_id}, corporation ID {corporation_id}.")
        return {}

    if not isinstance(refresh_token, str):
        logging.debug(f"Refresh token for server ID {server_id} and corporation ID {corporation_id} is not a string. Converting to string.")
        refresh_token = str(refresh_token)

    logging.debug(f"Refreshing token for server ID {server_id}, corporation ID {corporation_id}. Using refresh token: {refresh_token}")

    refresh_token_encoded = quote(refresh_token)
    data = f'grant_type=refresh_token&refresh_token={refresh_token_encoded}'

    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        'Authorization': f'Basic {b64_auth_str}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'login.eveonline.com'
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post('https://login.eveonline.com/v2/oauth/token', data=data, headers=headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    logging.error(f"Failed to refresh access token for server ID {server_id}, corporation ID {corporation_id}. Status: {response.status}, Response: {response_text}. Refresh token used: {refresh_token}")
                    return {}

                response_data = await response.json()

                access_token = response_data.get('access_token')
                if not access_token:
                    logging.error(f"Failed to refresh access token for server ID {server_id}, corporation ID {corporation_id}. No access token in response. Refresh token used: {refresh_token}")
                    return {}

                # Preserve existing character_id if not provided in response
                existing_character_id = token_data.get('character_id', '')

                new_refresh_token = response_data.get('refresh_token', refresh_token)  # Use existing refresh token if new one is not provided
                expires_in = response_data.get('expires_in', 3600)  # Default to 3600 if not provided
                created_at = datetime.utcnow().isoformat() + "Z"  # Set the current UTC time for 'created_at'
                character_id = response_data.get('character_id', existing_character_id)  # Preserve existing character_id

                logging.debug(f"New access token for server ID {server_id}, corporation ID {corporation_id}")

                # Save the tokens with the updated values
                config.save_token(server_id, corporation_id, access_token, new_refresh_token, expires_in, created_at, character_id)
                return response_data
        except aiohttp.ClientError as e:
            logging.error(f"Exception occurred while refreshing access token for server ID {server_id}, corporation ID {corporation_id}: {str(e)}. Refresh token used: {refresh_token}")
            return {}

async def refresh_all_tokens():
    """Refresh all tokens for all servers and corporations."""
    try:
        all_tokens = config.load_all_tokens()

        if not all_tokens:
            logging.error("No tokens found.")
            return

        logging.info("Starting token refresh for all servers.")

        for server_id, corporations in all_tokens.items():
            for corporation_id in corporations.keys():
                try:
                    # Refresh token for each corporation in each server
                    response = await refresh_token(server_id, corporation_id)

                    if response:
                        logging.debug(f"Successfully refreshed access token for server ID {server_id}, corporation ID {corporation_id}.")
                    else:
                        logging.error(f"Failed to refresh access token for server ID {server_id}, corporation ID {corporation_id}.")

                except Exception as e:
                    logging.error(f"Exception occurred while refreshing token for server ID {server_id}, corporation ID {corporation_id}: {str(e)}")

    except Exception as e:
        logging.error(f"refresh_all_tokens failed with error: {str(e)}")

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
        logging.error(f"Error retrieving character info: {e}")
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

async def fetch_corporation_name(corporation_id):
    """Fetch the corporation name from EVE ESI API."""
    url = f"https://esi.evetech.net/latest/corporations/{corporation_id}/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('name', f"Corporation {corporation_id}")
            else:
                logging.error(f"Failed to fetch corporation name for ID {corporation_id}. Status code: {response.status}")
                return f"Corporation {corporation_id}"
            
def get_latest_token(server_id):
    tokens = load_token(server_id, None)  # Assuming `None` if corporation_id is not used

    if server_id in tokens:
        # Sort tokens by creation time, most recent first
        sorted_tokens = sorted(tokens.values(), key=lambda x: x['created_at'], reverse=True)
        return sorted_tokens[0]  # Return the latest token

    logging.error(f"No tokens found for server {server_id}.")
    return None

def extract_corporation_id_from_filename(server_id):
    """Extract the corporation ID from the filename pattern serverid_corporationid.json."""
    files = [f for f in os.listdir() if f.startswith(f"{server_id}_") and f.endswith("_token.json")]
    if not files:
        logging.error(f"No token file found for server {server_id}.")
        return None
    
    # Extract corporation_id from the first matching file
    filename = files[0]
    try:
        parts = filename.split('_')
        if len(parts) >= 2:
            corporation_id = parts[1]
            return corporation_id
    except IndexError:
        logging.error(f"Error extracting corporation ID from filename {filename}.")
    
    return None