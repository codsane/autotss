import requests as r
import subprocess
import dataset
import os


def get_board_config(identifier): # Returns the board config given a device identifier
	api = r.get('https://api.ipsw.me/v2.1/firmwares.json/condensed').json()
	return api['devices'][identifier]['BoardConfig']


def get_ota_versions(identifier): # Returns all OTA versions of iOS for a particular identifier
	versions = []
	api = r.get('https://api.ipsw.me/v2.1/ota.json/condensed').json()
	for firmware in api[identifier]['firmwares']:
		try:
			if firmware['releasetype'] == 'Beta':
				continue
		except KeyError:
			if not firmware['version'].startswith("9.9"):
				if firmware['version'] not in versions:
					versions.append(firmware['version'])
	return versions


def get_beta_versions(identifier): # Returns all beta versions of iOS for a particular identifier
	versions = []
	api = r.get('https://api.ipsw.me/v2.1/ota.json/condensed').json()
	for firmware in api[identifier]['firmwares']:
		try:
			if firmware['releasetype'] == 'Beta':
				if not firmware['version'].startswith("9.9"):
					if firmware['version'] not in versions:
						versions.append(firmware['version'])
		except KeyError:
			continue
	return versions


def save_blobs(identifier, board_config, ecid, version, versions_saved, version_type): # Save shsh2 blobs with tsschecker
	if version_type is "beta":
		save_path = os.path.dirname(os.path.realpath(__file__)) + "/blobs/beta/" + identifier + "/" + ecid + "/" + version

		if not os.path.exists(save_path):
			os.makedirs(save_path)

		output = subprocess.Popen(
			['./tsschecker', '-e', ecid, '--boardconfig', board_config, '-i', version, '-s', '--save-path', save_path, '-b', '-o'],
			stdout=subprocess.PIPE)

		if "Saved shsh blobs!" in output.stdout.read():
			print "[TSS] Successfully saved blobs for " + identifier + " on " + version + " (" + version_type + ")" + ' with ECID: ' + ecid + "!"
		else:
			print "[TSS] Error saving blobs for " + identifier + " on " + version + " (" + version_type + ")" + ' with ECID: ' + ecid + "!"
		db = dataset.connect('sqlite:///devices.db')
		blobs_db = db['blobs']
		blobs_db.update(dict(ecid=ecid, beta_versions_saved=versions_saved + version + ','), ['ecid'])
		return

	elif version_type is "ota":
		save_path = os.path.dirname(os.path.realpath(__file__)) + "/blobs/ota/" + identifier + "/" + ecid + "/" + version

		if not os.path.exists(save_path):
			os.makedirs(save_path)

		output = subprocess.Popen(
			['./tsschecker', '-e', ecid, '--boardconfig', board_config, '-i', version, '-s', '--save-path', save_path, '-o'],
			stdout=subprocess.PIPE)

		if "Saved shsh blobs!" in output.stdout.read():
			print "[TSS] Successfully saved blobs for " + identifier + " on " + version + " (" + version_type + ")" + ' with ECID: ' + ecid + "!"
		else:
			print "[TSS] Error saving blobs for " + identifier + " on " + version + " (" + version_type + ")" + ' with ECID: ' + ecid + "!"
		db = dataset.connect('sqlite:///devices.db')
		blobs_db = db['blobs']
		blobs_db.update(dict(ecid=ecid, ota_versions_saved=versions_saved + version + ','), ['ecid'])
		return

	else:
		save_path = os.path.dirname(os.path.realpath(__file__)) + "/blobs/release/" + identifier + "/" + ecid + "/" + version

		if not os.path.exists(save_path):
			os.makedirs(save_path)

		output = subprocess.Popen(['./tsschecker', '-e', ecid, '--boardconfig', board_config, '-i', version, '-s', '--save-path', save_path], stdout=subprocess.PIPE)

		if "Saved shsh blobs!" in output.stdout.read():
			print "[TSS] Successfully saved blobs for " + identifier + " on " + version + " (" + version_type + ")" + ' with ECID: ' + ecid + "!"
			db = dataset.connect('sqlite:///devices.db')
			blobs_db = db['blobs']
			blobs_db.update(dict(ecid=ecid, release_versions_saved=versions_saved + version + ','), ['ecid'])
		else:
			print "[TSS] Error saving blobs for " + identifier + " on " + version + " (" + version_type + ")" + ' with ECID: ' + ecid + "!"
		return


