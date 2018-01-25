import requests as r
import configparser
import subprocess
import argparse
import dataset
import json
import sys
import os
import io


class autotss:

	def __init__(self, userPath = None):
		self.scriptPath = self.getScriptPath(userPath)
		self.liveFirmwareAPI = self.getFirmwareAPI()
		self.database = dataset.connect('sqlite:///autotss.db')

		self.importNewDevices()
		self.checkAllDevices()
		self.pushToDatabase()

	def importNewDevices(self):
		""" Checks devices.txt for new entries. Parses entries and
		inserts them into the devices table in our database """

		print('\nChecking devices.ini for new devices...')
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
					boardconfig = config.get(section, 'boardconfig').lower()
				except:
					boardconfig = ''
				if not boardconfig:
					boardconfig = self.getBoardConfig(identifier)

				newDevices.append({'deviceName': name, 'deviceID': identifier, 'boardConfig': boardconfig, 'deviceECID': ecid, 'blobsSaved': '[]'})
		else:
			print('Unable to find devices.ini')

		# Add only new devices to database
		for newDevice in newDevices:
			if not db.find_one(deviceECID=newDevice['deviceECID']):
				print('Device: [{deviceName}] ECID: [{deviceECID}] Board Config: [{boardConfig}]'.format(**newDevice))
				numNew += 1
				db.insert(newDevice)
		print('Added {} new devices to the database'.format(str(numNew)))

		return

	def getBoardConfig(self, deviceID):
		""" Using the IPSW.me API, when supplied a device identifier
		the relevant board config will be returned."""

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

	def getFirmwareAPI(self):
		""" Taking the raw response from the IPSW.me API, process
		 the response as a JSON object and remove unsigned firmware
		 entries. Returns a freshly processed devices JSON containing
		 only signed firmware versions. """

		rawResponse = r.get('https://api.ipsw.me/v2.1/firmwares.json/condensed')

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

		print('\nGrabbing devices from the database...')
		self.devices = [row for row in self.database['devices']]
		for device in self.devices:
			print('Device: [{deviceName}] ECID: [{deviceECID}] Board Config: [{boardConfig}]'.format(**device))
		print('Grabbed {} devices from the database'.format(len(self.devices)))


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
			# print('[{0}] [{1}] {2}'.format(device['deviceID'], versionNumber, 'Blobs already saved!'))
			return

		savePath = 'blobs/' + device['deviceID'] + '/' + device['deviceECID'] + '/' + versionNumber + '/' + buildID
		if not os.path.exists(savePath):
			os.makedirs(savePath)

		scriptArguments = [self.scriptPath,
						'-d', device['deviceID'],
						'-e', device['deviceECID'],
						'--boardconfig', device['boardConfig'],
						'--buildid', buildID,
						'--save-path', savePath,
						'-s']

		tssCall = subprocess.Popen(scriptArguments, stdout=subprocess.PIPE)

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
			print('[{0}] [{1} - {2}] {3}'.format(device['deviceName'], versionNumber, buildID, 'Saved shsh blobs!'))
		else:
			self.logBlobsFailed(scriptArguments, savePath, tssOutput)
                        print('[{0}] [{1} - {2}] {3}'.format(device['deviceName'], versionNumber, buildID, 'Error, see log file: ' + './' + savePath + '/tsschecker_log.txt'))

		return

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

	def logBlobsFailed(self, scriptArguments, savePath, tssOutput):
		""" When blobs are unable to be saved, we save
		a log of tsschecker's output in the blobs folder. """

		with open(savePath + '/tsschecker_log.txt', 'w') as file:
			file.write(' '.join(scriptArguments) + '\n\n')
			file.write('\n'.join(tssOutput))

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

	def getScriptPath(self, userPath):
		""" Determines if the user provided a path to the tsschecker
		 binary, whether command line argument or passed to autotss().
		 If the user did not provide a path, try to find it within
		 /tsschecker or /tsschecker-latest and select the proper binary
		 Also verifies that these files exist. """

		scriptPath = None

		argParser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
		argParser.add_argument("-p", "--path", help='Supply the path to your tsschecker binary.\nExample: -p /Users/codsane/tsschecker/tsschecker_macos', required=False, default='')
		argument = argParser.parse_args()

		# Check to see if the user provided the command line argument -p or --path
		if argument.path:
			scriptPath = argument.path

			# Check to make sure this file exists
			if os.path.isfile(argument.path):
				print('Using manually specified tsschecker binary: ' + argument.path)
			else:
				print('Unable to find tsschecker at specificed path: ' + argument.path)
				sys.exit()

		# No command line argument provided, check to see if a path was passed to autotss()
		else:
			if userPath:
				scriptPath = userPath

				# Check to make sure this file exists
				if os.path.isfile(userPath):
					print('Using manually specified tsschecker binary: ' + userPath)
				else:
					print('Unable to find tsschecker at specificed path: ' + userPath)
					sys.exit()

			# No path was passed to autotss(), try and find tsschecker within /tsschecker or /tsschecker-latest
			else:
				if sys.platform == "linux" or sys.platform == "linux2":
					scriptName = 'tsschecker_linux'
				elif sys.platform == "darwin":
					scriptName = 'tsschecker_macos'
				elif sys.platform == "win32" or "win64":
					scriptName = 'tsschecker_windows.exe'

				# Check to make sure this file exists
				theIdealPath = os.path.join('tsschecker', scriptName)
				theOtherOne = os.path.join('tsschecker-latest', scriptName)
				if os.path.isfile(theIdealPath):
					scriptPath = theIdealPath
				elif os.path.isfile(theOtherOne):
					scriptPath = theOtherOne
				else:
					print('\nCould not find the tsschecker binary.')

					''' tsschecker releases haven't included a Windows binary in quite
					a while. We check to see if one exists however warn the user that
					they may have to build one themselves. '''
					if scriptName == 'tsschecker_windows.exe':
						print('Recent tsschecker builds have not included a Windows binary, you may need to build one yourself')

					print('Get tsschecker here: http://api.tihmstar.net/builds/tsschecker/tsschecker-latest.zip')
					print('Unzip into the same folder as autotss')
					sys.exit()

				print('Automatically found tsschecker binary: ' + scriptPath)

		# Check to make sure user has the right tsschecker version
		tssCall = subprocess.Popen(scriptPath, stdout=subprocess.PIPE)

		tssOutput = []
		for line in io.TextIOWrapper(tssCall.stdout, encoding='utf-8'):
			tssOutput.append(line.strip())

		versionNumber = int(tssOutput[0].split('-')[-1].strip())
		if versionNumber < 247:
			print('Your version of tss checker is too old')
			print('Get the latest version here: http://api.tihmstar.net/builds/tsschecker/tsschecker-latest.zip')
			print('Unzip into the same folder as autotss')
			sys.exit()

		return scriptPath

def main():
	# autotss('/Users/codsane/tsschecker/tsschecker_macos')
	autotss()

if __name__ == "__main__":
	main()
