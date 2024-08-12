import json
from datetime import datetime, timedelta

def load_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {file_path}: {e}")
        return {}

server_structures = load_json('server_structures.json')
metenox_goo = load_json('metenox_goo.json')


def get_moon_drill_count():
    moon_drill_count = 0
    for server_id, data in server_structures.items():
        moon_drill_count += len(data.get("metenox_moon_drill_ids", []))
    return moon_drill_count
