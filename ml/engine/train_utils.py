import torch

def train_one_epoch(model, dataloader, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    for users, items, ratings in dataloader:
        users, items, ratings = users.to(device), items.to(device), ratings.to(device)
        optimizer.zero_grad()
        predictions = model(users, items).squeeze()
        ratings = ratings.float().squeeze()
        loss = criterion(predictions, ratings)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * len(ratings)
    avg_loss = running_loss / len(dataloader.dataset)
    return avg_loss

def evaluate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    with torch.no_grad():
        for users, items, ratings in dataloader:
            users, items, ratings = users.to(device), items.to(device), ratings.to(device)
            predictions = model(users, items)
            loss = criterion(predictions, ratings)
            running_loss += loss.item() * len(ratings)
    avg_loss = running_loss / len(dataloader.dataset)
    return avg_loss

class EarlyStopping:
    def __init__(self, patience=5, min_delta=0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float('inf')
        self.early_stop = False

    def __call__(self, val_loss):
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
