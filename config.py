import yaml
import json

# Define global variables to be loaded from the config.yaml
config = {}
tokens = {}
states = {}

def load_config():
    global config
    try:
        with open('config.yaml', 'r') as file:
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
            'metenox_moon_drill_ids': []
        }

def save_config():
    with open('config.yaml', 'w') as file:
        yaml.safe_dump(config, file)

def load_tokens():
    global tokens
    try:
        with open('tokens.json', 'r') as file:
            tokens = json.load(file)
    except FileNotFoundError:
        tokens = {}

def save_tokens():
    with open('tokens.json', 'w') as file:
        json.dump(tokens, file)

def get_config(key, default=None):
    return config.get(key, default)

def set_config(key, value):
    config[key] = value
    save_config()

# Load configurations when the module is imported
load_config()
load_tokens()
