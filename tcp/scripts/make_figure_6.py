#!/usr/bin/env python3

# This script generates Figure 6 from the paper.
# call as: $ scripts/make_figure_6.py data/ pickle_cache/ plots/
# The pickle dir is used to store partially processed data structures,
# so the data does not have to be read from the csv files every time the script runs.

import os
import sys
import pickle

import matplotlib.pyplot as plt
from matplotlib.markers import *


import analyze_vpp

import numpy as np

def cm2inch(value):
    return value/2.54

def set_fig_size(f, x, y):
	f.set_size_inches(cm2inch(x), cm2inch(y))

fig_width = 8

params = {
   'figure.figsize' : "{}, {}".format(cm2inch(fig_width), cm2inch(fig_width/2.3)),
   'figure.subplot.left' : 0.15,
   'figure.subplot.right' : 0.85,
   'figure.subplot.top' : 1,
   'figure.subplot.bottom' : 0.15,
   'axes.labelsize': 5,
   'font.size': 5,
   'legend.fontsize': 4,
   'xtick.labelsize': 5,
   'ytick.labelsize': 5,
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
   'axes.spines.bottom' : False,
   'axes.spines.top' : False,
   'axes.spines.right' : True,
   'axes.unicode_minus'  : True,
   'pdf.fonttype' : 42,
   'ps.fonttype' : 42
   }
rcParams.update(params)


alpha = 0.2

BLACK = (0.2, 0.2, 0.2)
RED = (1, 0, 0)
LIGHT_BLUE = (0, 1, 1)
BLUE = (0, 0, 1)
DARK_GREEN = (0, 100/255, 0)
PURPLE =  (102/255, 51/255 ,153/255)
PINK = (255/255, 192/255, 203/255)
YELLOW = (128/255, 128/255, 0)

color_rules = (
               ('wifi', RED),
               ('wired', DARK_GREEN),
               ('catserver', BLUE)
               )

base_dir = sys.argv[1]
pickle_dir = sys.argv[2]
out_dir = sys.argv[3]
plt.figure()

data_set = list()

data_dirs = sorted(os.listdir(base_dir))
for data_dir in data_dirs:
    # For Mac users ;-)
    if data_dir == '.DS_Store':
      continue
    if data_dir.find("vm_runs") != -1:
            continue
    #if data_dir.find("03") == -1:
    #        continue
    data_files = os.listdir(base_dir + '/' + data_dir)
    for data_file in data_files:
        if data_file.find("skip") != -1:
            continue
        if data_file[0] == '.':
            continue
        if data_file.find("buehlert") != -1:
            continue
        # if data_file.find("wired-5137") != -1:
        #     continue

        print(data_file, end='')
        pickle_file_name = "{}__{}.pickle".format(data_dir, data_file)
        pickle_file_path = pickle_dir + '/' + pickle_file_name

        from_csv = False
        try:
            pickle_file = open(pickle_file_path, 'rb')
        except FileNotFoundError:
            from_csv = True
        else:
            print(" from pickle.")
            data_set.append(pickle.load(pickle_file))
            pickle_file.close()

        if from_csv:
            print(" from csv")
            vpp_data = analyze_vpp.read_vpp_file(base_dir + '/' + data_dir + '/' + data_file)
            #analyze_vpp.hack_moving_min_into_vpp_data(vpp_data, 'all_ts')
            x, y = analyze_vpp.make_ecdf_data(vpp_data, 'all_ts', 'vec', True, True)
            #x_smooth, y_smooth = analyze_vpp.make_ecdf_data(vpp_data, 'all_ts_smooth', 'vec', True, True)

            data_entry = (data_dir, data_file, vpp_data, x, y)
            data_set.append(data_entry)
            pickle_file = open(pickle_file_path, 'wb')
            pickle.dump(data_entry, pickle_file)
            pickle_file.close()

print("I have {} data_entires.".format(len(data_set)))
print("moving on to plotting")

do_values_vec = list()
wired_values_vec = list()
wifi_values_vec = list()

errors_do = list()
errors_wired = list()
errors_wifi = list()


