import torch
import json
import pandas as pd
import ml.engine.config as config
from ml.engine.models import MFModel


def _book_name(df, item_id):
    return df.loc[df['ISBN'] == item_id, 'Book-Title'].values[0]

def _format_top_k(
    all_scores, top_k, mappings
):
    k = min(top_k, len(all_scores))
    top_scores, top_indices = torch.topk(all_scores, k=k)
    recommendations = [(
            mappings['idx_to_item'][str(idx.item())],
            score.item())
        for score, idx in zip(top_scores, top_indices)]
    return recommendations

def _calculate_item_weight(rating):
    if rating is None or rating == 0:
        return 2.0  # implicit weight of 2.0
    return float(rating) - 5.0 # midpoint so 0 centered


def load_model():
    with open("ml/engine/artifacts/mappings.json", "r") as f:
        mappings = json.load(f)

    num_users = len(mappings['user_to_idx'])
    num_items = len(mappings['item_to_idx'])
    model_metadata = torch.load("ml/engine/artifacts/model.pt", weights_only=True)
    loaded_model = MFModel(num_users=num_users, num_items=num_items, num_features=config.NUM_FEATURES)
    loaded_model.load_state_dict(model_metadata['model_state_dict'])
    loaded_model.eval()
    return loaded_model, mappings


@torch.no_grad()
def cold_start_top_k(
        user_history: list[tuple[str, float]],  # tuples of structure (ISBN, rating)
        model: torch.nn.Module,
        mappings: dict,
        top_k: int = 10,
):
    model.eval()
    valid_items = [
        (mappings['item_to_idx'][str(isbn)], _calculate_item_weight(rating))
        for isbn, rating in user_history
        if str(isbn) in mappings['item_to_idx']
    ]

    if not valid_items:
        # recommend the general popular books, scores = deviation of item bias from global bias
        all_scores = model.global_bias + model.item_biases.weight.squeeze()
        seen_indices = []
    else:
        seen_indices, weights = zip(*valid_items)
        indices_t = torch.tensor(seen_indices, dtype=torch.long)
        weights_t = torch.tensor(weights, dtype=torch.float32).unsqueeze(1)

        item_vectors = model.get_item_vectors(indices_t)
        amp = 2.0
        u_temp = amp * ((item_vectors * weights_t).sum(dim=0) / (torch.abs(weights_t).sum() + 1e-8))
        all_scores = model.predict_from_user_vector(u_temp)

    if seen_indices:
        # move them to the bottom of the list when sorting
        all_scores[torch.tensor(seen_indices, dtype=torch.long)] = float('-inf')

    return _format_top_k(all_scores, top_k, mappings)

def add_titles(recommendations):
    res = []
    book_df = pd.read_csv("../../data/books_clean.csv")
    book_dict = dict(zip(book_df['ISBN'], book_df['Book-Title']))
    for item in recommendations:
        isbn = str(item[0])
        title = book_dict.get(isbn, "Unknown Title")
        res.append((isbn, title, item[1]))
    return res