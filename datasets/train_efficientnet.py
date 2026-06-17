import argparse
import random
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import timm
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms


class HAM10000Dataset(Dataset):
    def __init__(self, metadata: pd.DataFrame, data_root: Path, transform=None):
        self.metadata = metadata.reset_index(drop=True)
        self.data_root = Path(data_root)
        self.transform = transform
        self.label_map = {
            label: idx
            for idx, label in enumerate(sorted(self.metadata["dx"].unique().tolist()))
        }

    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, idx):
        row = self.metadata.iloc[idx]
        image_id = row["image_id"]

        image_path = self.data_root / "HAM10000_images_part_1" / f"{image_id}.jpg"
        if not image_path.exists():
            image_path = self.data_root / "HAM10000_images_part_2" / f"{image_id}.jpg"

        if not image_path.exists():
            image_path = self.data_root / "HAM10000_images_part_1" / f"{image_id}.png"
        if not image_path.exists():
            image_path = self.data_root / "HAM10000_images_part_2" / f"{image_id}.png"

        image = Image.open(image_path).convert("RGB")
        if self.transform:
            image = self.transform(image)

        label = self.label_map[row["dx"]]
        return image, torch.tensor(label, dtype=torch.long)


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def ensure_dataset_ready(data_root: Path):
    part1 = data_root / "HAM10000_images_part_1"
    part2 = data_root / "HAM10000_images_part_2"

    if part1.exists() and part2.exists():
        return

    zip_candidates = [
        data_root / "HAM10000_images_part_1.zip",
        data_root / "HAM10000_images_part_2.zip",
    ]

    for zip_path in zip_candidates:
        if not zip_path.exists():
            matches = list(data_root.glob("**/" + zip_path.name))
            if matches:
                zip_path = matches[0]

        if zip_path.exists():
            target_dir = data_root / (
                "HAM10000_images_part_1"
                if "part_1" in zip_path.name
                else "HAM10000_images_part_2"
            )
            target_dir.mkdir(exist_ok=True)
            print(f"Extracting {zip_path.name} to {target_dir}...")
            with zipfile.ZipFile(zip_path, "r") as archive:
                for member in archive.namelist():
                    archive.extract(member, target_dir)

    if not part1.exists() or not part2.exists():
        raise FileNotFoundError(
            "Expected extracted HAM10000 image folders at "
            f"{part1} and {part2}. Please place the downloaded zip files in {data_root}."
        )


def build_transforms(image_size: int = 224):
    train_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(0.5),
            transforms.RandomRotation(15),
            transforms.ColorJitter(
                brightness=0.1, contrast=0.1, saturation=0.1, hue=0.05
            ),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    val_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return train_transform, val_transform


def evaluate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    true_labels, pred_labels = [], []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)
            running_loss += loss.item() * images.size(0)

            preds = torch.argmax(outputs, dim=1)
            true_labels.extend(labels.cpu().tolist())
            pred_labels.extend(preds.cpu().tolist())

    accuracy = accuracy_score(true_labels, pred_labels)
    avg_loss = running_loss / len(loader.dataset)
    return avg_loss, accuracy


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet on HAM10000")
    parser.add_argument(
        "--data-root",
        type=str,
        default="data/ham10000",
        help="Path to the HAM10000 dataset root",
    )
    parser.add_argument(
        "--epochs", type=int, default=10, help="Number of epochs to train"
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument(
        "--model-name",
        type=str,
        default="efficientnet_b0",
        help="timm EfficientNet model name",
    )
    parser.add_argument(
        "--pretrained",
        action="store_true",
        help="Use pretrained timm weights (may download from HF)",
    )
    parser.add_argument(
        "--image-size", type=int, default=224, help="Image size used by the model"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="auto", help="cpu or cuda")
    args = parser.parse_args()

    set_seed(args.seed)

    data_root = Path(args.data_root)
    ensure_dataset_ready(data_root)

    metadata_candidates = sorted(list(data_root.glob("HAM10000_metadata.*")))
    if not metadata_candidates:
        raise FileNotFoundError(
            f"Expected metadata file in {data_root}. Download HAM10000 first."
        )

    metadata_path = metadata_candidates[0]
    sep = "\t" if metadata_path.suffix.lower() == ".tab" else ","
    metadata = pd.read_csv(metadata_path, sep=sep)
    if "dx" not in metadata.columns or "image_id" not in metadata.columns:
        raise ValueError("Metadata file must contain dx and image_id columns.")

    train_df, val_df = train_test_split(
        metadata,
        test_size=0.2,
        stratify=metadata["dx"],
        random_state=args.seed,
    )

    train_transform, val_transform = build_transforms(args.image_size)
    train_dataset = HAM10000Dataset(train_df, data_root, transform=train_transform)
    val_dataset = HAM10000Dataset(val_df, data_root, transform=val_transform)

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0
    )

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device

    num_classes = train_dataset.label_map.__len__()
    model = timm.create_model(
        args.model_name, pretrained=args.pretrained, num_classes=num_classes
    )
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_acc = 0.0
    best_path = Path("best_efficientnet_ham10000.pth")

    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)

        train_loss = running_loss / len(train_loader.dataset)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)

        print(
            f"Epoch {epoch + 1:02d} | train_loss={train_loss:.4f} | val_loss={val_loss:.4f} | val_acc={val_acc:.4f}"
        )

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_name": args.model_name,
                    "model_state_dict": model.state_dict(),
                    "label_map": train_dataset.label_map,
                    "val_accuracy": val_acc,
                },
                best_path,
            )

    print(f"Best validation accuracy: {best_acc:.4f}")
    print(f"Saved checkpoint to: {best_path.resolve()}")


if __name__ == "__main__":
    main()