legend_items = list()
for data_entry in data_set:

    errors, cum_prob = data_entry[3:5]
    #print(max(errors))

    x, y = analyze_vpp.get_time_series(data_entry[2], "all_ts")
    rtts = np.array(y)
    ave = np.average(rtts)
    number_of_estimates_all_ts = len(x)
    number_of_rtts = 2*60*1000 / ave

    x, y = analyze_vpp.get_time_series(data_entry[2], "vec")

    number_of_estimates_vec = len(y)

    print("{},{},{}".format(data_entry[1], number_of_estimates_all_ts / number_of_rtts, number_of_estimates_vec / number_of_rtts))

    if "vpp_data" in data_entry[1]:
        do_values_vec.append(number_of_estimates_vec / number_of_rtts)
        errors_do.extend(errors)

    if "wired" in data_entry[1]:
        wired_values_vec.append(number_of_estimates_vec / number_of_rtts)
        errors_wired.extend(errors)

    if "wifi" in data_entry[1]:
        wifi_values_vec.append(number_of_estimates_vec / number_of_rtts)
        errors_wifi.extend(errors)




########
#Plots #
########

#fig, ax = plt.subplots(2, 1)

#ax[0].boxplot((do_values_vec, wired_values_vec, wifi_values_vec))  # VEC's / RTT
#ax[1].boxplot((errors_do, errors_wired, errors_wifi), showfliers=False) # ERROR
#plt.grid()

## spacing magic

#number_of_boxes = 8
#box_width = 1 / number_of_boxes
#box_centers = [ box_width / 2 + i * box_width for i in range(number_of_boxes)]

DEEP_RED = (184/255, 0, 0)

fig, left_ax = plt.subplots()
leftcolor = '0'
left_ax.axhline(1, color = '0', linewidth = 0.1)


left_plot = left_ax.boxplot((do_values_vec, wired_values_vec, wifi_values_vec),
                patch_artist=True,
                widths = 0.75,
                positions = (1, 4, 7),
                #boxprops = {'color':leftcolor},
                whiskerprops = {'color':leftcolor},
                capprops = {'color':leftcolor},
                medianprops = {'color':'0', 'linewidth':0.5},
                flierprops = {'markeredgecolor':leftcolor})
#left_ax.set_ylim((0.5, 2.2))

print("left boxplot:")
print("   median DC:", left_plot['medians'][0].get_ydata()[0])
print("   median wired:", left_plot['medians'][1].get_ydata()[0])
print("   median wireless:", left_plot['medians'][2].get_ydata()[0])

for box in left_plot['boxes']:
    box.set_facecolor('1')
    box.set_linewidth(0.5)


rightcolor = '#ff6f6f'
right_ax = left_ax.twinx()
right_plot = right_ax.boxplot((errors_do, errors_wired, errors_wifi),
                 showfliers=False,
                 patch_artist=True,
                 widths = 0.75,
                 positions = (2, 5, 8),
                 #boxprops = {'color':rightcolor},
                 whiskerprops = {'color':rightcolor},
                 capprops = {'color':rightcolor},
                 medianprops = {'color':'0', 'linewidth':0.5},
                 flierprops = {'markeredgecolor':rightcolor})
for box in right_plot['boxes']:
    box.set_facecolor(rightcolor)
    box.set_linewidth(0.5)

print("right boxplot:")
print("   median DC (%):", right_plot['medians'][0].get_ydata()[0])
print("   median wired (%):", right_plot['medians'][1].get_ydata()[0])
print("   median wireless (%):", right_plot['medians'][2].get_ydata()[0])

right_ax.spines['right'].set_color('0')
right_ax.set_xlim((0.5, 8.5))
right_ax.spines['left'].set_color('0')

left_ax.tick_params(axis='y', colors='0')
right_ax.tick_params(axis='y', colors='0')
left_ax.set_ylabel("Samples / RTT", color=leftcolor)
right_ax.set_ylabel("Error [%RTT]", color=rightcolor)
left_ax.set_xticks((1.5, 4.5, 7.5))
left_ax.set_xticklabels(('a) DC to DC', 'b) Wired to DC', 'c) Wireless to DC'))
left_ax.tick_params(axis='x', length=0)
#left_ax.set_axis_bgcolor('0.95')
left_ax.set_ylim((0, 2.2))
#right_ax.set_xlim()

left_ax.get_yaxis().set_label_coords(-0.12,0.5)
right_ax.get_yaxis().set_label_coords(1.12,0.5)

left_ax.set_facecolor((0.94, 0.94, 0.94))

#left_ax.get_xaxis().set_visible(False)


analyze_vpp.save_figure(plt.gcf(), "{}/figure_6".format(out_dir))
