#! /usr/bin/env python3
import analyze_vpp

import os
import math
import matplotlib.pyplot as plt
from matplotlib.markers import *
import pickle
import collections

script_location = dirname = os.path.dirname(__file__)

PLOT_DIR = script_location + "/../plots/"
BASE_DATA_DIR = script_location + "/../data/"


#plt.style.use(['seaborn-deep', 'seaborn-paper'])
#plt.style.use('ggplot')
#plt.style.use('seaborn-deep')


RED =    "#E24A33"
BLUE =   "#348ABD"
PURPLE = "#988ED5"
GRAY =   "#777777"
YELLOW = "#FBC15E"
GREEN =  "#8EBA42"
PINK =   "#FFB5B8"

RED =    "#C44E52"
BLUE =   "#4C72B0"
PURPLE = "#8172B2"
GRAY =   "#777777"
YELLOW = "#CCB974"
GREEN =  "#55A868"
LIGHT_BLUE =   "#64B5CD"

COLORS = (RED, BLUE, YELLOW, GREEN, GRAY, PINK, PURPLE)
#COLORS = ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974', '#64B5CD', GRAY]
MARKERS    = (("o", 6), ('s', 6), ("v", 6), ("^", 6), ('x', 6), ('p', 6), ('D', 5), ("+", 6), ("8", 6), ("h", 6))
LINESTYLES   = ('-', '--', '-.', '-.', ':')
#MARKERS = list((('${}$'.format(x), 6) for x in 'ABCDEFGHI'))
#MARKERS = (((0, 3, 0),   8),
		   #((3, 0, 0),   8),
		   #((3, 0, -90), 8),
		   #((4, 0, 0),   8),
		   #((4, 0, 45),  8),
		   #((5, 0, 0),   8),
		   #((8, 2, 0),   8),
		   #)

GRIDLINEPROPS = {'linewidth': 0.9, 'color': (0.75, 0.75, 0.75)}

def cm2inch(value):
    return value/2.54

def set_fig_size(f, x, y):
	f.set_size_inches(cm2inch(x), cm2inch(y))

fig_width = 8.6

params = {
   'figure.figsize' : "{}, {}".format(cm2inch(fig_width), cm2inch(fig_width/1.8)),
   'figure.subplot.left' : 0.2,
   'figure.subplot.right' : 1,
   'figure.subplot.top' : 1,
   'figure.subplot.bottom' : 0.21,
   'axes.labelsize': 9,
   'font.size': 9,
   'legend.fontsize': 8,
   'xtick.labelsize': 9,
   'ytick.labelsize': 9,
   'text.usetex': False,
   'markers.fillstyle': 'none',
   'legend.fancybox': False,
   'legend.facecolor': '0.9',
   'legend.edgecolor': '0.9',
   'legend.frameon': True,
   'axes.linewidth': 1,
   'axes.grid': 0,
   'grid.color': '0.9',
   'grid.linestyle': '-',
   'grid.linewidth': '.75',
   'axes.spines.left' : True,
   'axes.spines.bottom' : True,
   'axes.spines.top' : False,
   'axes.spines.right' : False,
   'axes.unicode_minus'  : True,


   }
rcParams.update(params)


INTERVAL_OF_INTEREST = (90,150)

analyzer_names = ["basic", "pn", "pn_valid", "valid", "pn_valid_edge",
						"valid_edge", 'status', "two_bit", "stat_heur", "rel_heur", "handshake"]

analyzers_to_plot = (("basic", "Spin bit", 0),
					 ("pn", "Packet number", 1),
#					 ("stat_heur", "Static heuristic", 2),
					 ("rel_heur", "Heuristic", 3),
					 ("status", "VEC", 4),
					)

analyzer_to_plot_half_rtt = analyzers_to_plot + (("status_half", "VEC half-RTT", 4), )

def save_figure(figure, filename):
	print("\tGenerating figure: {} ...".format(filename), end="")
	figure.savefig(PLOT_DIR + "{}.pdf".format(filename))
	#figure.savefig(PLOT_DIR + "{}.svg".format(filename))
	figure.savefig(PLOT_DIR + "{}.png".format(filename))
	pickle.dump(figure, open(PLOT_DIR + "{}.fig.pickle".format(filename), 'wb'))
	plt.close(figure)
	print("Done")

