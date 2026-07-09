from pipeline import Pipeline

if __name__ == "__main__":
    DATA_DIR = "data_split"
    CHECKPOINT_DIR = "checkpoints"

    pipeline = Pipeline(
        data_dir=DATA_DIR,
        checkpoint_dir=CHECKPOINT_DIR,
        epochs=200,
        lr=0.001,
        batch_size=16,
        max_hours=8.0,
    )

    print("\nTraining\n")
    pipeline.train()

    print("\nEvaluating on test\n")
    pipeline.test()