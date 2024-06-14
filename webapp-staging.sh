#!/bin/bash

source /home/yakov/anaconda3/etc/profile.d/conda.sh
export PATH="/home/yakov/anaconda3/bin:$PATH"

export ENV=staging
python app.py