def count_valid_edges_endpoint(mbytes, mtimes, interval = None):
	counter = 0
	for i in range(len(mbytes)):
		time = mtimes[i]
		byte = mbytes[i]
		if interval and not (time > interval[0] and time < interval[1]):
			continue
		if byte & 0x01:
			counter += 1

	return counter

def count_double_valid_edges_observer(run, interval = None):
	counter = 0
	mbytes = run['observer_mbytes']
	for i in range(1, len(mbytes)):
		time = mbytes[i]['time']
		byte = mbytes[i]['measurement']
		last_byte = mbytes[i-1]['measurement']
		if interval and not (time > interval[0] and time < interval[1]):
			continue
		if (byte & 0x01) and (last_byte & 0x01):
			counter += 1

	return counter

def count_vec_edges_observer(run, vec, interval = None):
	counter = 0
	mbytes = run['observer_mbytes']
	for i in range(len(mbytes)):
		time = mbytes[i]['time']
		byte = mbytes[i]['measurement']
		if interval and not (time > interval[0] and time < interval[1]):
			continue
		if ((byte & 0x0C) >> 2) in vec:
			counter += 1

	return counter


def count_samples_observer(run, analyzer, interval = None):
	counter = 0
	times, rtts, times_rej = analyze_vpp.make_analyzer_data(run, analyzer)
	for time in times:
		if time > interval[0] and time < interval[1]:
			counter += 1
	return counter

##########################################
#### Reordering
##########################################

r_w60_delay_1     = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522827221-bHosL_w60_delay-1ms")
r_w60_reorder_1   = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522826145-R1EMm_w60_delay-1ms-reorder-1")
r_w60_reorder_5   = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522826321-AUuPr_w60_delay-1ms-reorder-5")
r_w60_reorder_10  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522826501-QkHFG_w60_delay-1ms-reorder-10")
r_w60_reorder_20  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522826681-LJBr8_w60_delay-1ms-reorder-20")
r_w60_reorder_30  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522826861-wXE4m_w60_delay-1ms-reorder-30")
r_w60_reorder_40  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/1522827043-BdV25_w60_delay-1ms-reorder-40")

runs_to_plot = ((r_w60_delay_1, 0),
				(r_w60_reorder_1, 1),
				(r_w60_reorder_5, 5),
				(r_w60_reorder_10, 10),
				(r_w60_reorder_20, 20),
				(r_w60_reorder_30, 30),
				(r_w60_reorder_40, 40),
			   )

##
## ECDF for a single loss reordering rate
##

run_for_ecdf = r_w60_reorder_10

f, ax = plt.subplots(1)
#ax.axhline(0.5, **GRIDLINEPROPS)
ax.axvline(0, **GRIDLINEPROPS)

for analyzer, label, i in analyzers_to_plot:
	x_values, y_values = analyze_vpp.make_ecdf_data(run_for_ecdf, analyzer, INTERVAL_OF_INTEREST)
	ax.plot(x_values, y_values,
			label=label,
			#linestyle = LINESTYLES[i],
			color = COLORS[i],
			marker = MARKERS[i][0],
			markersize = MARKERS[i][1],
			markeredgecolor = COLORS[i],
			markerfacecolor = (0,0,0,0),
			markevery = (0.0*i, 0.2))

ax.legend()
ax.set_xlim((-55, 15))
ax.set_xlabel("Observer estimate – client estimate [ms]")
ax.set_ylabel("ECDF")
ax.set_yticks((0, 0.25, 0.5, 0.75, 1))
#ax.grid(True)
save_figure(f, "figure_3a")

##
## Analyzer error over various reordering rates
##

X_VALUE_TO_CMP = 10

f, ax = plt.subplots(1)
ax.axhline(1, **GRIDLINEPROPS)

