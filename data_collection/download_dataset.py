import argparse
import io
import json
import os
import random
import urllib.request
import zipfile
from collections import defaultdict

METADATA_URL = (
    "https://storage.googleapis.com/public-datasets-lila/"
    "snapshotserengeti-v-2-0/SnapshotSerengeti_S1-11_v2_1.json.zip"
)
SINGLE_SEASON_METADATA_URL = (
    "https://lilawildlife.blob.core.windows.net/lila-wildlife/"
    "snapshotserengeti-v-2-0/SnapshotSerengetiS01.json.zip"
)
IMAGE_BASE_URL = (
    "https://lilawildlife.blob.core.windows.net/lila-wildlife/"
    "snapshotserengeti-unzipped/"
)

TARGET_SPECIES = {
    "elephant": "elephant",
    "zebra": "zebra",
    "lion": "lion",
    "wildebeest": "wildebeest",
}
EMPTY_LABELS = {"empty", "blank"}


def download_metadata(url, cache_path):
    if os.path.exists(cache_path):
        print(f"Using cached metadata: {cache_path}")
        with open(cache_path, "r") as f:
            return json.load(f)

    print(f"Downloading metadata from {url} ...")
    with urllib.request.urlopen(url) as resp:
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        json_name = [n for n in zf.namelist() if n.endswith(".json")][0]
        with zf.open(json_name) as jf:
            meta = json.load(jf)

    with open(cache_path, "w") as f:
        json.dump(meta, f)

    return meta


def group_images_by_class(meta):
    cat_lookup = {c["id"]: c["name"].lower() for c in meta["categories"]}
    image_lookup = {img["id"]: img for img in meta["images"]}

    class_to_images = defaultdict(set)

    for ann in meta["annotations"]:
        cat_name = cat_lookup.get(ann["category_id"], "").lower()
        image = image_lookup.get(ann["image_id"])
        if image is None:
            continue

        if cat_name in TARGET_SPECIES:
            class_to_images[TARGET_SPECIES[cat_name]].add(image["file_name"])
        elif cat_name in EMPTY_LABELS:
            class_to_images["empty"].add(image["file_name"])

    return class_to_images


def sample_balanced_subset(class_to_images, per_class, seed=42):
    random.seed(seed)
    subset = {}
    for cls, files in class_to_images.items():
        files = list(files)
        random.shuffle(files)
        chosen = files[:per_class]
        subset[cls] = chosen
        print(f"{cls}: selected {len(chosen)} of {len(files)} available")
    return subset


def download_images(subset, out_dir):
    for cls, files in subset.items():
        cls_dir = os.path.join(out_dir, cls)
        os.makedirs(cls_dir, exist_ok=True)
        for i, file_name in enumerate(files):
            dest = os.path.join(cls_dir, os.path.basename(file_name))
            if os.path.exists(dest):
                continue
            url = IMAGE_BASE_URL + file_name
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                print(f"  Failed: {file_name} ({e})")
            if (i + 1) % 100 == 0:
                print(f"  {cls}: {i + 1}/{len(files)} downloaded")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=1800,
                         help="Target images per class (proposal: 1600-2000)")
    parser.add_argument("--out-dir", type=str, default="data/raw")
    parser.add_argument("--metadata-cache", type=str, default="metadata.json")
    parser.add_argument("--single-season", action="store_true",
                         help="Use only Season 1 metadata (faster, for feasibility trial)")
    args = parser.parse_args()

    url = SINGLE_SEASON_METADATA_URL if args.single_season else METADATA_URL
    meta = download_metadata(url, args.metadata_cache)
    class_to_images = group_images_by_class(meta)
    subset = sample_balanced_subset(class_to_images, args.per_class)
    download_images(subset, args.out_dir)

    print("Done.")


if __name__ == "__main__":
    main()