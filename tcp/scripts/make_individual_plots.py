#!/usr/bin/env python3

import os
import sys
import pickle

import matplotlib.pyplot as plt

import analyze_vpp

# This script generates the individual plots for each run.
# call as: $ scripts/make_individual_plots.py data/ pickle_cache/ plots/
# The pickle dir is used to store partially processed data structures,
# so the data does not have to be read from the csv files every time the script runs.

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
    data_files = os.listdir(base_dir + '/' + data_dir)
    for data_file in data_files:
        if data_file.find("skip") != -1:
            continue
        if data_file[0] == '.':
            continue
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

legend_items = list()
for data_entry in data_set:

    fig, ax = plt.subplots(2, 1)
    ax[0].set_title("{}/{}".format(data_entry[0], data_entry[1]))

    # first plot ecdf
    x, y = data_entry[3:5]

    if x and y:
        ax[0].plot(x,y, linewidth = 1)
    else:
        ax[0].text(0.5, 0.5, 'NO ECDF DATA', horizontalalignment='center',
        verticalalignment='center', transform=ax[0].transAxes)

    ax[0].set_xlabel("RTT error [% RTT]")
    ax[0].set_ylabel("ECDF")
    ax[0].set_ylim((0,1))
    ax[0].set_xlim((-50,50))

    # now plot various traces
    for analyzer, color, marker in (("all_ts", "b", '.'), ("all_ts_smooth", "g", 's'), ("vec", 'r', "x")):
        x, y = analyze_vpp.get_time_series(data_entry[2], analyzer)
        if x and y:
            markersize = 0.3
            if analyzer == "all_ts":
                markersize = 1
            ax[1].plot(x, y, label = analyzer, lw = 0.5, c = color, ls = '', marker = marker, markersize = markersize)
            if analyzer == 'vec':
                min_data = min(y)
                max_data = max(y)
                ax[1].set_ylim((min_data - 10, max_data + 110))

    ax[1].legend()
    plt.tight_layout()
    analyze_vpp.save_figure(plt.gcf(), "{}/{}_{}".format(out_dir, data_entry[0], data_entry[1]))
    plt.close(fig)

#plt.gca().axvline(0,  color = 'r')
#plt.gca().axhline(0.5, color = 'r')

#plt.figure()
#for vpp_data_file in vpp_data_files:
    #print(vpp_data_file)
    #vpp_data = analyze_vpp.read_vpp_file(draw_dir + '/' + vpp_data_file)
    #x, y = analyze_vpp.make_ecdf_data(vpp_data, 'all_ts', 'vec', True)
    #plt.plot(x,y, color = (0, 0, 0, 0.1))


#plt.xlabel("RTT error [ms]")
#plt.ylabel("ECDF")
#plt.ylim((0,1))
#plt.xlim((-20,20))
#plt.title(("weighted"))

#plt.show()
