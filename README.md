# three-bits-suffice
Supporting data and code for IMC 2018 submission "Three Bits Suffice"

This repository contains the following, for the QUIC and TCP measurements:

## TCP

- Patches to add latency spin signal support for TCP to the Linux kernel [4.9](tpc/kernel_patches/linux-4.9-tcpspin.patch) and [4.15](tpc/kernel_patches/linux-4.15-tcpspin.patch).

- The simple [webserver](tcp/webserver/webserver.py) we used for testing the spin bit with TCP.

- The results from all our TCP spin- and TS-based [RTT estimations](tcp/data/).
   This data is organized as follows:
  - [01_do-vpp-do](tcp/data/01_do-vpp-do) contains the digital ocean to digital ocean measurements
  - [02_wired-vpp-do](tcp/data/02_wired-vpp-do) contains the wired access networks to digital ocean measurements
  - [03_wifi-vpp-do](tcp/data/03_wifi-vpp-do) contains the wireless access networks to digital ocean measurements

   Each CSV file contains data from one measurement.
   For the access network measurements, the prefix of each file is an identifier of the access network,
   and the postfix an identifier of the digital oceans used.

- [Plots](/tcp/plots) from each measurement run, and Figure 5 and 6 from the paper

- [Scripts](tcp/scripts/) to create these plots

## QUIC

- The [master thesis](quic/thesis.pdf) this paper was based on.

- A [script](quic/download_dataset.bash) to download the actual QUIC dataset. 
Be carefull, running this script downloads around 100 GB of data!

- [Pinq](quic/pinq/), the modified QUIC endpoint implementation used for the experiments.
   This folder is a snapshot of  https://github.com/pietdevaere/minq.

- [Plots](quic/plots/) for each run of the dataset, as well as Figures 3 and 4 from the paper.

- Various [Scripts](quic/scripts) to generate these figures and to orchestrate emulated measurements.

   Scripts for generating figures:

  - [analyze_vpp.py](quic/scripts/analyze_vpp.py) This script is two things:

     1. A script to generate detailed plots for an individual measurement run. 

     1. An toolkit that can be used by other scripts that want
     to analyze runs. For example, `make_figure_3_and_4.py`.

  - [make_figure_3_and_4.py](quic/scripts/make_figure_3_and_4.py) generates Figure 3 and 4 from the paper.

   Scripts for orchestrating runs:

  - [simple_for_vpp.py](quic/scripts/simple_for_vpp.py) orchestrates a single measurement.

  - [run_series.py](quic/scripts/run_series.py) calls `simple_for_vpp.py` repetitively to run a series of measurements with one command.


### Names of spin signal flavours and dataset information.

This dataset uses different naming for the various flavours of
the spin signal. The below table gives a translation.

| Name in paper | Name in thesis    | Name in dataset | comment                                  |
|---------------|-------------------|-----------------|------------------------------------------|
| spin bit      | basic             | basic           |                                          |
| packet number | pn                | pn              |                                          |
|               |                   | pn_valid        |                                          |
|               |                   | valid           |                                          |
|               |                   | pn_valid_edge   |                                          |
|               | valid edge        | valid_edge      |                                          |
| VEC           |  VEC              | status          |                                          |
|               | two bit spin      | two_bit         |                                          |
|               | static heuristic  | stat_heur       |                                          |
| heuristic     | dynamic heuristic | rel_heur        |                                          |
|               |                   | handshake       | RTT measured by observing QUIC handshake |

Each measurement in the dataset has two phases: For the first 80 seconds, the emulated network has no impairments other than a 40 ms RTT. Then, the impairments under test are introduced, and the measurement continuous for an additional 80 seconds. The NetEm parameters used to introduce the impairments are in the
name of each measurement run.