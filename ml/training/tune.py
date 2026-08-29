import optuna
import torch
import torch.nn as nn
import pandas as pd
from ml.training.models import MFModel
from ml.training.data_utils import prepare_data_mappings, get_dataloaders
from ml.training.train_utils import train_one_epoch, evaluate

if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
print(device)

raw_ratings_df = pd.read_csv("../../data/Ratings.csv")
raw_books_df = pd.read_csv("../../data/books_clean.csv")


print(raw_ratings_df.shape)

valid_isbns = set(raw_books_df['ISBN'].astype(str).str.strip())

df, user_to_idx, movie_to_idx = prepare_data_mappings(raw_ratings_df, valid_isbns)

train_loader, val_loader, test_loader = get_dataloaders(df, train_batch_size=512, eval_batch_size=1024)

print(df.shape)


def objective(trial):
    num_features = trial.suggest_categorical("num_features", [8, 16, 32])
    lr = trial.suggest_float("lr", 5e-4, 8e-3, log=True)
    weight_decay = trial.suggest_float("weight_decay", 1e-4, 1e-1, log=True)

    model = MFModel(num_users=len(user_to_idx), num_items=len(movie_to_idx), num_features=num_features).to(device)
    model.global_bias.data.fill_(df['Book-Rating'].mean())
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.MSELoss()
    epochs = 15
    lowest_val_loss = float('inf')
    for epoch in range(epochs):
        train_one_epoch(model=model, dataloader=train_loader, optimizer=optimizer, criterion=criterion, device=device)
        val_loss = evaluate(model=model, dataloader=val_loader, criterion=criterion, device=device)
        trial.report(val_loss, epoch)
        if trial.should_prune():
            raise optuna.TrialPruned()
        lowest_val_loss = min(lowest_val_loss, val_loss)
    return lowest_val_loss



study = optuna.create_study(direction="minimize",
                            sampler=optuna.samplers.TPESampler(seed=42),
                            pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=3))
study.optimize(objective, n_trials=30)
print("\nBest Parameters Found:")
print(study.best_params)
print(f"Best Loss: {study.best_value:.4f}")



