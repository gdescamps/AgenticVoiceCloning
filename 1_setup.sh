#!/bin/bash
git submodule update --init --recursive

rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130
pip install -r ./requirements.txt

pushd ./higgs-audio
pip install -r ./requirements.txt
pip install -e .
popd

dvc pull
