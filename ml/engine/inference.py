import numpy as np


def _calculate_item_weight(rating):
    if rating is None or rating == 0:
        return 2.0  # implicit weight of 2.0
    return float(rating) - 5.0  # midpoint so 0 centered


def faiss_cold_top_k(
        user_history: list[tuple[str, float]],
        item_embeddings,
        faiss_index,
        mappings: dict,
        top_k: int
):
    valid_items = [
        (mappings['item_to_idx'][str(isbn)], _calculate_item_weight(rating))
        for isbn, rating in user_history
        if str(isbn) in mappings['item_to_idx']
    ]
    if not valid_items:
        seen_indices = []
        u_temp = np.zeros(item_embeddings.shape[1], dtype=np.float32)
    else:
        seen_indices, weights = zip(*valid_items)
        idx_arr = np.array(seen_indices, dtype=np.int64)
        w_arr = np.array(weights, dtype=np.float32)[:, np.newaxis]

        amp = 2.0
        weighted_sum = (item_embeddings[idx_arr] * w_arr).sum(axis=0)
        u_temp = amp * (weighted_sum / (np.abs(w_arr).sum() + 1e-8))

    query_vec = np.hstack([u_temp, np.array([1.0], dtype=np.float32)]).astype("float32").reshape(1, -1)
    query_count = min(top_k + len(seen_indices), faiss_index.ntotal)  # pad by count of user_history

    distances, indices = faiss_index.search(query_vec, query_count)

    #  filter out items in user history
    recommendations = []
    for idx in indices[0]:
        if idx in seen_indices or idx == -1:
            continue
        recommendations.append(mappings["idx_to_item"][str(idx)])  # append the isbn
        if len(recommendations) == top_k:
            break

    return recommendations