def check_for_devices(): # Check for new entries in devices.txt and add them to the database
	new_devices = []
	print "Checking for new devices to add to database..."

	with open('devices.txt') as f:
		for line in f:
			device_info, ecid = line.strip().split(':')
			try:
				identifier, board_config = device_info.split('-')
			except ValueError:
				identifier = device_info
				board_config = get_board_config(identifier)

			db = dataset.connect('sqlite:///devices.db')

			blobs_db = db['blobs']
			if blobs_db.find_one(ecid=ecid) is None:
				blobs_db.insert_ignore(dict(identifier=identifier,
											board_config=board_config,
											ecid=ecid,
											release_versions_saved='',
											beta_versions_saved='',
											ota_versions_saved=''), ['ecid'])
				new_devices.append(ecid)
				print "Added - ID: " + identifier + ", ECID: " + ecid + ", Board Config: " + str(board_config)
	if new_devices:
		fetch_signing(new_devices)


def fetch_signing(devices=None):
	api = r.get('https://api.ipsw.me/v2.1/firmwares.json/condensed')

	if devices:
		db = dataset.connect('sqlite:///devices.db')
		blobs_db = db['blobs']
		print "\nNew devices found and added, checking for signed firmwares..."

		for ecid in devices:
			device = blobs_db.find_one(ecid=ecid)
			for firmware in api.json()['devices'][device['identifier']]['firmwares']:
				if firmware['signed']:
					device = blobs_db.find_one(ecid=ecid)
					print "[TSS] Attempting to save blobs for " + device['identifier'] + " on " + firmware['version'] + " (release)" + ' with ECID: ' + device['ecid'] + "..."
					save_blobs(device['identifier'],
								device['board_config'],
								device['ecid'],
								firmware['version'],
								device['release_versions_saved'],
								'release')
			for firmware in get_ota_versions(device['identifier']):
				device = blobs_db.find_one(ecid=ecid)
				print "[TSS] Attempting to save blobs for " + device['identifier'] + " on " + firmware + " (ota)" + ' with ECID: ' + device['ecid'] + "..."
				save_blobs(device['identifier'],
							device['board_config'],
							device['ecid'],
							firmware,
							device['ota_versions_saved'],
							'ota')
			for firmware in get_beta_versions(device['identifier']):
				device = blobs_db.find_one(ecid=ecid)
				print "[TSS] Attempting to save blobs for " + device['identifier'] + " on " + firmware + " (beta)" + ' with ECID: ' + device['ecid'] + "..."
				save_blobs(device['identifier'],
							device['board_config'],
							device['ecid'],
							firmware,
							device['beta_versions_saved'],
							'beta')
	else:
		db = dataset.connect('sqlite:///devices.db')
		api_db = db['api']
		blobs_db = db['blobs']
		api_db.insert_ignore(dict(field='md5', value=''), ['field'])

		if api.headers['content-md5'] != api_db.find_one(field='md5')['value']:
			print "\nNew firmwares bring signed..."

			for row in blobs_db.find():
				versions_saved = row['release_versions_saved'].split(',')
				for firmware in api.json()['devices'][row['identifier']]['firmwares']:
					if firmware['signed']:
						if firmware['version'] not in versions_saved:
							print "[TSS] Attempting to save blobs for " + row['identifier'] + " on " + firmware['version'] + " (release)" + ' with ECID: ' + row['ecid'] + "..."
							save_blobs(row['identifier'],
										row['board_config'],
										row['ecid'],
										row['release_versions_saved'],
										firmware['version'],
										'release')

			api_db.update(dict(field='md5', value=api.headers['content-md5']), ['field'])
		else:
			print "\nNo new firmwares being signed..."
		print "\nChecking for beta/ota firmwares..."
		for row in blobs_db.find():
			versions_saved = row['ota_versions_saved'].split(',')
			for firmware in get_ota_versions(row['identifier']):
				if firmware not in versions_saved:
					print "[TSS] Attempting to save blobs for " + row[
						'identifier'] + " on " + firmware + " (ota)" + ' with ECID: ' + row['ecid'] + "..."
					save_blobs(row['identifier'],
								row['board_config'],
								row['ecid'],
								firmware,
								row['ota_versions_saved'],
								'ota')
			versions_saved = row['beta_versions_saved'].split(',')
			for firmware in get_beta_versions(row['identifier']):
				if firmware not in versions_saved:
					print "[TSS] Attempting to save blobs for " + row[
						'identifier'] + " on " + firmware + " (beta)" + ' with ECID: ' + row['ecid'] + "..."
					save_blobs(row['identifier'],
								row['board_config'],
								row['ecid'],
								firmware,
								row['beta_versions_saved'],
								'beta')
		print "\nDone..."


def main():
	check_for_devices()
	fetch_signing()


if __name__ == "__main__":
	main()