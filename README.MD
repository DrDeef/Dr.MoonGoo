# Dr.MoonGoo is Ready to Roll

A Discord bot that integrates with the EVE Online API to monitor moon drilling structures.

## Features

- **OAuth2 Authentication**: Securely authenticate with the EVE Online API.
- **Structure Monitoring**: Track and check conditions of EVE Online structures.
- **Gas Check**: Monitor gas levels in moon drilling structures and receive alerts if gas is low.
- **Administrative Commands**: Manage alert channels and update moon drill IDs with ease.

## Setup

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

4. **configure the bot**

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

## Commands

- **!authenticate**: Authenticate the Bot against the EvE Online ESI API
  - You need e.g. Director Permissions ingame to check the structural assets
- **!setup**: Will Setup the Alerting Channel
- **!setadmin**: Will Setup the Administrative Channel
- **!updatemoondrills**: Update your Moondrill Structures
- **!debug**: Debug Information about your ESI Token
- **!checkgas**: Prints the amount of Magmatic Gas and Fuel Blocks within the Moondrill with a timer
  
## Example Bot Response
<br>
<img src="images/bot-response.png" alt="drawing" width="400"/>


## Presented by Regnum Astera

[![Regnum Astera](https://e.dotlan.net/images/Alliance/99012040_128.png)](https://discord.gg/uPkd893FZV)

If you’re looking for a strong and dedicated EVE Online alliance to join, consider **Regnum Astera**!
Join us and be part of something epic!

For more information reach out to us directly on [Discord](https://discord.gg/uPkd893FZV)

Happy drilling! 🚀

## Donate

If you like the Bot, please consider donating ISK ingame to [PoorInternetGuy](https://evewho.com/character/2122580011)