for analyzer, label, i in analyzers_to_plot:
	## First build the data series
	y_values = list()
	x_values = list()
	for run, reorder_grade in runs_to_plot:
		y_val = analyze_vpp.find_ecdf_y_value(run, analyzer, abs(X_VALUE_TO_CMP), INTERVAL_OF_INTEREST) - \
				analyze_vpp.find_ecdf_y_value(run, analyzer, -abs(X_VALUE_TO_CMP), INTERVAL_OF_INTEREST)
		y_values.append(y_val)
		x_values.append(reorder_grade)

	ax.plot(x_values, y_values,
			label=label,
			color = COLORS[i],
			marker = MARKERS[i][0],
			markersize = MARKERS[i][1],
			markeredgecolor = COLORS[i],
			markerfacecolor = (0,0,0,0))

#ax.legend()
#ax.set_xticks(x_values)
ax.set_xlabel("Packet reordering rate [%]")
ax.set_ylabel("Fraction of samples\nwith |error| < 10 ms")
#ax.grid(True)
save_figure(f, "figure_3b")

##
## Analyzer sample rate over various reordering rates
##
# f, ax = plt.subplots(1)
# ax.axhline(1, **GRIDLINEPROPS)

# for analyzer, label, i in analyzer_to_plot_half_rtt:
# 	#analyzer, label = analyzers_to_plot_hack[i]
# 	## First build the data series
# 	y_values = list()
# 	x_values = list()
# 	for run, reorder_grade in runs_to_plot:
# 		valid_edges = 0
# 		valid_edges += count_valid_edges_endpoint(run['server_mbytes'],
# 												  run['server_mtimes'],
# 												  INTERVAL_OF_INTEREST)
# 		valid_edges += count_valid_edges_endpoint(run['client_mbytes'],
# 												  run['client_mtimes'],
# 												  INTERVAL_OF_INTEREST)

# 		if analyzer == "status_half":
# 			sampled_edges =  count_vec_edges_observer(run, (2, 3), INTERVAL_OF_INTEREST)

# 		else:
# 			sampled_edges = count_samples_observer(run, analyzer, INTERVAL_OF_INTEREST)

# 		y_values.append(sampled_edges/valid_edges)
# 		x_values.append(reorder_grade)
# 		#print(reorder_grade, valid_edges)

# 	#print()
# 	linestyle = None
# 	if analyzer == "status_half":
# 		linestyle = ':'
# 	else:
# 		label = None
# 	ax.plot(x_values, y_values,
# 			label = label,
# 			color = COLORS[i],
# 			marker = MARKERS[i][0],
# 			markersize = MARKERS[i][1],
# 			markeredgecolor = COLORS[i],
# 			markerfacecolor = (0,0,0,0),
# 			linestyle = linestyle)


# #ax.set_ylim((None, 2))
# ax.legend(loc='upper left')
# #ax.set_xticks(x_values)
# ax.set_xlabel("Packet reordering rate [%]")
# ax.set_ylabel("Edges sampled /\nvalid edges transmitted")
# #ax.grid(True)
# save_figure(f, "reordering_w60_effect_samples")


##
## Analyzer sample rate over various reordering rates
##

RTT = 44e-3

f, ax = plt.subplots(1)
#ax.axhline(2, **GRIDLINEPROPS)

for analyzer, label, i in analyzer_to_plot_half_rtt:
	#analyzer, label = analyzers_to_plot_hack[i]
	## First build the data series
	y_values = list()
	x_values = list()
	for run, reorder_grade in runs_to_plot:
		if analyzer == "status_half":
			sampled_edges =  count_vec_edges_observer(run, (2, 3), INTERVAL_OF_INTEREST)
		else:
			sampled_edges = count_samples_observer(run, analyzer, INTERVAL_OF_INTEREST)

		duration_s = INTERVAL_OF_INTEREST[1] - INTERVAL_OF_INTEREST[0]
		duration_rtt = duration_s / RTT

		y_values.append(sampled_edges/duration_rtt)
		x_values.append(reorder_grade)
		#print(reorder_grade, valid_edges)

	#print()
	linestyle = None
	if analyzer == "status_half":
		linestyle = ':'
	else:
		label = None
	ax.plot(x_values, y_values,
			label = label,
			color = COLORS[i],
			marker = MARKERS[i][0],
			markersize = MARKERS[i][1],
			markeredgecolor = COLORS[i],
			markerfacecolor = (0,0,0,0),
			linestyle = linestyle)


