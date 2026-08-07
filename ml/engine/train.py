import torch
import torch.nn as nn
import pandas as pd
from models import MFModel
import config
import json
from data_utils import prepare_data_mappings, get_dataloaders
from train_utils import train_one_epoch, evaluate, EarlyStopping

if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"
print(f"Using device: {DEVICE}")

# Data preparation
DATA_PATH = "../../data/Ratings.csv"
df = pd.read_csv(DATA_PATH)

ratings_df, user_to_idx, movie_to_idx = prepare_data_mappings(df)

mappings = {
    'user_to_idx': {int(k): int(v) for k, v in user_to_idx.items()},
    'movie_to_idx': {int(k): int(v) for k, v in user_to_idx.items()},
    'idx_to_movie': {v: k for k, v in movie_to_idx.items()}
}

with open("artifacts/mappings.json", 'w') as f:
    json.dump(mappings, f, indent=2)

train_loader, val_loader, test_loader = get_dataloaders(
                                            ratings_df,
                                            train_batch_size=config.TRAIN_BATCH_SIZE,
                                            eval_batch_size=config.EVAL_BATCH_SIZE)

# Training Loop
model = MFModel(len(user_to_idx), len(movie_to_idx), num_features=config.NUM_FEATURES).to(DEVICE)
model.global_bias.data.fill_(ratings_df['Book-Rating'].mean())
optimizer = torch.optim.AdamW(model.parameters(), lr=config.LEARNING_RATE, weight_decay=config.WEIGHT_DECAY)
criterion = nn.MSELoss()
stopper = EarlyStopping(patience=config.PATIENCE, min_delta=config.MIN_DELTA)
min_val_loss = float('inf')

for epoch in range(1, config.EPOCHS + 1):
    train_loss = train_one_epoch(model=model,
                                 dataloader=train_loader,
                                 optimizer=optimizer,
                                 criterion=criterion,
                                 device=DEVICE)
    val_loss = evaluate(model=model, dataloader=val_loader, criterion=criterion, device=DEVICE)
    print(f"Epoch {epoch:02d} | Train_loss: {train_loss:.4f} | Val_loss: {val_loss:.4f}")

    if val_loss < min_val_loss:
        min_val_loss = val_loss
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'embedding_dim': config.NUM_FEATURES,
            'optimizer_state_dict': optimizer.state_dict(),
            'val_loss': val_loss,
        },
            "artifacts/model.pt"
        )

    stopper(val_loss)
    if stopper.early_stop:
        print(f"Early stopping at epoch {epoch}")
        break

best_model = torch.load("artifacts/model.pt", weights_only=True)
model.load_state_dict(best_model['model_state_dict'])
test_loss = evaluate(model=model, dataloader=test_loader, criterion=criterion, device=DEVICE)
print(f"\nFinal Test Loss (MSE): {test_loss:.4f}")
print(f"\nFinal Root Mean Square Error: {test_loss**(1/2):.4f}")
