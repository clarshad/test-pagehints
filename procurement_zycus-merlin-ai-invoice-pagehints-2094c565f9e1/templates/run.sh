#!/bin/bash
# mkdir -p ../Logs/
# mkdir -p ../Logs/Merlin-AI-Invoice-PageHints/

# source activate env_cascade_tabnet
# echo "source activated"
cd ../code ; gunicorn -c gunicorn.conf.py run:app -w 1 --threads 1 --max-requests 10 --max-requests-jitter 5 -t 600 -b 0.0.0.0:6001 --preload
