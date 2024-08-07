
import requests
import logging
import config
from config import load_tokens, save_tokens
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
    
    # Check if there's a valid token already
    if tokens and 'access_token' in tokens and not is_token_expired():
        return tokens['access_token']
    
    # Refresh the token if expired or missing
    if tokens and 'refresh_token' in tokens:
        new_tokens = await refresh_access_token()
        # Save the new tokens
        save_tokens(new_tokens['access_token'], new_tokens.get('refresh_token', tokens.get('refresh_token')), new_tokens.get('expires_in', 3600))
        return new_tokens['access_token']
    
    # Handle the case where no refresh token is available
    return None

def is_token_expired():
    """Check if the stored token is expired."""
    tokens = load_tokens()
    if not tokens:
        # No tokens found
        return True

    created_at_str = tokens.get('created_at')
    expires_in = tokens.get('expires_in')

    if not created_at_str or expires_in is None:
        # Missing token details
        return True

    created_at = datetime.fromisoformat(created_at_str)
    expiration_time = created_at + timedelta(seconds=expires_in)

    # Compare the current time with the expiration time
    return datetime.utcnow() > expiration_time

async def refresh_access_token():
    refresh_url = 'https://login.eveonline.com/v2/oauth/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens.get('refresh_token', ''),
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    try:
        response = requests.post(refresh_url, headers=headers, data=data)
        response.raise_for_status()
        response_data = response.json()

        if 'access_token' in response_data:
            access_token = response_data['access_token']
            refresh_token = response_data.get('refresh_token', tokens.get('refresh_token', ''))
            expires_in = response_data.get('expires_in', 3600)  # Default to 1 hour if not provided

            save_tokens(access_token, refresh_token, expires_in)
            return access_token
        else:
            logging.error(f"Failed to refresh access token: {response_data.get('error_description', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error while refreshing access token: {e}")
        return None

