#!/usr/bin/python2
import os
import sys

CLIENT_CONF_PREFIX = "1r5"

if os.geteuid() != 0:
	print("I am not root, goodnight")
	sys.exit()
else:
	print("Bow before me for I am root")

os.system("killall ovs-testcontroller")
os.system("mn -c")


#RUN_TYPE

d = dict()
with open('config') as config_file:
	for line in config_file:
		line = line.strip().split()
		if len(line) == 2:
			d[line[0]] = line[1]

netem_options = (
	#"loss gemodel 1 0.1",
	#"loss gemodel 1 0.5",
	#"loss gemodel 1 1",
	#"loss gemodel 1 5",
	#"loss gemodel 1 7",
	#"loss gemodel 1 8",
	#"loss gemodel 1 10",
	#"loss gemodel 1 15",
	#"loss gemodel 1 20",
	"loss gemodel 1 25",
	#"loss gemodel 1 30",
	#"loss random  0.1",
	#"loss random  0.5",
	#"loss random  1",
	#"loss random  5",
	#"loss random  10",
	#"loss random  15",
	#"loss random  20",
	#"delay 1ms reorder 1",
	#"delay 1ms reorder 5",
	#"delay 1ms reorder 10",
	#"delay 1ms reorder 20",
	#"delay 1ms reorder 30",
	#"delay 1ms reorder 40",
#	"delay 1ms reorder 50",
	#"delay 0",
#	"delay 10ms",


	#"delay 5ms",
	#"delay 1ms",
##	"delay 500us",
	#"delay 5ms 1ms",
	#"delay 5ms 2ms",
	#"delay 5ms 3ms",
	#"delay 5ms 4ms",
	#"delay 5ms 5ms",
				 #"delay 10ms 10ms 99",
				 #"delay 10ms 3ms 25",
				 #"loss random 0.01",
				 #"loss random 0.1",
				 #"loss random 1",
				 #"loss random 2",
				 #"delay 100us reorder 1 25",
				 #"delay 100us reorder 10 25",

				 #"delay 1ms reorder 1 25",
				 #"delay 1ms reorder 10 25",
				 #"delay 1ms reorder 50 25",
				 #"delay 5ms reorder 10 25",
				 #"delay 5ms reorder 50 25",


				 #
				 #"loss gemodel 1 10 75 0.1",
				 #"loss gemodel 1 10 100 0.1",

				 ##"loss gemodel 1 25 70 0.1",
				 ##"loss gemodel 1 25 100 0",
				 ##"loss gemodel 1 20 70 0.1",
				 ##"loss gemodel 1 20 100 0",
				 ##"loss gemodel 1 15 70 0.1",
				 ##"loss gemodel 1 15 100 0",
				 ##"loss gemodel 1 30 70 0.1",
				 ##"loss gemodel 1 30 100 0",
				 ##"loss gemodel 1 30 25 0.1",
				 ##"loss gemodel 1 10 25 0.1",s
				 ##"loss gemodel 1 10 75 0.1",

				 ##"loss gemodel 1 10 100 0.1",

				 #"loss gemodel 0.1 10 25 0.1",
				 #"loss gemodel 0.1 10 75 0.1",
				 #"loss gemodel 0.1 10 100 0.1",
				 ##"loss gemodel 0.01 5 25 0.1",
				 ##"loss gemodel 0.01 5 75 0.1",
				 ##"loss gemodel 0.01 5 100 0.1",
				 )

for netem_option in netem_options:
	print('#'*80)
	print('Now moving to netem option: {}'.format(netem_option))
	print('#'*80)
	cmd = "{SCRIPT_PATH}/simple_for_vpp.py --run-name '{prefix}_{netem}' --dynamic-intf '{netem}' --file 10GiB --time 80"
	#cmd += " --tcp"
	#cmd += " --one-direction"
	#cmd += " --no-baseline"
	#cmd = "/home/piet/eth/msc/hephaestus/simple.py --run-name '{netem}' --dynamic-intf '{netem}' --time 30 --heartbeat 100"
	cmd = cmd.format(prefix = CLIENT_CONF_PREFIX, netem = netem_option, **d)
	os.system(cmd)

#print('#'*80)
#print('Now moving to bursty_traffic')
#print('#'*80)
#cmd = "{SCRIPT_PATH}/simple_for_vpp.py --run-name '{prefix}_bursty_traffic_100_5' --time 160 --traffic-gen '--cycles 100 --heartbeat 100 --calm-time 5'"
##cmd += " --no-baseline"
#cmd = cmd.format(prefix = CLIENT_CONF_PREFIX, **d)
#os.system(cmd)
