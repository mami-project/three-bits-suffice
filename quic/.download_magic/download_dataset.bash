#!/bin/bash

DATASET_URLS=(\
	"https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/294813/quic_dataset_part_1.tar"\
	"https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/294813/quic_dataset_part_2.tar"\
	"https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/294813/quic_dataset_part_3.tar"\
	"https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/294813/quic_dataset_part_4.tar"\
	"https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/294813/quic_dataset_part_5.tar"\
	"https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/294813/quic_dataset_part_6.tar"\
)

read -p "Download dataset? This will use about 80 GB. (y/N) " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
	rm -rf data
	mkdir data
	for URL in "${DATASET_URLS[@]}"
	do
		echo $URL
		curl $URL | tar -xvf - -C data
	done 
fi
