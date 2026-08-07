import torch
from torch.utils.data import TensorDataset, DataLoader, random_split

def prepare_data_mappings(df):
    df.dropna(subset=['User-ID', 'ISBN', 'Book-Rating'])
    df = df[df['Book-Rating'] > 0].copy()
    user_to_idx = {raw_id: idx for idx, raw_id in enumerate(df['User-ID'].unique())}
    item_to_idx = {raw_id: idx for idx, raw_id in enumerate(df['ISBN'].unique())}
    df['user_idx'] = df['User-ID'].map(user_to_idx)
    df['item_idx'] = df['ISBN'].map(item_to_idx)
    return df, user_to_idx, item_to_idx

def get_dataloaders(df, train_batch_size, eval_batch_size):
    dataset = TensorDataset(
        torch.tensor(df['user_idx'].values, dtype=torch.long),
        torch.tensor(df['user_idx'].values, dtype=torch.long),
        torch.tensor(df['Book-Rating'].values, dtype=torch.float32)
    )

    total_len = len(dataset)
    train_size = int(0.8 * total_len)
    val_size = int(0.1 * total_len)
    test_size = total_len - train_size - val_size

    train_dataset, val_dataset, test_dataset = random_split(
        dataset,
        [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_dataset, batch_size=train_batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=eval_batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=eval_batch_size, shuffle=False)

    return train_loader, val_loader, test_loader