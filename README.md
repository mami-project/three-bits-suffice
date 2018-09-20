# three-bits-suffice
Supporting data and code for IMC 2018 submission "Three Bits Suffice"

This repository contains the following:

- Patches to add latency spin signal support for TCP to the Linux kernel [4.9](linux-4.9-tcpspin.patch) and [4.15](linux-4.15-tcpspin.patch).

- The simple [webserver](internet_measurements/webserver/webserver.py) we used for testing the spin bit with TCP.

- The results from all our TCP spin- and TS-based [RTT estimations](internet_measurements/data/).

- [Scripts](internet_measurements/scripts/) to recreate Figure 5 and 6 from the paper.