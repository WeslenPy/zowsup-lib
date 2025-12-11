# zowsup

zowsup is a python WhatsApp-protocol project based on [yowsup](https://github.com/tgalal/yowsup/).

Since the original yowsup project has not been maintained for a long time, we forked yowsup and some associated projects (axolotl, consonance) and integrated them into an All-In-One project, keeping it updated with the latest version of WhatsApp.

```
- ZOWSUP VERSION : 0.6.5

- UPDATE TIME : 2025-11-16

- WHATSAPP VERSION :
    2.25.29.75 (Android)
    2.25.32.75 (SMB Android)
    2.25.32.77 (iOS)
    2.25.32.77 (SMB iOS)

```

## Discussion Groups
 * telegram:  [zowsup](https://t.me/+au1dTQz7jyU0YjU5)

## What's New 0.6.5
 * new interactive mode

## What's New 0.6.0
 * new commands `mdlink` and `mdremove`
 * linkcode for companion device registration

## What's New 0.5.0
 * Latest version (6.3) of noise-protocol and token-dictionary
 * Multi-Environment support (android,smb_android,ios,smb_ios)
 * Multi-Device protocol support
 * Display a QR to Login as a companion device 
 * 6-parts account support (import / export )
 * Proxy support
 * Threading command architecture 
 * Bubbling up all the config variables to the top layer ( app and conf folder)
 * Mass of WA-protocol updates
 
## Subsequent update promise
 * Critical protocol update
 * Version update with latest WhatsApp 
 

## Quick start for the project

 * Installation 

```
 pip install -r requirements.txt

```
 * Basic configuration

```
copy ./conf/config.conf.example to ./conf/config.conf and modify variables in config.conf according to your system

ACCOUNT_PATH=/data/account/               #location you store the account data
DOWNLOAD_PATH=/data/tmp/                  #download path
UPLOAD_PATH=/data/tmp/                    #upload path
LOG_PATH=/data/log/                       #log path
DEFAULT_ENV=android                       #default environment

```

 * Import account from 6-parts-account-data

```
 python script/import6.py [6-parts-account-data] --env android             # env : android/smb_android/ios/smb_ios is available

```

 * Export accounts to 6-parts-account-data
 
```
 python script/export6.py [account-number]

```

 * Run

```
 python script/main.py [account-number] --env android                        # env : android/smb_android/ios/smb_ios is available

```

then you can enter interactive mode with 'CMD > ' prompt


* Register as a companion device

```
 [QRCODE]
 python script/regwithscan.py 

 [LINKCODE]
 python script/regwithlinkcode.py [account-number]

```

* Basic commands

```
python script/main.py [account-number] [command] [commandParams] #in shell console

or

[command] [commandParams]   #in the interactive mode 


[command]                     |   [description]
----------------------------------------------------------------------------
account.getavatar             | get account avatar
account.getemail              | get account email
account.init                  | initialize the account (for the 1st login)
account.set2fa                | set account 2fa
account.setavatar             | set account avatar
account.setemail              | set account email
account.setname               | set account name
account.verifyemail           | request email verification
account.verifyemailcode       | verify email code
contact.getavatar             | get account avatar
contact.sync                  | sync contacts
contact.trust                 | trust contact
group.add                     | add member(s) to group
group.approve                 | approve participants to join the group
group.create                  | create a group
group.demote                  | demote group member(s) from admin
group.getinvite               | get the invite code of group
group.info                    | show group information
group.join                    | join group with an invite code
group.leave                   | leave group
group.list                    | list all groups
group.promote                 | promote group member(s) to admin
group.remove                  | remove a member from group
group.seticon                 | set icon for group
md.link                       | link to companion device with qrcode-str
md.remove                     | remove companion device(s)
msg.edit                      | edit message
msg.revoke                    | revoke message
msg.send                      | send message
msg.sendmedia                 | send media message
----------------------------------------------------------------------------
```


 * Proxy 

```
 python script/main.py [account-number] --proxy "host:port:username:password"  

 dynamic [location] and [session_id] replacement in the proxy string is supported 

```


## Technologies

- Python 3
- WhatsApp multi-device protocol (Web/Mobile compatible)
- Signal / Axolotl (Double Ratchet, pre-keys) – `axolotl/`
- Noise protocol / TLS-like – `consonance/`, `dissononce`
- `pycryptodome` (`Crypto.*`) for AES/HMAC/HKDF
- `protobuf` – messages defined in `proto/*.proto`
- `requests`, `websocket-client`, `PySocks`, `gevent`
- `ffmpeg`, `pillow`, `qrcode`, `apkutils`


## Architecture Overview

- `yowsup/`: WhatsApp protocol stack (layers, entities, stacks)
- `axolotl/`: Signal/Axolotl implementation
- `consonance/`: Noise handshake and transport
- `app/`: application and high-level API (bot, envs, `ZowsupClient`)
- `common/`: utilities and CLI base (`consolemain.py`, `utils.py`)
- `conf/`: configuration (`config.conf`, `SysVar`, `GlobalVar`)
- `script/`: CLI entry points (`main.py`, `import6.py`, `export6.py`, `regwithscan.py`, `regwithlinkcode.py`, `reset2fa.py`)


## Configuration details

Configuration file (`conf/config.conf` – copy from `conf/config.conf.example`):

```ini
[SysVar]
ACCOUNT_PATH=/data/account/   # where account data (profiles, axolotl DB) is stored
DOWNLOAD_PATH=/data/tmp/      # media download path
UPLOAD_PATH=/data/tmp/        # media upload path
LOG_PATH=/data/log/           # log files path
DEFAULT_ENV=android           # default environment: android / smb_android / ios / smb_ios
```

- Low-level loader: `SysVar.loadConfig(path=None)`
  - Uses `path` if given, else env var `ZOWSUP_CONFIG`, else default `conf/config.conf`.
- Configuração agora é feita via `Settings` (pydantic BaseSettings) em `settings/conf.py`, carregando `.env`/variáveis `ZOWSUP_*` e aplicando defaults tipados.


## High-level Python API (`ZowsupClient`)

`app/api.py` exposes a high-level client to interact with zowsup programmatically.

### Basic usage

```python
from app.api import ZowsupClient

client = ZowsupClient(
    account_id="5511999999999",  # phone number / account ID
    # config_path="C:/my/conf/config.conf",  # optional
    # env="android",                        # optional, defaults to DEFAULT_ENV
    # proxy="host:port:user:pass",          # optional, DIRECT if omitted
)

client.connect()
client.send_text("5511888888888", "Hello from ZowsupClient!")
client.disconnect()
```

### Sending text messages

```python
from app.api import ZowsupClient, ZowsupError

client = ZowsupClient("5511999999999")

try:
    # Fire-and-forget (CLI-like behaviour)
    client.send_text("5511888888888", "Hello!")

    # Returning the WhatsApp message ID
    resp = client.send_text(
        "5511888888888",
        "Message with ID",
        wait_for_id=True,
        wait_msg_id_timeout=30,
    )
    print("Message ID:", resp.data["message_id"])
except ZowsupError as e:
    print("Error:", e.code, str(e))
finally:
    client.disconnect()
```

### Sending media

```python
client = ZowsupClient("5511999999999")

# Local image
client.send_media(
    "5511888888888",
    "image",
    "C:/images/photo.jpg",
    caption="Test image",
)

# Video from URL
client.send_media(
    "5511888888888",
    "video",
    "https://example.com/video.mp4",
    caption="Watch this",
)
```

### Groups and contacts

```python
# Create group
resp = client.create_group(
    subject="Test Group",
    participants="5511888888888@s.whatsapp.net,5511777777777@s.whatsapp.net",
)
print("Group info:", resp.data)

# List groups
resp = client.list_groups()
print("Groups:", resp.data)

# Sync contacts
resp = client.sync_contacts("5511888888888,5511777777777")
print("Sync result:", resp.data)
```

### Importing a new account from 6-parts data

Besides the CLI `script/import6.py`, you can import a new account programmatically using `ZowsupClient.import_account_from_six_parts`:

```python
from app.api import ZowsupClient

six_parts = "5511999999999,PK1,SK1,PK2,SK2,SIXTH"  # string generated by export6.py

account_id = ZowsupClient.import_account_from_six_parts(
    six_parts_data=six_parts,
    env="android",                # or ios / smb_android / smb_ios
    # config_path="C:/my/conf/config.conf",  # optional
)

print("Imported account:", account_id)

client = ZowsupClient(account_id)
client.send_text("5511888888888", "New account imported successfully!")
client.disconnect()
```


## Error handling

- The high-level API raises a single exception type: `ZowsupError(code, message)`.
- Low-level protocol errors and command failures are mapped into this exception for easier handling.

