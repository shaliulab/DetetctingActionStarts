#!/bin/bash
# expects to be run in <...>/QuackNN/scripts
. /opt/venv/bin/activate
# source /groups/branson/bransonlab/kwaki/venvs/pytorch/bin/activate
cd ~/checkouts/QuackNN/

python -m i3d.eval_finetune --filelist $1 --gpus 1 --batch_size 6 --window_size 64 --window_start -31 --movie_dir $2 --out_dir $3 --feat_key $4 --eval_type $5 --logfile $6 --model $7 --type $8 --feat_dir $9
