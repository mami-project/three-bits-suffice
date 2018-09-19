#!/usr/bin/python3

import sys
import csv
import math
import collections
import pickle
import copy
import functools
import os
import os.path
import shutil

import matplotlib.pyplot as plt

def save_figure(figure, filename):
    print("\tGenerating figure: {} ...".format(filename), end="")
    figure.savefig("{}.pdf".format(filename))
    figure.savefig("{}.png".format(filename))
    pickle.dump(figure, open("{}.fig.pickle".format(filename), 'wb'))
    print(" Done")

# stupid hack function used because picke can't handle lambda functions
def return_none():
    return None

magic_translator = { "vec": { "new" : "status_new",
                                 "data" : "status_data"},
                     "single_ts" : { "new" : "single_ts_rtt_new",
                                     "data" : "single_ts_rtt"},
                     "all_ts" : { "new" : "all_ts_rtt_new",
                                  "data" : "all_ts_rtt"}
                     }

def read_vpp_file(path):
    analyzer_names = ("vec", "single_ts", "all_ts")
#    os.system("sed -i $'s/\t//g' {}".format(path))
    csvfile = open(path)
    reader = csv.DictReader(csvfile, skipinitialspace=True)
    #print(reader.fieldnames)

    vpp_data = list()
    ignore_count = 0

    base_time = None
    for row in reader:
        if base_time == None:
            base_time = float(row["time"])

        # ignore the first two entries.
        if ignore_count < 2:
            ignore_count += 1
            continue

        vpp_entry = collections.defaultdict(return_none)
        vpp_entry['time'] = float(row['time']) - base_time
        vpp_entry['host'] = row["host"].strip()
        vpp_entry["sec_num"] = int(row["seq_num"])
        vpp_entry["total_state"] = int(row["total_state"])

        for analyzer in analyzer_names:
            #if row[magic_translator[analyzer]["new"]] == '1':
            vpp_entry[analyzer] = float(row[magic_translator[analyzer]["data"]]) * 1000
            if row[magic_translator[analyzer]["new"]] == '1':
                vpp_entry[analyzer + "_new"] = 1
            else:
                vpp_entry[analyzer + "_new"] = 0

        vpp_data.append(vpp_entry)

    return vpp_data

def get_time_series(vpp_data, analyzer):
    time = [x['time'] for x in vpp_data if x[analyzer + "_new"]]
    rtt =  [x[analyzer] for x in vpp_data if x[analyzer + "_new"]]

    return time, rtt

def moving_minimum_filter(time_in, rtt_in):
    rtt_out = list()

    rtt_out.append(rtt_in[0])

    time_buffer = collections.deque()
    rtt_buffer = collections.deque()
    rtt_buffer.append(rtt_in[0])
    time_buffer.append(time_in[0])

    cursor = 1
    while cursor < len(rtt_in):
        rtt_buffer.append(rtt_in[cursor])
        time_buffer.append(time_in[cursor])

        now = time_in[cursor]
        start_of_window = now - rtt_out[-1]

        # remove values older than one RTT from window
        while time_buffer[0] < start_of_window:
            time_buffer.popleft()
            rtt_buffer.popleft()

        # calculate new RTT estimate
        rtt_estimate = min(rtt_buffer)
        rtt_out.append(rtt_estimate)

        cursor += 1
    return rtt_out

def hack_moving_min_into_vpp_data(vpp_data, analyzer):

    # first generate the smooth RTT data
    time_raw, rtt_raw = get_time_series(vpp_data, analyzer)
    rtt_smooth = moving_minimum_filter(time_raw, rtt_raw)
    time_smooth = time_raw

    # now insert it in to the VPP data structure
    vpp_data_cursor = 0
    smooth_data_cursor = 0

    # forward to the point where the analyzer first has data
    # insert zeros until then
    while vpp_data[vpp_data_cursor]['time'] < time_smooth[smooth_data_cursor]:
        vpp_data[vpp_data_cursor][analyzer + '_smooth'] = 0
        vpp_data[vpp_data_cursor][analyzer + '_smooth_new'] = 0

    # Now, for every measurement, forward
    while smooth_data_cursor < len(time_smooth):

        # insert the new measurement
        vpp_data[vpp_data_cursor][analyzer + '_smooth'] = rtt_smooth[smooth_data_cursor]
        vpp_data[vpp_data_cursor][analyzer + '_smooth_new'] = 1
        vpp_data_cursor += 1

        # advance vpp_data_cursor, until just before next measurement
        while (vpp_data_cursor < len(vpp_data)) and \
        smooth_data_cursor < len(rtt_smooth) - 1 and \
        (vpp_data[vpp_data_cursor]['time'] < time_smooth[smooth_data_cursor + 1]):
            vpp_data[vpp_data_cursor][analyzer + '_smooth'] = rtt_smooth[smooth_data_cursor]
            vpp_data[vpp_data_cursor][analyzer + '_smooth_new'] = 0
            vpp_data_cursor += 1

        smooth_data_cursor += 1

    # And, for the last measurement, keep placing it in the vpp_data
    while vpp_data_cursor < len(vpp_data):
        vpp_data[vpp_data_cursor][analyzer + '_smooth'] = rtt_smooth[-1]
        vpp_data[vpp_data_cursor][analyzer + '_smooth_new'] = 0
        vpp_data_cursor += 1

