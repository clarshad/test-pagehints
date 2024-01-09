#!/bin/bash
source activate env_cascade_tabnet
echo "source activated"
which pip
/miniconda/envs/env_cascade_tabnet/bin/pip --no-cache-dir install torch==1.7.0+cu110 torchvision==0.8.1+cu110 torchaudio===0.7.0 -f https://download.pytorch.org/whl/torch_stable.html
/miniconda/envs/env_cascade_tabnet/bin/pip --no-cache-dir install mmcv-full==1.4.0 -f https://download.openmmlab.com/mmcv/dist/cu110/torch1.7.0/index.html
