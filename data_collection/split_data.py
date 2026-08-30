import argparse
import json
import os
import random
import shutil
from collections import defaultdict


def load_manifest(data_dir):
    manifest_path = os.path.join(data_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path) as f:
        records = json.load(f)
    # class -> file_name -> location
    lookup = defaultdict(dict)
    for rec in records:
        if rec.get("location") is not None:
            lookup[rec["class"]][rec["file_name"]] = rec["location"]
    return lookup


def assign_locations_to_splits(locations_with_counts, train_frac, val_frac, seed):
    rng = random.Random(seed)
    locations = list(locations_with_counts.items())
    rng.shuffle(locations)
    locations.sort(key=lambda kv: kv[1], reverse=True)  # biggest first: pack big ones first

    target_frac = {"train": train_frac, "val": val_frac, "test": 1.0 - train_frac - val_frac}
    totals = {"train": 0, "val": 0, "test": 0}
    assignment = {}

    for loc, count in locations:
        grand_total = sum(totals.values()) or 1
        deficit = {
            split: target_frac[split] - (totals[split] / grand_total)
            for split in totals
        }
        best_split = max(deficit, key=deficit.get)
        assignment[loc] = best_split
        totals[best_split] += count

    return assignment, totals


def split_by_location(data_dir, out_dir, class_name, file_to_location,
                       train_frac, val_frac, seed):
    counts_by_location = defaultdict(int)
    for loc in file_to_location.values():
        counts_by_location[loc] += 1

    assignment, totals = assign_locations_to_splits(
        counts_by_location, train_frac, val_frac, seed
    )

    src_dir = os.path.join(data_dir, class_name)
    split_counts = {"train": 0, "val": 0, "test": 0}
    for file_name, loc in file_to_location.items():
        src_path = os.path.join(src_dir, file_name)
        if not os.path.exists(src_path):
            continue
        split = assignment[loc]
        dest_dir = os.path.join(out_dir, split, class_name)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copyfile(src_path, os.path.join(dest_dir, file_name))
        split_counts[split] += 1

    print(f"  {class_name}: {sum(split_counts.values())} images across "
          f"{len(counts_by_location)} locations -> "
          f"train {split_counts['train']} / val {split_counts['val']} / "
          f"test {split_counts['test']}  (location-based split)")


def split_randomly(data_dir, out_dir, class_name, train_frac, val_frac, seed):
    src_dir = os.path.join(data_dir, class_name)
    files = [f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg"))]
    random.Random(seed).shuffle(files)

    n = len(files)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    splits = {
        "train": files[:n_train],
        "val": files[n_train:n_train + n_val],
        "test": files[n_train + n_val:],
    }
    for split, split_files in splits.items():
        dest_dir = os.path.join(out_dir, split, class_name)
        os.makedirs(dest_dir, exist_ok=True)
        for f in split_files:
            shutil.copyfile(os.path.join(src_dir, f), os.path.join(dest_dir, f))

    print(f"  {class_name}: {n} images -> train {len(splits['train'])} / "
          f"val {len(splits['val'])} / test {len(splits['test'])}  "
          f"(WARNING: random per-image split, no location metadata found)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out-dir", default="data_split")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="Re-split classes that already have a split")
    parser.add_argument("--force-random", action="store_true",
                         help="Ignore manifest.json even if present and use the old random per-image split")
    args = parser.parse_args()

    random.seed(args.seed)
    classes = sorted(
        d for d in os.listdir(args.data_dir)
        if os.path.isdir(os.path.join(args.data_dir, d))
    )
    if not classes:
        print(f"No class folders found under {args.data_dir}")
        return

    print(f"Found classes: {classes}")

    manifest = None if args.force_random else load_manifest(args.data_dir)
    if manifest is None:
        print("No usable manifest.json with location data found -- "
              "falling back to random per-image splitting for all classes.\n"
              "This risks train/val/test leakage if these images came from "
              "bursty camera-trap sequences. Re-run collect_class.py "
              "(updated version) to get location-aware splitting.")

    for class_name in classes:
        existing = os.path.join(args.out_dir, "train", class_name)
        if os.path.exists(existing) and not args.force:
            print(f"  {class_name}: already split (use --force to redo)")
            continue

        if manifest is not None and class_name in manifest and manifest[class_name]:
            split_by_location(
                args.data_dir, args.out_dir, class_name, manifest[class_name],
                args.train_frac, args.val_frac, args.seed,
            )
        else:
            split_randomly(
                args.data_dir, args.out_dir, class_name,
                args.train_frac, args.val_frac, args.seed,
            )

    print(f"\nDone. Split data is in {args.out_dir}/")


if __name__ == "__main__":
    main()