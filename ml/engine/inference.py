import torch
from models import MFModel
import json
import config
import pandas as pd


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
    if rating is not None:
        return float(rating) - 5.0 # midpoint so 0 centered
    return 2.0 # implicit weight of 2.0

def load_model():
    with open("artifacts/mappings.json", "r") as f:
        mappings = json.load(f)

    num_users = len(mappings['user_to_idx'])
    num_items = len(mappings['item_to_idx'])
    model_metadata = torch.load("artifacts/model.pt", weights_only=True)
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
        amp = 5
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


 # top k for cold start

print("\n---Cold Start Top K Recommendations---")
model, mappings = load_model()

fantasy = [ # the hobbit ('1594130051', 10.0),
        ('0345339703', 10.0), # lotr 1
        ('0345339711', 10.0), # lotr 2
        ]

dystopian = [
        ('0451524934', 10.0), # 1984
        ('0451522303', 10.0), # Animal Farm
        ('0060929871', 10.0), # Brave New World
        ]
empty = []

dystopian_large = [
    # Primary Canonical Seeds
    ('0451524934', 10.0), # 1984 - George Orwell
    ('0451522303', 10.0), # Animal Farm - George Orwell
    ('0060929871', 10.0), # Brave New World - Aldous Huxley
    ('0307281270', 10.0), # Fahrenheit 451 - Ray Bradbury
    ('038549081X', 10.0), # The Handmaid's Tale - Margaret Atwood
    ('0393312836', 10.0), # A Clockwork Orange - Anthony Burgess
    ('0441569560', 10.0), # Neuromancer - William Gibson
    ('0553283685', 10.0), # Snow Crash - Neal Stephenson
    ('0345313860', 10.0), # The Running Man - Stephen King (Richard Bachman)
    ('0451167317', 10.0), # The Long Walk - Stephen King (Richard Bachman)

    # Secondary & Adjacent Dystopian/Speculative Seeds
    ('0385490828', 10.0), # Oryx and Crake - Margaret Atwood
    ('0156027321', 10.0), # Lord of the Flies - William Golding
    ('0553293354', 10.0), # Foundation - Isaac Asimov
    ('0060850524', 10.0), # The Doors of Perception - Aldous Huxley
    ('0064400558', 10.0), # The Giver - Lois Lowry
]

fantasy_scifi_seeds = [
    ('0345339703', 10.0), # The Fellowship of the Ring - J.R.R. Tolkien
    ('0345339711', 10.0), # The Two Towers - J.R.R. Tolkien
    ('0345339738', 10.0), # The Return of the King - J.R.R. Tolkien
    ('0345339681', 10.0), # The Hobbit - J.R.R. Tolkien
    ('0441172717', 10.0), # Dune - Frank Herbert
    ('0812550706', 10.0), # Ender's Game - Orson Scott Card
    ('0812511816', 10.0), # The Eye of the World (Wheel of Time) - Robert Jordan
    ('0765346524', 10.0), # Wizard's First Rule - Terry Goodkind
]

thriller_seeds = [
    ('0440211727', 10.0), # The Firm - John Grisham
    ('0440214041', 10.0), # The Pelican Brief - John Grisham
    ('044022165X', 10.0), # The Runaway Jury - John Grisham
    ('0 Warner / 0446602612', 10.0), # Along Came a Spider - James Patterson (or standard 0446602612)
    ('0446601241', 10.0), # Kiss the Girls - James Patterson
    ('038542471X', 10.0), # The Firm / General Thriller anchor
]


cozy_mystery_seeds = [
    ('0553560247', 10.0), # Dying for Chocolate - Diane Mott Davidson
    ('0553284320', 10.0), # Catering for Murder - Diane Mott Davidson
    ('0553572822', 10.0), # The Main Corpse - Diane Mott Davidson
    ('0451180291', 10.0), # Candy Cane Murder / Cozy Mystery
]




new_recommendations = cold_start_top_k(user_history=cozy_mystery_seeds,
                                           model=model,
                                           mappings=mappings,
                                           top_k=20,
)

formatted_recommendations = add_titles(new_recommendations)

for r in formatted_recommendations:
        print(r)