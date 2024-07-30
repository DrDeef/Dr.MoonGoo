import yaml
import json
import os

# Global variables for configuration and tokens
tokens = {}
states = {}

def load_config():
    config_path = "config.yaml"
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
    
    with open(config_path, "r") as config_file:
        return yaml.safe_load(config_file)

def save_config(config):
    config['admin_channels'] = [str(chan) for chan in config.get('admin_channels', [])]
    
    with open("config.yaml", "w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)

def load_tokens():
    global tokens
    tokens_path = 'tokens.json'
    if os.path.isfile(tokens_path):
        with open(tokens_path, 'r') as f:
            tokens = json.load(f)
    else:
        tokens = {}

def save_tokens():
    with open('tokens.json', 'w') as f:
        json.dump(tokens, f, indent=4)

# Load the initial configuration and tokens
try:
    config = load_config()
    load_tokens()
except Exception as e:
    print(f"Error loading configuration or tokens: {e}")
    raise

# Extract configuration settings
DISCORD_BOT_TOKEN = config.get('discord_bot_token')
CLIENT_ID = config.get('eve_online_client_id')
CLIENT_SECRET = config.get('eve_online_secret_key')
CALLBACK_URL = config.get('eve_online_callback_url')
CORPORATION_ID = config.get('corporation_id')
ADMIN_CHANNELS = [str(chan) for chan in config.get('admin_channels', [])]
ALERT_CHANNEL_ID = config.get('alert_channel_id')
ALERT_THRESHOLD = config.get('alert_threshold', 500)
MOON_DRILL_IDS = config.get('metenox_moon_drill_ids', [])

print(f"CLIENT_ID: {CLIENT_ID}")
print(f"CLIENT_SECRET: {CLIENT_SECRET}")
print(f"ADMIN_CHANNELS: {ADMIN_CHANNELS}")