def make_ecdf_data(vpp_data, analyzerA, analyzerB, weighted = False, relative = False):

    errors = list()
    times = list()

    time_cursor = None
    current_error = None
    A_ready = False
    B_ready = False

    for row in vpp_data:
        ## skip forward to point where there is
        ## data for both analyzers
        if (not A_ready) or (not B_ready):
            if row[analyzerA + "_new"]:
                A_ready = True

            if row[analyzerB + "_new"]:
                B_ready = True

            if A_ready and B_ready:
                current_error = row[analyzerA] - row[analyzerB]
                if relative and row[analyzerA] > 0:
                    current_error = current_error / row[analyzerA] * 100
                time_cursor = row['time']

            continue

        # From now on there is data for both analyzers.
        # If either one is updated, calculate error.
        if row[analyzerA + "_new"] or row[analyzerB + "_new"]:

            # record the info from the period that ended
            last_time_delta = row['time'] - time_cursor
            errors.append(current_error)
            times.append(last_time_delta)

            # start a new error period
            current_error = row[analyzerA] - row[analyzerB]
            if relative and row[analyzerA] > 0:
                current_error = current_error / row[analyzerA] * 100
            time_cursor = row['time']

    # end the last measurement period
    if time_cursor == None:
        print("One analyzer has not data, not generating ECDF")
        return None, None

    last_time_delta = row['time'] - time_cursor
    errors.append(current_error)
    times.append(last_time_delta)

    zipped = list(zip(errors, times))
    zipped.sort()
    errors, times = list(zip(*zipped))


    if not weighted:
        cum_prob = [i/len(errors) for i in range(1, len(errors)+1)]
    else:
        cum_prob = list()
        running_total = 0
        total_time = sum(times)

        for i in range(len(errors)):
            delta = times[i]/total_time
            running_total += delta
            cum_prob.append(running_total)

    return errors, cum_prob



if __name__ == "__main__":
    vpp_data = read_vpp_file(sys.argv[1])

    #time = [x['time'] for x in vpp_data]
    vec_rtt = get_time_series(vpp_data, 'vec')
    single_ts_rtt = get_time_series(vpp_data, 'single_ts')
    all_ts_rtt = get_time_series(vpp_data, 'all_ts')

    #print(vec_rtt)

    ##
    ## Time series figure
    ##
    plt.plot(single_ts_rtt[0], single_ts_rtt[1], 'y.', label="single ts")
    plt.plot(all_ts_rtt[0], all_ts_rtt[1], 'b.', label="all ts ")
    plt.plot(vec_rtt[0], vec_rtt[1], 'r.', label="vec ")
    plt.legend()
    plt.xlabel("time [s]")
    plt.ylabel("rtt [ms]")

    freq_text = "Number of samp les:\nall ts: {}\nsingle ts: {}\nvec: {}"
    freq_text = freq_text.format(len(all_ts_rtt[0]),
                                 len(single_ts_rtt[0]),
                                 len(vec_rtt[0]))
    plt.text(0.3, 0.9, freq_text, horizontalalignment='left',
         verticalalignment='top', transform=plt.gca().transAxes)

    ##
    ## Ecdf
    ##

    plt.figure()
    x, y = make_ecdf_data(vpp_data, 'all_ts', 'vec')
    plt.plot(x,y)
    plt.xlabel("RTT error [ms]")
    plt.ylabel("ECDF")
    plt.ylim((0,1))
    plt.xlim((-20,20))


    plt.show()
