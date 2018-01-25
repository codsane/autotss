# autotss
Automatically save shsh2 blobs for signed iOS firmwares using [tsschecker](https://github.com/tihmstar/tsschecker) and the [IPSW.me API](https://ipsw.me/api/ios/docs/2.1/Firmware)

## Motivation
>tsschecker is not only meant to be used to check signing status, but also to explore Apple's tss servers. By using all of its customization possibilities, __you might discover a combination of devices and iOS versions that is now getting signed but wasn't getting signed before.__ -[tihmstar (author of tsschecker)](https://github.com/tihmstar/tsschecker/blob/master/README.md#features)

[@leftyfl1p](https://github.com/leftyfl1p) and I were curious to see if Apple ever accidentally signs firmwares that should no longer be signed ([they do](https://www.reddit.com/r/jailbreak/comments/7pmbwu/meta_apple_signing_fck_up_mega_thread/?utm_content=title&utm_medium=browse&utm_source=reddit&utm_name=jailbreak)). While tsschecker is great for this, a tool to automate the process did not yet exist.

## Usage
1. Place your device info in devices.ini
      - [Find your device identifier](https://ipsw.me/device-finder)
      - [Find your device ECID](https://www.theiphonewiki.com/wiki/ECID#Getting_the_ECID) (both hex and dec are accepted)
      - Determine if your iOS device requires a board config. iOS devices with multiple available board configs will require you to manually specify a board config. Check [this list](https://www.theiphonewiki.com/wiki/Models) to see if your device is applicable.
      - Put this information in devices.ini in the appropriate format (see below for formatting)
2. Unzip the latest [tsschecker](https://github.com/tihmstar/tsschecker/releases) release, and place the unzipped folder in the same directory as autotss.py
	- Once the unzipped tsschecker folder is in the same directory as autotss.py, the binary for your operating system will be automatically selected
	- Or you can manually provide a path to your tsschecker binary:
      -   `autotss('/Users/codsane/tsschecker/tsschecker_macos')`
      -   `python3 autotss.py -p /Users/codsane/tsschecker/tsschecker_macos`
3. Run `python3 autotss.py`
4. (Optional) Schedule autotss to run frequently to save blobs for firmwares as they are signed

## Config File
Your devices.ini file should follow the format below. Specifying a board config is optional but may be required for your device model.
```
[Device Name]
identifier = iPhone9,4
ecid = 1438617935153
```

Example:
```
[codsane's iPhone SE]
identifier = iPhone8,4
ecid = A1032047B013A
boardconfig = n69uap
```

## Known Issues
- iOS 11.2 Build 15C113
    - This specific iOS 11.2 build doesn't like to work with tsschecker for some reason. tsschecker works fine with iOS 11.2 Build 15C114 so that build can be used instead.

- Outdated version of tsschecker at tsschecker's repo
    - The release at the tsschecker repo hasn't been updated in a while and might cause some issues. Instead, the latest version of tsschecker (>=247) can be found here: http://api.tihmstar.net/builds/tsschecker/tsschecker-latest.zip

## Requirements
* python 3
* cron (optional, but recommended for full automation)
* [requests](https://github.com/kennethreitz/requests)
* [dataset](https://github.com/pudo/dataset)
* [tsschecker](https://github.com/tihmstar/tsschecker)

## To Do
- [ ] Add support for Beta/OTA firmwares