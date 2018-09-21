#!/usr/bin/python2

from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import OVSController
from mininet.link import TCLink

import datetime
import os
import subprocess
import shutil
import shlex
import time
import sys
import argparse
import random
import string

parser = argparse.ArgumentParser(description='Run a minq measurement experiment, creating a trace for VPP analysis')
parser.add_argument("--echo", action="store_true") # WIP
parser.add_argument("--run-name")
parser.add_argument("--dynamic-intf")
parser.add_argument("--no-baseline", action="store_true")
parser.add_argument("--heartbeat", type=int)
parser.add_argument("--file")
parser.add_argument("--time", type=float)
parser.add_argument("--wait-for-client", action="store_true")
parser.add_argument("--traffic-gen")
parser.add_argument("--one-direction", action="store_true")
parser.add_argument("--tcp", action="store_true")
args = parser.parse_args()

d = dict()

with open('config') as config_file:
	for line in config_file:
		line = line.strip().split()
		if len(line) == 2:
			d[line[0]] = line[1]

d['MINQ_LOG_LEVEL'] = "stats"

LOCAL = None

class Logger(object):
	def __init__(self, path):
		self.terminal = sys.stdout
		self.log = open(path, "a")

	def write(self, message):
		self.terminal.write(message)
		self.log.write(message)

	def flush(self):
		self.terminal.flush()
		self.log.flush()

	def fileno(self):
		return self.terminal.fileno()

def configureNetem(interfaces, options):
	for intf in interfaces:
		node = intf.node
		intf_name = intf.name

		## see if there is already a configuration.
		cmd = "tc qdisc show dev {}".format(intf)
		tc_output = node.cmd(cmd)
		print("[{}] tc_output:: {}".format(node, tc_output))
		if tc_output.find("netem") != -1:
			operator = "change"
		else:
			operator = "add"

		## add / update the netem qdisc
		cmd = "tc qdisc {operator} dev {interface} parent 5:1 handle 10: netem {options}"
		cmd = cmd.format(operator = operator, interface = intf_name, options = options)

		tc_output = node.cmd(cmd)
		#print("tc_output:: {}".format(tc_output))

		# check the configuration
		cmd = "tc qdisc show dev {}".format(intf)
		tc_output = node.cmd(cmd)
		print("[{}] tc_output:: {}".format(node, tc_output))

####################################################
## MAKE FOLDER AND ARCHIVE CODE
####################################################

d['timestamp'] = datetime.datetime.now().isoformat()
d['epoch'] = int(time.time())
d['randID'] = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))

if args.run_name != None:
	run_name = args.run_name
else:
	run_name = raw_input("Name for run: ").strip()
if run_name:
	run_name = run_name.replace(' ', '-')
	outputdir = "{OUTPUT_BASE_PATH}/{epoch}-{randID}_{run_name}"
	outputdir = outputdir.format(run_name=run_name, **d)
else:
	outputdir = "{OUTPUT_BASE_PATH}/nameless_runs/{epoch}-{randID}"
	outputdir = outputdir.format(run_name=run_name, **d)


os.makedirs(outputdir)
os.chdir(outputdir)

randID_file = open("randID", 'w')
randID_file.write(d['randID'])
randID_file.close()

epoch_file = open("epoch", 'w')
epoch_file.write(str(d['epoch']))
epoch_file.close()

timestamp_file = open("timestamp", 'w')
timestamp_file.write(d['timestamp'])
timestamp_file.close()

sys.stdout = Logger('console_output.txt')
sys.stderr = sys.stdout

shutil.make_archive("minq", "zip", d['MINQ_PATH'])
shutil.make_archive("moku", "zip", d['MOKU_PATH'])
shutil.make_archive("script", "zip", d['SCRIPT_PATH'])

argfile = open("arguments.txt", 'w')
for var in vars(args):
	argfile.write("{}: {}\n".format(var, vars(args)[var]))
argfile.close()

####################################################
## BUILD NETWORK
####################################################

static_intfops = dict(bw = 100, delay = '10ms')
dynamic_intfops = dict(bw = 100)

net = Mininet(link = TCLink)

