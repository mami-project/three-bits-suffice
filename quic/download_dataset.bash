#!/bin/bash

DOWNLOAD_SCRIPT_URL="https://raw.githubusercontent.com/mami-project/three-bits-suffice/master/quic/.download_magic/download_dataset.bash"

echo "I will fetch and run the following script:"
echo $DOWNLOAD_SCRIPT_URL
read -p "Continue? (y/N) " -n 1 -r
echo  # newline
if [[ $REPLY =~ ^[Yy]$ ]]
	then
		bash <(curl -v $DOWNLOAD_SCRIPT_URL)
fi
