# autotss
Automatically save shsh2 blobs for signed iOS firmwares using [tssstatus](https://ineal.me/tss) and [tsschecker](https://github.com/tihmstar/tsschecker)

## Motivation
>tsschecker is not only meant to be used to check signing status, but also to explore Apple's tss servers. By using all of its customization possibilities, __you might discover a combination of devices and iOS versions that is now getting signed but wasn't getting signed before.__ -[tihmstar (author of tsschecker)](https://github.com/tihmstar/tsschecker/blob/master/README.md#features)

I was curious to see if Apple ever accidentally signs firmwares that should no longer be signed. tsschecker is very useful for this, however a tool to automate this process did not exist.

## Usage
1. Place device info in devices.txt
  1. Find your device's identifier. You can use [IPSW.me's device finder](https://ipsw.me/device-finder) to do this.
  2. Find your device's ECID. Your device ECID can be found in iTunes. (both hex and dec are accepted)
  3. Put this information in 'devices.txt' in the following format: `identifier:ecid` `example: iPhone9,4:E1041046B003A`
2. Place [tsschecker](https://github.com/tihmstar/tsschecker) in the same directory as autotss.py
3. (Optional) Schedule autotss to run frequently to save blobs for firmwares as they are signed

## Requirements
* python
* cron (optional, but recommended for full automation)
* [requests](https://github.com/kennethreitz/requests)
* [dataset](https://github.com/pudo/dataset)
* [tsschecker](https://github.com/tihmstar/tsschecker)

## To Do
- [X] Device Identifier Validation (to prevent adding a device that doesn't exist)
