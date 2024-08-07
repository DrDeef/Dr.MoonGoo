import yaml
import json
from datetime import datetime 

# Define global variables to be loaded from the config.yaml
config = {}
tokens = {}
states = {}
config_file = 'config.yaml'

def load_config():
    global config
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file) or {}
    except FileNotFoundError:
        # Default configuration if file does not exist
        config = {
            'admin_channels': [],
            'alert_channel_id': None,
            'alert_threshold': 500,
            'corporation_id': '',
            'discord_bot_token': '',
            'eve_online_callback_url': '',
            'eve_online_client_id': '',
            'eve_online_secret_key': '',
            'admin_role': 'Admin',
            'metenox_moon_drill_ids': []
        }

def save_config():
    with open(config_file, 'w') as file:
        yaml.safe_dump(config, file)

def load_tokens():
    try:
        with open('tokens.json', 'r') as file:
            tokens = json.load(file)
            return tokens
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return an empty dictionary if tokens cannot be loaded



def save_tokens(access_token, refresh_token, expires_in):
    global tokens
    tokens = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'created_at': datetime.utcnow().isoformat(),
        'expires_in': expires_in
    }
    with open('tokens.json', 'w') as file:
        json.dump(tokens, file, indent=4)  # Added indent for better readability


def get_config(key, default=None):
    return config.get(key, default)

def set_config(key, value):
    config[key] = value
    save_config()

# Load configurations and tokens when the module is imported
load_config()
load_tokens()