#ax.set_ylim((None, 2))
ax.legend(loc='upper left')
#ax.set_xticks(x_values)
ax.set_xlabel("Packet reordering rate [%]")
ax.set_ylabel("Samples per RTT")
#ax.grid(True)
save_figure(f, "figure_3c")

##############################################################################
#### EFFECT OF BURST LOSS, WINDOW
##############################################################################

r_w20_delay_0        = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522831927-4bloa_w20_delay-0")
r_w20_loss_burst_5   = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522829244-6MCCk_w20_loss-gemodel-1-5")
r_w20_loss_burst_7   = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522829423-fElX0_w20_loss-gemodel-1-7")
r_w20_loss_burst_8   = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522829602-CqHLQ_w20_loss-gemodel-1-8")
r_w20_loss_burst_10  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522829781-mZovb_w20_loss-gemodel-1-10")
r_w20_loss_burst_15  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522829960-KHXoA_w20_loss-gemodel-1-15")
r_w20_loss_burst_20  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522830140-EE0id_w20_loss-gemodel-1-20")
r_w20_loss_burst_25  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522830318-1z2kQ_w20_loss-gemodel-1-25")
r_w20_loss_burst_30  = analyze_vpp.analyze_run(BASE_DATA_DIR + "/" + "1522830498-wiUkE_w20_loss-gemodel-1-30")

runs_to_plot = (
				(r_w20_delay_0, math.inf),
				(r_w20_loss_burst_30, 30),
				(r_w20_loss_burst_25, 25),
				(r_w20_loss_burst_20, 20),
				(r_w20_loss_burst_15, 15),
				(r_w20_loss_burst_10, 10),
				(r_w20_loss_burst_8, 8),
				(r_w20_loss_burst_7, 7),
				(r_w20_loss_burst_5, 5),
			   )

##
## ECDF for a single burst loss rate
##

run_for_ecdf = r_w20_loss_burst_10

f, ax = plt.subplots(1)
#ax.axhline(0.5, **GRIDLINEPROPS)
ax.axvline(0, **GRIDLINEPROPS)


for analyzer, label, i in analyzers_to_plot:
	x_values, y_values = analyze_vpp.make_ecdf_data(run_for_ecdf, analyzer, INTERVAL_OF_INTEREST)
	ax.plot(x_values, y_values,
			label=label,
			color = COLORS[i],
			marker = MARKERS[i][0],
			markersize = MARKERS[i][1],
			markeredgecolor = COLORS[i],
			markerfacecolor = (0,0,0,0),
			markevery = (0.1*i, 0.2))

ax.legend()
ax.set_xlim((-10, 32))
ax.set_xlabel("Observer estimate – client estimate [ms]")
ax.set_ylabel("ECDF")
ax.set_yticks((0, 0.25, 0.5, 0.75, 1))
#ax.set_ylim((-0.01,1.01))
#ax.grid(True)
save_figure(f, "figure_4a")

##
## Analyzer error over various burst rates
##

X_TICKS = (0, 5, 10, 15, 20)

f, ax = plt.subplots(1)
ax.axhline(1, **GRIDLINEPROPS)

for analyzer, label, i in analyzers_to_plot:
	## First build the data series
	y_values = list()
	x_values = list()
	for run, burst_parameter in runs_to_plot:
		y_val = analyze_vpp.find_ecdf_y_value(run, analyzer, abs(X_VALUE_TO_CMP), INTERVAL_OF_INTEREST) - \
				analyze_vpp.find_ecdf_y_value(run, analyzer, -abs(X_VALUE_TO_CMP), INTERVAL_OF_INTEREST)
		y_values.append(y_val)
		burst_length = 1 / (burst_parameter / 100)
		x_values.append(burst_length)

	ax.plot(x_values, y_values,
			label=label,
			color = COLORS[i],
			marker = MARKERS[i][0],
			markersize = MARKERS[i][1],
			markeredgecolor = COLORS[i],
			markerfacecolor = (0,0,0,0))

#ax.legend()
ax.set_xticks(X_TICKS)
ax.set_yticks((0.8, 0.9, 1))
ax.set_xlabel("Average burst length [packets]")
ax.set_ylabel("Fraction of samples\nwith |error| < 10 ms")
#ax.grid(True)
save_figure(f, "figure_4b")


