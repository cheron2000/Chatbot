# EfficientNet training on HAM10000

This workspace is set up to train an EfficientNet model on the HAM10000 skin lesion dataset.

## Folder structure

Place your downloaded HAM10000 files in the dataset folder, for example:

./dataset/
  HAM10000_images_part_1.zip
  HAM10000_images_part_2.zip
  HAM10000_metadata.tab

The training script will automatically extract the image ZIP files when needed.

## Install dependencies

Use the Python environment already configured in this workspace:

D:/virgov/venv/Scripts/python.exe -m pip install -r requirements.txt

## Train the model

D:/virgov/venv/Scripts/python.exe train_efficientnet.py --data-root data/ham10000 --epochs 10 --batch-size 32

You can also change the model with:

D:/virgov/venv/Scripts/python.exe train_efficientnet.py --model-name efficientnet_b1
