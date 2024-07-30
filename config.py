import yaml
import json

# Load configuration from config.yaml
def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)

# Save configuration to config.yaml
def save_config(config):
    with open("config.yaml", "w") as config_file:
        yaml.dump(config, config_file)

# Load and save tokens
def load_tokens():
    global tokens
    try:
        with open('tokens.json', 'r') as f:
            tokens = json.load(f)
    except FileNotFoundError:
        tokens = {}

def save_tokens():
    with open('tokens.json', 'w') as f:
        json.dump(tokens, f)

# Load the initial configuration and tokens
config = load_config()
load_tokens()

DISCORD_BOT_TOKEN = config.get('discord_bot_token')
CLIENT_ID = config.get('eve_online_client_id')
CLIENT_SECRET = config.get('eve_online_secret_key')
CALLBACK_URL = config.get('eve_online_callback_url')
CORPORATION_ID = config.get('corporation_id')
ADMIN_CHANNELS = [str(chan) for chan in config.get('admin_channels', [])]
ALERT_CHANNEL_ID = config.get('alert_channel_id')
ALERT_THRESHOLD = config.get('alert_threshold', 500)
MOON_DRILL_IDS = config.get('metenox_moon_drill_ids', [])

tokens = tokens  # Ensure tokens are accessible
states = {}  # Initialize empty states dictionary

# Debug prints
print(f"CLIENT_ID: {CLIENT_ID}")
print(f"CLIENT_SECRET: {CLIENT_SECRET}")