controllers = []
switches = []
servers = []
clients = []
links = []

#
#
#          static shaped      dynamic shaped
#              link 0             link 1
#                |                  |
#                V                  V
# +----------+       +----------+       +----------+
# | client-0 | <---> | switch-0 | <---> | switch-1 |
# +----------+       +----------+       +----------+
#                                             ^
#                                             |  <-- unshaped link
#                                             |         link 2
#                                             V
#                                       +----------+
#                                       | observer |
#                                       | switch-2 |
#                                       +----------+
#                                             ^
#                                             |  <-- unshaped link
#                                             |         link 3
#                                             V
# +----------+       +----------+       +----------+
# | server-0 | <---> | switch-4 | <---> | switch-3 |
# +----------+       +----------+       +----------+
#                ^                  ^
#                |                  |
#              link 5             link 4
#          static shaped      dynamic shaped
#

## add switches
switches.append(net.addSwitch('switch-0'))
switches.append(net.addSwitch('switch-1'))
switches.append(net.addSwitch('switch-2'))
switches.append(net.addSwitch('switch-3'))
switches.append(net.addSwitch('switch-4'))

observer = switches[2]

## add controler and servers
controllers.append(net.addController('controller-0'))
servers.append(net.addHost('server-0', ip='10.0.0.1'))
clients.append(net.addHost('client-0', ip='10.0.0.101'))

## add links
links.append(net.addLink(clients[0],  switches[0]))   # link 0
links.append(net.addLink(switches[0], switches[1]))   # link 1
links.append(net.addLink(switches[1], switches[2]))   # link 2
links.append(net.addLink(switches[2], switches[3]))   # link 3
links.append(net.addLink(switches[3], switches[4]))   # link 4
links.append(net.addLink(switches[4], servers[0]))    # link 5


## TEST DISABLE OFFLOADING
for link in links:
	for intf in (link.intf1, link.intf2):
	#	node = intf.node
		cmd = "ethtool -K {} tx off sg off tso off"
		cmd = cmd.format(intf.name)
		intf.node.cmd(cmd)


## configure interfaces

if args.one_direction:
	dynamic_interfaces = (links[1].intf1, links[4].intf1)
else:
	dynamic_interfaces = (links[1].intf1, links[1].intf2, links[4].intf1, links[4].intf2)

static_interfaces  = (links[0].intf1, links[0].intf2, links[5].intf1, links[5].intf2)

for node in net.values():
	if isinstance(node, OVSController):
		print("Not configuring interfaces of controller")
		continue
	for intf in node.intfList():

		if intf in dynamic_interfaces:
			print("Configuring dynamic intf {} from {}".format(intf, node))
			intf.config(**dynamic_intfops)

		elif intf in static_interfaces:
			print("Configuring static intf {} from {}".format(intf, node))
			intf.config(**static_intfops)

		else:
			print("Not configuring intf {} from {}".format(intf, node))

if args.dynamic_intf and args.no_baseline:
	configureNetem(dynamic_interfaces, args.dynamic_intf)

setLogLevel('info')
net.start()
net.pingAll()

####################################################
## RUN MEASUREMENT COMMANDS
####################################################

running_commands = list()

def popenWrapper(prefix, command, host = None, stdin = None, stdout = None, stderr = None):
	args = shlex.split(command)

	if not stdin:
		stdin = subprocess.PIPE
	elif type(stdin) == str:
		stdin = open(stdin, 'r')

	if not stdout:
		stdout = open("{}_stdout.txt".format(prefix), 'w')
	elif type(stdout) == str:
		stdout = open(stdout, 'w')

	if not stderr:
		stderr = open("{}_stderr.txt".format(prefix), 'w')
	elif type(stderr) == str:
		stderr = open(stderr, 'w')

	if host:
		host_name = host.name
		handle = host.popen(args, stdout=stdout, stderr=stderr, stdin=stdin)
	else:
		host_name = "local"
		handle = subprocess.Popen(args, stdout=stdout, stderr=stderr, stdin=stdin)

	print("[{}] running:: {}".format(host_name, command))

	return handle

