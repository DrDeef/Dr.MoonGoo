import yaml
import json
import os
from datetime import datetime
import logging

# Define global variables to be loaded from the config.yaml
config = {}
tokens = {}
states = {}
config_file = 'config.yaml'
tokens_file = 'tokens.json'
server_structures_file = 'server_structures.json'

def load_config():
    global config
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file) or {}
    except FileNotFoundError:
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
        }

def save_config(config_data):
    global config
    try:
        with open(config_file, 'w') as file:
            yaml.safe_dump(config_data, file)
    except IOError as e:
        logging.error(f"Error saving configuration: {e}")


def load_tokens():
    try:
        with open(tokens_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return an empty dictionary if tokens cannot be loaded

def save_tokens(server_id, access_token, refresh_token, expires_in):
    try:
        # Load existing tokens
        with open('tokens.json', 'r') as file:
            file_content = file.read().strip()
            if file_content:
                all_tokens = json.loads(file_content)
            else:
                all_tokens = {}
    except FileNotFoundError:
        all_tokens = {}
    except json.JSONDecodeError:
        all_tokens = {}

    # Ensure server_id is a string to use as a dictionary key
    server_id_str = str(server_id)

    # Update tokens for the specific server_id
    all_tokens[server_id_str] = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': expires_in,
        'created_at': datetime.utcnow().isoformat()
    }

    # Save updated tokens
    with open('tokens.json', 'w') as file:
        json.dump(all_tokens, file, indent=4)

def get_server_tokens(server_id):
    # Make sure server_id is a string
    server_id_str = str(server_id)
    # Load tokens from file or database
    tokens = load_tokens()  # Ensure this function loads the tokens correctly
    return tokens.get(server_id_str, {})

def add_server_id(server_id):
    tokens = load_tokens()
    if server_id not in tokens:
        tokens[server_id] = {}
    with open(tokens_file, 'w') as file:
        json.dump(tokens, file, indent=4)


def get_config(key, default=None):
    return config.get(key, default)

def set_config(key, value, server_id=None):
    global config

    if server_id:
        if 'servers' not in config:
            config['servers'] = {}

        if server_id not in config['servers']:
            config['servers'][server_id] = {}

        config['servers'][server_id][key] = value
    else:
        config[key] = value

    save_config(config)



def load_server_structures():
    if not os.path.exists(server_structures_file):
        return {}
    with open(server_structures_file, 'r') as file:
        return json.load(file)
    

def save_server_structures(data):
    with open(server_structures_file, 'w') as file:
        json.dump(data, file, indent=4)
   



# Load configurations and tokens when the module is imported
load_config()
load_tokens()
