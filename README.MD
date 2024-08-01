![Version](https://img.shields.io/badge/version-0.0.1-red) ![Docker Pulls](https://img.shields.io/docker/pulls/drdeef/drmoongoo) ![GitHub commit activity](https://img.shields.io/github/commit-activity/m/drdeef/Dr.MoonGoo?style=flat&color=green)



# If you like Moons and Goo, i have a solution for you!
<img src="images/drMoonGoo.jpg" alt="DrMoonGoo" width="250"/>


## What is Dr. MoonGoo?
> A Discord bot that integrates with the EVE Online API to monitor moon drilling structures.

## Features

- **OAuth2 Authentication**: Securely authenticate with the EVE Online API.
- **Structure Monitoring**: Track and check conditions of EVE Online structures.
- **Goo-Alert**: Set a channel to check for Gas and Fuel levels every hour and alerts you if it falls short.
  - An alert will be send 48 Hours and 24 Hours in regards of the depletion of the Gas / Fuel
- **Gas Check**: Monitor gas levels in moon drilling structures and receive alerts if gas is low.
- **Goo Check**: Print out the amount of materials the drill has in its 'assets'.
- **Administrative Commands**: Manage alert channels and update moon drill IDs with ease.

## Setup

### Dockerfile

There are two ways, you can either use one of the following images:
https://hub.docker.com/r/drdeef/drmoongoo/tags

Or you build your Dockerimage yourself with the `Dockerfile`

Run the Container with:

```bash
docker run -d -p 5005:5005 -v /path/to/local/config.yaml:/usr/src/app/config.yaml drdeef/drmoongoo:0.0.1
```

### Without Docker

1. **Clone the Repository:**

```sh
   git clone https://github.com/DrDeef/Dr.MoonGoo.git
   cd Dr.MoonGoo
```

2. **Create and Activate Virtual Environment**

```bash
   python3 -m venv venv
   source venv/bin/activate
```

3. **Install Dependencies:**

```bash
   pip install -r requirements.txt
```

4. **Eve Online Scopes**

You need to generate your API ID/KEY pair here: https://developers.eveonline.com/applications
Give it the following scopes:

```bash
- esi-search.search_structures.v1
- esi-universe.read_structures.v1
- esi-assets.read_assets.v1
- esi-corporations.read_structures.v1
- esi-assets.read_corporation_assets.v1
- publicData
```

5. **Discord application**

Register your application here: https://discord.com/developers/applications
Navigate to Applications > Bot

Give it following Parameters:
```bash
Message Content Intent.

Permission Integer
- 517544037440
```

6. **configure the bot**

Update the config.yaml to your needs:

```bash
admin_channels: []
alert_channel_id: null
alert_threshold: 500
corporation_id: 'CORP-ID'
discord_bot_token: YOUR_DISCORD_BOT_TOKEN
eve_online_callback_url: http://localhost:5005/oauth-callback
eve_online_client_id: YOUR_EVE_ONLINE_CLIENT_ID
eve_online_secret_key: YOUR_EVE_ONLINE_SECRET_KEY
metenox_moon_drill_ids: []
```

7. **First Startup Sequence**

- !authenticate: NEEDED! Authenticate against the EvE ESI via SSO
- !getMeGoo: Will run the base setup.
  - Will update your Moondrill structures, Gas & Fuel Levels, and the Goo Assets.
- !updatemoondrills: Update your Moondrill structures
- !gooalert: Set the current channel to be your alert channel

## Magmatic Gas & Fuelblock Calculation

Calculation is based on ingame values

- Magmatic Gas: 1 Hour = 55 Units
- Fuel Blocks: 1 Hour = 5 BLocks

## Commands

- **!authenticate**: Authenticate the bot against the EvE Online ESI API
  - You need e.g. Director permissions ingame to check the structural assets
- **!getMeGoo**: Will Setup basic parameters
- **!setadmin**: Will setup the administrative channel
- **!updatemoondrills**: Update your Moondrill Structures
- **!debug**: Debug information about your ESI-token
- **!checkGoo**: Print out every Asset within your Metenox Moon Drills.
- **!checkGas**: Prints the amount of Magmatic Gas and Fuel Blocks within the Moondrill with a timer
- **!gooalert**: Set the current channel as alerting channel and activate the scheduler.

## Example Bot Response

> !checkGas

<img src="images/bot-response.png" alt="Bot Response" width="400"/>

> !checkGoo

<img src="images/moonmaterials.png" alt="Bot Response" width="400"/>

## Example Bot Alert:

**Structure Name**: Magmatic Gas is running **low!**<br>
Magmatic Gas: ***440*** <br>
Gas runs out in: **0 Days 8 Hours**

## Presented by Regnum Astera

[![Regnum Astera](https://e.dotlan.net/images/Alliance/99012040_128.png)](https://discord.gg/uPkd893FZV)

If you’re looking for a strong and dedicated EVE Online alliance to join, consider **Regnum Astera**!
Join us and be part of something epic!

For more information reach out to us directly on [Discord](https://discord.gg/uPkd893FZV)

Happy drilling! 🚀

## Donate

If you like the Bot, please consider donating ISK ingame to [PoorInternetGuy](https://evewho.com/character/2122580011)