## Start tcpdump on client
cmd = """tcpdump -i {interface} -n "udp port 4433 or tcp portrange 45670-45690"  -w {tcpdump_file}"""
cmd = cmd.format(interface = "client-0-eth0", tcpdump_file = "client-0_tcpdump.pcap")
handle = popenWrapper("client-0_tcmpdump", cmd, clients[0])
running_commands.append(handle)

## Start tcpdump on server
cmd = """tcpdump -i {interface} -n "udp port 4433 or tcp portrange 45670-45690" -w {tcpdump_file}"""
cmd = cmd.format(interface = "server-0-eth0", tcpdump_file = "server-0_tcpdump.pcap")
handle = popenWrapper("server-0_tcmpdump", cmd, servers[0])
running_commands.append(handle)

## Start tcpdump on observer
cmd = """tcpdump -i {interface} -n "udp port 4433 or tcp portrange 45670-45690" -w {tcpdump_file}"""
cmd = cmd.format(interface = "switch-2-eth1", tcpdump_file = "switch-2_tcpdump.pcap")
handle = popenWrapper("switch-2_tcpdump", cmd, LOCAL)
running_commands.append(handle)

## start ping on client
#cmd = """{SCRIPT_PATH}/ping.py {target_ip}"""
cmd = """ping -D -i 0.001 {target_ip}"""
cmd = cmd.format(target_ip = servers[0].IP(), **d)
handle = popenWrapper("client-0_ping", cmd, clients[0])
running_commands.append(handle)


## Start Minq | TCP Server
if not args.tcp:
	cmd = """sudo -u {USER} MINQ_LOG={MINQ_LOG_LEVEL} /usr/local/go/bin/go run {MINQ_PATH}/bin/server/main.go -addr {server_ip}:4433 -server-name {server_ip}"""
else:
	cmd = """sudo -u {USER} {SCRIPT_PATH}/tcp_endpoint.py server --server-ip {server_ip}"""

if args.echo:
	cmd += " -echo"
cmd = cmd.format(server_ip = servers[0].IP(), **d)
server_stdout_path = "server-0_minq_stdout"
handle = popenWrapper("server-0_minq", cmd, servers[0], stdout = server_stdout_path)
running_commands.append(handle)

## Give the server some time to initialize.
time.sleep(10)

## Start Minq Client
#cmd = """sudo -u {USER} MINQ_LOG={MINQ_LOG_LEVEL} /usr/local/go/bin/go run {MINQ_PATH}/bin/client/main.go -heartbeat 1 -addr {server_ip}:4433"""
if not args.tcp:
	srv_cmd = """sudo -u {USER} MINQ_LOG={MINQ_LOG_LEVEL} /usr/local/go/bin/go run {MINQ_PATH}/bin/client/main.go -addr {server_ip}:4433"""
else:
	srv_cmd = """sudo -u {USER} {SCRIPT_PATH}/tcp_endpoint.py client --server-ip {server_ip}"""

if args.heartbeat:
	srv_cmd += " -heartbeat {}".format(args.heartbeat)
srv_cmd = srv_cmd.format(server_ip = servers[0].IP(), **d)
if args.file:
	client_stdin = "{FILES_PATH}/{filename}".format(filename = args.file, **d)
elif args.traffic_gen != None:
	traffic_cmd = """sudo -u {USER} {SCRIPT_PATH}/traffic_gen.py {arguments}"""
	traffic_cmd = traffic_cmd.format(arguments = args.traffic_gen, **d)
	traffic_generator = popenWrapper("client_0_traffic_gen", traffic_cmd, None, stdout=subprocess.PIPE, stderr=sys.stdout)
	running_commands.append(traffic_generator)
	client_stdin = traffic_generator.stdout
else:
	client_stdin = None
if not args.tcp:
	handle = popenWrapper("client-0_minq", srv_cmd, clients[0], stdin=client_stdin)
else:
	handle = popenWrapper("client-0_tcp", srv_cmd, clients[0], stdin=client_stdin)
running_commands.append(handle)
client_handle = handle

####################################################
## DELAY AND STOP MEASUREMENT
####################################################

