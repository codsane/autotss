from __future__ import print_function
import subprocess
import time

# python 2
# Usage: with libimobiledevice installed, plug in device to generate
# ini entry for autotss

UDIDs = []
print("Waiting for devices...\n")
while 1:
	status = subprocess.check_output(['idevice_id', '-l'], stderr=subprocess.PIPE).rstrip().split('\n') #rstrip because \n
	if status[0]:
		for line in status:
			if line not in UDIDs:
				device_name     = subprocess.check_output(['ideviceinfo', '-k', 'DeviceName',    '-u', line], stderr=subprocess.PIPE).rstrip() #rstrip because \n
				product_type    = subprocess.check_output(['ideviceinfo', '-k', 'ProductType',   '-u', line], stderr=subprocess.PIPE).rstrip() #rstrip because \n
				ecid            = subprocess.check_output(['ideviceinfo', '-k', 'UniqueChipID',  '-u', line], stderr=subprocess.PIPE).rstrip() #rstrip because \n
				hardware_model  = subprocess.check_output(['ideviceinfo', '-k', 'HardwareModel', '-u', line], stderr=subprocess.PIPE).rstrip() #rstrip because \n
				
				print("[" + device_name + "]")
				print("identifier = " + product_type)
				print("ecid = " + ecid)
				print("boardconfig = " + hardware_model + "\n")

				UDIDs.append(line)

	time.sleep(1)