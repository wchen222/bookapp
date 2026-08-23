import numpy as np
import torch
import faiss


MODEL_PATH = 'artifacts/model.pt'
BIAS_SCALE = 1.0

model = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
state_dict = model['model_state_dict']

item_embeddings = state_dict["item_embeddings.weight"].detach().cpu().numpy().astype("float32")
item_biases = state_dict["item_biases.weight"].detach().cpu().numpy().astype("float32")

scaled_item_biases = (item_biases * BIAS_SCALE).reshape(-1, 1)

augmented_item_vectors = np.hstack([item_embeddings, scaled_item_biases]).astype("float32")
num_items, d_augmented = augmented_item_vectors.shape

index = faiss.IndexFlatIP(d_augmented)
index.add(augmented_item_vectors)
assert index.ntotal == num_items, "Mismatch between vector and FAISS index count"
faiss.write_index(index, "artifacts/items.index")
np.save("artifacts/item_embeddings.npy", item_embeddings)

