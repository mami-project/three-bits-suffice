#!/bin/bash

DATASET_URL="http://muninn.ethz.ch/spinbit/for_eth_archive/quic_data.tar.gz"

read -p "Download dataset? This will use about 100 GB. (y/N) " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
	curl $DATASET_URL | tar -xvzf - 
    fi