def fancyWait(wait_time, steps = 50):
	elapsed_time = 0
	total_time = wait_time

	print("Will run for {} seconds".format(wait_time))
	print("|"+"-"*(steps-2)+"|")

	step_size = float(total_time) / steps
	while wait_time > step_size:
		time.sleep(step_size)
		wait_time -= step_size
		sys.stdout.write('*')
		sys.stdout.flush()
	time.sleep(wait_time)
	sys.stdout.write('\n')

if args.time:
	fancyWait(args.time)

	handle = popenWrapper("client-0_ip", "ip ad", clients[0])
	running_commands.append(handle)

	if args.dynamic_intf and not args.no_baseline:
		configureNetem(dynamic_interfaces, args.dynamic_intf)
		if not args.wait_for_client:
			fancyWait(args.time)
			if client_handle.poll() != None:
				open(" EARLY TERMINATION", 'w').close()
				print(">>> Something went wrong, client terminated early <<<")
			try:
				client_handle.terminate()
			except:
				pass

if args.wait_for_client:
	print("Now waiting for client to terminate")
	startTime = datetime.datetime.now()
	client_handle.wait()
	print("Client is done :) {}".format(datetime.datetime.now() - startTime))

if type(client_stdin) == str:
	cmd = "cmp {} {}"
	cmd = cmd.format(client_stdin, server_stdout_path)
	cmd_args = shlex.split(cmd)
	if  not subprocess.call(cmd_args):
		print("input and output file equal!")

while len(running_commands) > 0:
	handle = running_commands.pop()
	try:
		handle.terminate()
	except:
		pass

print('Done, shutting down mininet')
net.stop()

#####################################################
### RUN MOKUMOKUREN
#####################################################

#cmd = """sudo -u {USER} /usr/local/go/bin/go run {MOKU_PATH}/tmoku/main.go --file {inputfile}"""
#cmd = cmd.format(inputfile = "switch-2_tcpdump.pcap", **d)
#handle = popenWrapper("switch-2_moku", cmd, LOCAL)
#handle.wait()

#####################################################
### RUN ANALYZER SCRIPTS
#####################################################

#cmd = """python3 {SCRIPT_PATH}/analyze_spinbit.py switch-2_moku_stdout.txt client-0_minq_stderr.txt server-0_minq_stderr.txt client-0_ping_stdout.txt client-0 '{title}'"""
#cmd = cmd.format(title=run_name, **d)
#handle = popenWrapper("client-0_spin_", cmd, LOCAL)
#handle.wait()

#cmd = """python3 {SCRIPT_PATH}/analyze_congestion.py client-0_minq_stderr.txt client-0 '{title}'"""
#cmd = cmd.format(title=run_name, **d)
#handle = popenWrapper("client-0_congestion_", cmd, LOCAL)
#handle.wait()

#cmd = """python3 {SCRIPT_PATH}/analyze_congestion.py server-0_minq_stderr.txt server-0 '{title}'"""
#cmd = cmd.format(title=run_name, **d)
#handle = popenWrapper("server-0_congestion_", cmd, LOCAL)
#handle.wait()

#####################################################
### VERIFY THAT FILE WAS SUCESSFULLY COPIED
#####################################################

#if type(client_stdin) == str:
	#if args.wait_for_client:
		#cmd = "cmp {} {}"
		#cmd = cmd.format(client_stdin, server_stdout_path)
		#cmd_args = shlex.split(cmd)
		#not_equal = subprocess.call(cmd_args)

		#if client_stdin and not_equal:
			#print(">>>OUTPUT FILES ARE NOT EQUAL<<<")
			#in_size = os.path.getsize(client_stdin)
			#out_size = os.path.getsize(server_stdout_path)
			#print("File size original: {}, copy: {}".format(in_size, out_size))
			#open(" FAIL", 'w').close()
		#elif client_stdin:
			#print("> output files are equal :) ")
			#os.system("rm server-0_minq_stdout")
			#open(" SUCCESS", 'w').close()
	#else:
		#os.system("rm server-0_minq_stdout")

#####################################################
### CLEAN UP
#####################################################

os.system("chown piet:piet . -R")
os.system("chmod -w *")
