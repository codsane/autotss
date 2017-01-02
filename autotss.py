from sys import platform
import requests as r
import subprocess
import dataset
import os

def get_device_list():
    device_list = []

    api = r.get("https://api.ineal.me/tss/all")
    for device in api.json():
        device_list.append(device)

    return device_list

def save_blobs(identifier, ecid, version): # Save shsh2 blobs with tsschecker
    save_path = os.path.dirname(os.path.realpath(__file__)) + "\\" + identifier + "\\" + ecid + "\\" + version

    if platform.startswith("linux"):
        user_platform = "linux"
        save_path = save_path.replace("\\","/")
    elif platform == "darwin":
        user_platform = "macos"
        save_path = save_path.replace("\\", "/")
    elif platform == "win32":
        user_platform = "windows"

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    output = subprocess.Popen(['tsschecker/tsschecker_' + user_platform, '-e', ecid, '-d', identifier, '-i', version, '-s', '--save-path', save_path], stdout=subprocess.PIPE)

    if "success" in output.stdout.read().lower():
        print "Successfully saved blobs for " + identifier + " on " + version + ' with ECID: ' + ecid + "!"
    else:
        print "Error saving blobs for " + identifier + " on " + version + ' with ECID: ' + ecid + "!"
    return

def check_for_devices(): # Check for new entries in devices.txt and add them to the database
    print "Checking for new devices to add to database..."

    with open('devices.txt') as f:
        for line in f:
            identifier, ecid = line.strip().replace(" ","").split(":")

            if identifier in get_device_list():
                db = dataset.connect('sqlite:///devices.db')

                blobs_db = db['blobs']
                if blobs_db.find_one(ecid=ecid) is None:
                    blobs_db.insert_ignore(dict(identifier=identifier, ecid=ecid, versions_saved=''), ['ecid'])
                    print "Added " + identifier + " with ECID: " + ecid + " to database."
            else:
                print "Could not add " + identifier + " with ECID: " + ecid + " to database...invalid identifier."

def main():
    check_for_devices()

    db = dataset.connect('sqlite:///devices.db')

    blobs_db = db['blobs']
    api_db = db['api']
    api_db.insert_ignore(dict(field='last_modified', value=''), ['field'])
    api_db.insert_ignore(dict(field='num_devices', value=''), ['field'])

    api = r.get("https://api.ineal.me/tss/all")

    print "\nChecking for new signed firmwares or new added devices..."
    if (api.headers['last-modified'] != api_db.find_one(field='last_modified')['value']) or (str(blobs_db.count()) != api_db.find_one(field='num_devices')['value']):
        if str(blobs_db.count()) != api_db.find_one(field='num_devices')['value']:
            print "New devices found, checking for signed firmwares..."

        if (api.headers['last-modified'] != api_db.find_one(field='last_modified')['value']):
            print "New signed firmwares found...\n"

        for row in blobs_db.find():
            versions_saved = row['versions_saved'].split(',')
            for firmware in api.json()[row['identifier']]["firmwares"]:
                if firmware["signing"]:
                    if firmware['version'] not in versions_saved:
                        print "Attempting to save blobs for " + row['identifier'] + " on " + firmware['version'] + ' with ECID: ' + row['ecid'] + "..."
                        save_blobs(row['identifier'], row['ecid'], firmware['version'])
                        blobs_db.update(dict(identifier=row['identifier'], ecid=row['ecid'], versions_saved=row['versions_saved'] + ',' + firmware['version']), ['ecid'])

        api_db.update(dict(field='last_modified', value=api.headers['last-modified']), ['field'])
        api_db.update(dict(field='num_devices', value=str(blobs_db.count())), ['field'])
    else:
        print "No new blobs to be saved...nothing to do here."

if __name__ == "__main__":
    main()
