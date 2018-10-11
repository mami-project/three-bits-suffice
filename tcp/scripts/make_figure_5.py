#!/usr/bin/env python3

# This script generates Figure 5 from the paper.
# call as: $ scripts/make_figure_5.py data/ pickle_cache/ plots/
# The pickle dir is used to store partially processed data structures,
# so the data does not have to be read from the csv files every time the script runs.

import os
import sys
import pickle

import matplotlib.pyplot as plt
from matplotlib.markers import *

import analyze_vpp


def cm2inch(value):
    return value/2.54

def set_fig_size(f, x, y):
	f.set_size_inches(cm2inch(x), cm2inch(y))

fig_width = 16

params = {
   'figure.figsize' : "{}, {}".format(cm2inch(fig_width), cm2inch(fig_width/1.8)),
   'figure.subplot.left' : 0.125,
   'figure.subplot.right' : 0.975,
   'figure.subplot.top' : 0.975,
   'figure.subplot.bottom' : 0.125,
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
YELLOW = (255/255, 255/255, 51/255)
LIGHTBLUE = (137/255,207/255,240/255)


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

### For plot in paper submitted to initial review
#data_files = ("01_do-vpp-do/catserver-5-5077",
#              "02_wired-vpp-do/gutenswil1-wired-5152.csv",
#              "03_wifi-vpp-do/britram1-wifi-5152.csv")

data_files = ("01_do-vpp-do/vpp_data_19.csv",
              "02_wired-vpp-do/gutenswil1-wired-5152.csv",
              "03_wifi-vpp-do/britram1-wifi-5152.csv")
#data_files = (base_dir + '/' + i for i in data_files)

for item in data_files:
    data_dir, data_file = item.split('/')
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

DEEP_RED = (184/255, 0, 0)
SAND = (254/255, 221/255, 170/255)
PINK = (249/255, 170/255, 254/255)
BETTER_BLUE = '#558EB6'

analyzers_to_plot = (("all_ts", '0.666', 'x', '1.2', '-', "TCP timestamps"),
                     ("vec", 'r', ".", '2.8', '', "Spin signal"),
                     )

fig, axes = plt.subplots(3, 1, True)


### For plot in paper submitted to initial review
#ylims = ((60, 90),
#         (40, 100),
#         (0, 1000),
#         )

ylims = ((50, 80),
         (40, 100),
         (0, 1000),
         )

run_labels = ("a) DC to DC",
              "b) Wired home network to DC",
              "c) Wireless home network to DC",
              )

for i in range(len(data_set)):
    data_entry = data_set[i]
    ax = axes[i]

    for analyzer, color, marker, markersize, linestyle, label in analyzers_to_plot:
        x, y = analyze_vpp.get_time_series(data_entry[2], analyzer)
        ax.plot(x, y,
                   lw = 0.05,
                   c = color,
                   ls = linestyle,
                   marker = marker,
                   markersize = markersize,
                   markerfacecolor = color,
                   mew = 0.1)
        ax.set_ylabel("RTT [ms]")
        ax.get_yaxis().set_label_coords(-0.1,0.5)
        ax.set_ylim(ylims[i])
        ax.text(0.025, 0.95,
                run_labels[i],
                horizontalalignment='left',
                verticalalignment='top',
                transform=ax.transAxes,
                #backgroundcolor='0.9',
                size = 9
                )

        if i == 2:
            ax.set_xlabel("Time [s]")
            ax.set_xlim((0, 120))

## make legend entries
legend_ax = axes[0]
for entry in analyzers_to_plot:
    label = entry[5]
    marker = entry [2]
    linestyle = entry[4]
    color = entry[1]

    legend_ax.plot((None, ), (None, ),
                       color = color,
                       marker = marker,
                       linestyle = linestyle,
                       label = label,
                       markerfacecolor = color)
legend_ax.legend(loc = 'upper right', ncol = 2)

analyze_vpp.save_figure(plt.gcf(), "{}/figure_5".format(out_dir, data_entry[0], data_entry[1]))










