import requests as r
import configparser
import subprocess
import dataset
import json
import os
import io


class autotss:

    def __init__(self):
        self.liveFirmwareURL = 'https://api.ipsw.me/v2.1/firmwares.json/condensed'
        self.liveFirmwareAPI = None
        # self.otaFirmwareURL = 'https://api.ipsw.me/v2.1/ota.json/condensed'
        # self.otaFirmwareAPI = None
        self.database = dataset.connect('sqlite:///autotss.db')

        self.importNewDevices()
        self.devices = [row for row in self.database['devices']]
        self.checkAllDevices()
        self.pushToDatabase()

    def importNewDevices(self):
        """ Checks devices.txt for new entries. Parses entries and
        inserts them into the devices table in our database """

        print('Checking devices.ini for new devices...')
        db = self.database['devices']
        newDevices = []
        numNew = 0

        # Check to make sure devices.ini exists, otherwise warn and continue without new devices
        if os.path.isfile('devices.ini'):
            config = configparser.ConfigParser()
            config.read('devices.ini')
            for section in config.sections():
                name = section
                identifier = config.get(section, 'identifier').replace(' ','')
                ecid = config.get(section, 'ecid')

                try:
                    boardconfig = config.get(section, 'boardconfig')
                except:
                    boardconfig = ''
                if not boardconfig:
                    boardconfig = self.getBoardConfig(identifier)

                newDevices.append({'deviceName': name, 'deviceID': identifier, 'boardConfig': boardconfig, 'deviceECID': ecid, 'blobsSaved': '[]'})
        else:
            print('Unable to find devices.ini')

        # Add only new devices to database
        for newDevice in newDevices:
            print('Device: [{deviceName}] ECID: [{deviceECID}] Board Config: [{boardConfig}]'.format(**newDevice))
            if not db.find_one(deviceECID=newDevice['deviceECID']):
                numNew += 1
                db.insert(newDevice)
        print('Added {} new devices to the database'.format(str(numNew)))

        return

    def getBoardConfig(self, deviceID):
        """ Using the IPSW.me API, when supplied a device identifier
        the relevant board config will be returned. The request to
        IPSW.me will be stored as `self.liveFirmwareAPI` to avoid
        unneeded repeated calls to the IPSW.me API. """

        if not self.liveFirmwareAPI:
            self.liveFirmwareAPI = self.removeUnsignedFirmwares(r.get(self.liveFirmwareURL))
        return self.liveFirmwareAPI[deviceID]['BoardConfig']

    def checkForBlobs(self, deviceECID, buildID):
        """ Checks against our database to see if blobs for a
        device have already been saved for a specific iOS version.
        The device is identified by a deviceECID, iOS version is
        identified by a buildID. """

        deviceInfo = self.database['devices'].find_one(deviceECID=deviceECID)

        for entry in json.loads(deviceInfo['blobsSaved']):
            if entry['buildID'] == buildID:
                return True

        return False

    def removeUnsignedFirmwares(self, rawResponse):
        """ Taking the raw response from the IPSW.me API, process
         the response as a JSON object and remove unsigned firmware
         entries. Returns a freshly processed devices JSON containing
         only signed firmware versions. """

        deviceAPI = rawResponse.json()['devices']

        ''' Rather than messing around with copies, we can loop
         through all firmware dictionary objects and append the
         signed firmware objects to a list. The original firmware
         list is then replaced with the new (signed firmware only) list.'''
        for deviceID in deviceAPI:
            signedFirmwares = []
            for firmware in deviceAPI[deviceID]['firmwares']:
                if firmware['signed']:
                    signedFirmwares.append(firmware)
            deviceAPI[deviceID]['firmwares'] = signedFirmwares

        return deviceAPI

    def checkAllDevices(self):
        """ Loop through all of our devices and grab matching
        device firmwares from the firmwareAPI. Device and
        firmware info is sent to saveBlobs(). """

        print('\nSaving unsaved blobs for {} devices...'.format(str(len(self.devices))))
        for device in self.devices:
            for firmware in self.liveFirmwareAPI[device['deviceID']]['firmwares']:
                self.saveBlobs(device, firmware['buildid'], firmware['version'])

        print('Done saving blobs')

    def saveBlobs(self, device, buildID, versionNumber):
        """ First, check to see if blobs have already been
        saved. If blobs have not been saved, use subprocess
        to call the tsschecker script and save blobs. After
        saving blobs, logSavedBlobs() is called to log that
        we saved the device/firmware blobs. """

        if self.checkForBlobs(device['deviceECID'], buildID):
            return True

        print('Device: [{}] Version: [{}]'.format(device['deviceID'], versionNumber))
        savePath = 'blobs/' + device['deviceID'] + '/' + device['deviceECID'] + '/release/' + versionNumber
        if not os.path.exists(savePath):
            os.makedirs(savePath)

        tssCall = subprocess.Popen(['./tsschecker_macos',
                                    '-e', device['deviceECID'],
                                    '--boardconfig', device['boardConfig'],
                                    '--buildid', buildID,
                                    '--save-path', savePath,
                                    '-s'], stdout=subprocess.PIPE)

        # The io module is a bit overkill but helps easily handle the stream from tssCall
        tssOutput = []
        for line in io.TextIOWrapper(tssCall.stdout, encoding='utf-8'):
            tssOutput.append(line.strip())

        ''' Checks console output for the `Saved shsh blobs!`
        string. While this works for now, tsschecker updates
        may break the check. It may be possible to check to
        see if the .shsh file was created and also check for
        the right file format. '''
        if 'Saved shsh blobs!' in tssOutput:
            self.logBlobsSaved(device, buildID, versionNumber)
            return True
        else:
            return False

    def logBlobsSaved(self, device, buildID, versionNumber):
        """ Taking a reference to a device dictionary, we can
         load the string `blobsSaved` from the database into
         a JSON object, append a newly saved version, and
         turn the JSON object back into a string and
         replace `blobsSaved` """

        oldBlobsSaved = json.loads(device['blobsSaved'])
        newBlobsSaved = {'releaseType': 'release', 'versionNumber': versionNumber, 'buildID': buildID}

        oldBlobsSaved.append(newBlobsSaved)

        device['blobsSaved'] = json.dumps(oldBlobsSaved)

        return

    def pushToDatabase(self):
        """ Loop through all of our devices and update their
        entries into the database. ECID is used as the value
        to update by, as it is the only unique device identifier."""

        print('\nUpdating database with newly saved blobs...')
        for device in self.devices:
            self.database['devices'].update(device, ['deviceECID'])
        print('Done updating database')

        return

def main():
    autotss()

if __name__ == "__main__":
    main()