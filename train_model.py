# train_model.py — runs DistilBERT fine-tuning
import os
from models.training.trainer import TaskTrainer

def main():
    print("=" * 60)
    print("QUORUM — Task Detection Model Training")
    print("=" * 60)

    # Paths
    data_path = os.path.join("models", "data", "task_dataset.json")
    checkpoint_dir = os.path.join("models", "checkpoints", "task_v2")

    # Initialise trainer
    trainer = TaskTrainer(config={
        "learning_rate": 2e-5,
        "epochs": 10,
        "batch_size": 8,
        "val_split": 0.2,
        "max_length": 128,
    })

    # Run training
    print(f"\nData:       {data_path}")
    print(f"Checkpoint: {checkpoint_dir}")
    print(f"Device:     {trainer.device}")
    print(f"{'─' * 60}")

    history = trainer.train(data_path, checkpoint_dir)

    # Print training summary
    print(f"\n{'─' * 60}")
    print("TRAINING HISTORY")
    print(f"{'─' * 60}")
    print(f"{'Epoch':<8}{'Train Loss':<15}{'Val Loss':<15}{'Val Acc':<10}")
    print(f"{'─' * 48}")

    for i in range(len(history["train_loss"])):
        print(
            f"{i + 1:<8}"
            f"{history['train_loss'][i]:<15}"
            f"{history['val_loss'][i]:<15}"
            f"{history['val_accuracy'][i]:<10}"
        )

    print(f"\n{'=' * 60}")
    print(f"Model saved to: {checkpoint_dir}")
    print("Screenshot this output for writeup evidence.")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
