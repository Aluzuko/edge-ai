import argparse
import json
import os
import random
import zipfile
import io
import sys
import urllib.request

METADATA_BASE = "https://lilawildlife.blob.core.windows.net/lila-wildlife/snapshotserengeti-v-2-0"
IMAGE_BASE = "https://storage.googleapis.com/public-datasets-lila/snapshotserengeti-unzipped"

CLASS_TO_CATEGORIES = {
    "elephant": ["elephant"],
    "zebra": ["zebra"],
    "wildebeest": ["wildebeest"],
    "lion": ["lionfemale", "lionmale", "lioncub"],
    "empty": ["empty"],
}


def download_file(url, dest_path):
    if os.path.exists(dest_path):
        return dest_path
    print(f"  downloading {url}")
    urllib.request.urlretrieve(url, dest_path)
    return dest_path


def load_season_metadata(season, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    zip_name = f"SnapshotSerengeti{season}.json.zip"
    zip_path = os.path.join(cache_dir, zip_name)
    download_file(f"{METADATA_BASE}/{zip_name}", zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        json_name = [n for n in zf.namelist() if n.endswith(".json")][0]
        with zf.open(json_name) as f:
            return json.load(f)


def collect_candidates(metadata, wanted_categories):
    cat_ids = {c["id"] for c in metadata["categories"] if c["name"] in wanted_categories}
    if not cat_ids:
        return []

    images_by_id = {img["id"]: img for img in metadata["images"]}
    matched_image_ids = {
        ann["image_id"] for ann in metadata["annotations"] if ann["category_id"] in cat_ids
    }

    best_per_sequence = {}
    for img_id in matched_image_ids:
        img = images_by_id.get(img_id)
        if img is None:
            continue
        seq_key = img.get("seq_id", img_id)
        best_per_sequence.setdefault(seq_key, img)

    return list(best_per_sequence.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--class", dest="class_name", required=True, choices=CLASS_TO_CATEGORIES.keys())
    parser.add_argument("--target", type=int, default=1800, help="Target number of images for this class")
    parser.add_argument("--season", nargs="+", default=["S01"], help="One or more seasons, e.g. S01 S02")
    parser.add_argument("--out-dir", default="data", help="Root output folder")
    parser.add_argument("--cache-dir", default=".metadata_cache", help="Where metadata jsons are cached")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    class_dir = os.path.join(args.out_dir, args.class_name)
    os.makedirs(class_dir, exist_ok=True)

    already_have = set(os.listdir(class_dir))
    print(f"Already have {len(already_have)} images for class '{args.class_name}'")

    wanted_categories = CLASS_TO_CATEGORIES[args.class_name]
    all_candidates = []
    for season in args.season:
        print(f"Loading metadata for season {season} ...")
        metadata = load_season_metadata(season, args.cache_dir)
        candidates = collect_candidates(metadata, wanted_categories)
        print(f"  {season}: {len(candidates)} candidate images (after de-duplicating sequences)")
        all_candidates.extend(candidates)

    random.shuffle(all_candidates)

    still_needed = args.target - len(already_have)
    if still_needed <= 0:
        print(f"Already at or above target ({args.target}). Nothing to download.")
        return

    downloaded = 0
    for img in all_candidates:
        if downloaded >= still_needed:
            break
        file_name = img["file_name"]
        safe_name = file_name.replace("/", "_")
        if safe_name in already_have:
            continue
        dest_path = os.path.join(class_dir, safe_name)
        url = f"{IMAGE_BASE}/{file_name}"
        try:
            urllib.request.urlretrieve(url, dest_path)
            downloaded += 1
            if downloaded % 50 == 0:
                print(f"  downloaded {downloaded}/{still_needed}")
        except Exception as e:
            print(f"  failed: {file_name} ({e})", file=sys.stderr)

    total_now = len(os.listdir(class_dir))
    print(f"\nDone. Class '{args.class_name}' now has {total_now} images in {class_dir}")
    if total_now < args.target:
        print(f"Still short of target ({args.target}). Add another --season and re-run "
              f"(already-downloaded files are skipped automatically).")


if __name__ == "__main__":
    main()
