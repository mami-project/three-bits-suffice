# three-bits-suffice
Supporting data and code for IMC 2018 submission "Three Bits Suffice"

This repository contains the following, for the QUIC and TCP measurements:

## TCP

- Patches to add latency spin signal support for TCP to the Linux kernel [4.9](tpc/kernel_patches/linux-4.9-tcpspin.patch) and [4.15](tpc/kernel_patches/linux-4.15-tcpspin.patch).

- The simple [webserver](tcp/webserver/webserver.py) we used for testing the spin bit with TCP.

- The results from all our TCP spin- and TS-based [RTT estimations](tcp/data/).

   This data is organized as follows:
  - [01_do-vpp-do](tcp/data/01_do-vpp-do) contains the digital ocean to digital ocean measurements
  - [02_wired-vpp-do](tcp/data/01_wired-vpp-do) contains the wired access networks to digital ocean measurements
  - [03_wifi-vpp-do](tcp/data/01_wifi-vpp-do) contains the wireless access networks to digital ocean measurements

   Each CSV file contains data from one measurement.
   For the access network measurements, the prefix of each file is an identifier of the access network,
   and the postfix an identifier of the digital oceans used.

- [Scripts](tcp/scripts/) to recreate Figure 5 and 6 from the paper.

## QUIC