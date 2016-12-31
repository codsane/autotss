import requests as r
import dataset
import subprocess
import os

def save_blobs(identifier, ecid, version): # Save blobs with tsschecker
    save_path = os.path.dirname(os.path.realpath(__file__)) + "\\" + identifier + "\\" + ecid + "\\" + version
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    output = subprocess.Popen(['tsschecker/tsschecker_windows', '-e', ecid, '-d', identifier, '-i', version, '-s', '-b', '--save-path', save_path], stdout=subprocess.PIPE)
    if "success" in output.stdout.read().lower():
        print "Successfully saved blobs for " + identifier + " on " + version + ' with ECID: ' + ecid + "!"
    else:
        print "Error saving blobs for " + identifier + " on " + version + ' with ECID: ' + ecid + "!"
    return

def check_for_devices(): # Check for new entries in devices.txt and add them to the database
    identifier = ''
    ecid = ''

    with open('devices.txt') as f:
        for line in f:
            identifier, ecid = line.strip().replace(" ","").split(":")

            db = dataset.connect('sqlite:///tss.db')

            blobs_db = db['blobs']
            if blobs_db.find_one(ecid=ecid) is None:
                blobs_db.insert_ignore(dict(identifier=identifier, ecid=ecid, versions_saved=''), ['identifier'])
                print "Added " + identifier + " with ECID: " + ecid + " to database."

def main():
    check_for_devices()

    db = dataset.connect('sqlite:///tss.db')

    blobs_db = db['blobs']
    api_db = db['api']
    api_db.insert_ignore(dict(field='last_modified', value=''), ['field'])
    api_db.insert_ignore(dict(field='num_devices', value=''), ['field'])


    api = r.get("https://api.ineal.me/tss/all")

    if (api.headers['last-modified'] != api_db.find_one(field='last_modified')['value']) or (str(blobs_db.count()) != api_db.find_one(field='num_devices')['value']):
        print "TSS API has been modified...looking for newly signed versions..."
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

if __name__ == "__main__":
    main()
