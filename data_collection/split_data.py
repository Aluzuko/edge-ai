import argparse
import os
import random
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out-dir", default="data_split")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="Re-split classes that already have a split")
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

    for class_name in classes:
        existing = os.path.join(args.out_dir, "train", class_name)
        if os.path.exists(existing) and not args.force:
            print(f"  {class_name}: already split (use --force to redo)")
            continue

        src_dir = os.path.join(args.data_dir, class_name)
        files = [f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg"))]
        random.shuffle(files)

        n = len(files)
        n_train = int(n * args.train_frac)
        n_val = int(n * args.val_frac)

        splits = {
            "train": files[:n_train],
            "val": files[n_train:n_train + n_val],
            "test": files[n_train + n_val:],
        }

        for split, split_files in splits.items():
            dest_dir = os.path.join(args.out_dir, split, class_name)
            os.makedirs(dest_dir, exist_ok=True)
            for f in split_files:
                shutil.copyfile(os.path.join(src_dir, f), os.path.join(dest_dir, f))

        print(f"  {class_name}: {n} images -> train {len(splits['train'])} / "
              f"val {len(splits['val'])} / test {len(splits['test'])}")

    print(f"\nDone. Split data is in {args.out_dir}/")


if __name__ == "__main__":
    main()