##
## Analyzer sample rate over various burst rates
##
# f, ax = plt.subplots(1)
# ax.axhline(1, **GRIDLINEPROPS)

# for analyzer, label, i in analyzer_to_plot_half_rtt:
# 	#analyzer, label = analyzers_to_plot_hack[i]
# 	## First build the data series
# 	y_values = list()
# 	x_values = list()
# 	for run, burst_parameter in runs_to_plot:
# 		valid_edges = 0
# 		valid_edges += count_valid_edges_endpoint(run['server_mbytes'],
# 												  run['server_mtimes'],
# 												  INTERVAL_OF_INTEREST)
# 		valid_edges += count_valid_edges_endpoint(run['client_mbytes'],
# 												  run['client_mtimes'],
# 												  INTERVAL_OF_INTEREST)

# 		if analyzer == "status_half":
# 			sampled_edges =  count_vec_edges_observer(run, (2, 3), INTERVAL_OF_INTEREST)

# 		else:
# 			sampled_edges = count_samples_observer(run, analyzer, INTERVAL_OF_INTEREST)


# 		burst_length = 1 / (burst_parameter / 100)
# 		#loss_rate = burst_length / (burst_length + GOOD_LENGTH)

# 		y_values.append(sampled_edges/valid_edges)
# 		x_values.append(burst_length)
# 		#print(burst_parameter, valid_edges)

# 	#print()
# 	linestyle = None
# 	if analyzer == "status_half":
# 		linestyle = ':'
# 	ax.plot(x_values, y_values,
# 			label=label,
# 			color = COLORS[i],
# 			marker = MARKERS[i][0],
# 			markersize = MARKERS[i][1],
# 			markeredgecolor = COLORS[i],
# 			markerfacecolor = (0,0,0,0),
# 			linestyle = linestyle)

# #ax.legend()
# ax.set_xticks(X_TICKS)
# ax.set_xlabel("Average burst length [packets]")
# ax.set_ylabel("Edges sampled /\nvalid edges transmitted")
# #ax.grid(True)
# save_figure(f, "loss_burst_w20_effect_samples")

##
## Analyzer sample rate over various burst rates
##

RTT = 40e-3

f, ax = plt.subplots(1)
#ax.axhline(2, **GRIDLINEPROPS)

for analyzer, label, i in analyzer_to_plot_half_rtt:
	#analyzer, label = analyzers_to_plot_hack[i]
	## First build the data series
	y_values = list()
	x_values = list()
	for run, burst_parameter in runs_to_plot:
		if analyzer == "status_half":
			sampled_edges =  count_vec_edges_observer(run, (2, 3), INTERVAL_OF_INTEREST)
		else:
			sampled_edges = count_samples_observer(run, analyzer, INTERVAL_OF_INTEREST)

		duration_s = INTERVAL_OF_INTEREST[1] - INTERVAL_OF_INTEREST[0]
		duration_rtt = duration_s / RTT

		burst_length = 1 / (burst_parameter / 100)

		y_values.append(sampled_edges/duration_rtt)
		x_values.append(burst_length)
		#print(reorder_grade, valid_edges)

	#print()
	linestyle = None
	if analyzer == "status_half":
		linestyle = ':'
	else:
		label = None
	ax.plot(x_values, y_values,
			label = label,
			color = COLORS[i],
			marker = MARKERS[i][0],
			markersize = MARKERS[i][1],
			markeredgecolor = COLORS[i],
			markerfacecolor = (0,0,0,0),
			linestyle = linestyle)

#y_ticks  = (0.3, 0.4, 0.5, 0.6, 0.7 , 0.8, 0.9, 2
#y_labels = (0.3, 0.5,

#ax.set_ytick(y_labels)
#ax.set_yticklabels(y_labels)
#ax.set_yscale('log')
ax.set_ylim((None, 2.1))
ax.legend(loc='lower left')
#ax.set_xticks(x_values)
ax.set_xlabel("Average burst length [packets]")
ax.set_ylabel("Samples per RTT")
#ax.grid(True)
save_figure(f, "figure_4c")