import torch
import torch.nn as nn


class MFModel(nn.Module):
    def __init__(self, num_users, num_items, num_features):
        super().__init__()
        self.user_embeddings = nn.Embedding(num_users, num_features)
        self.item_embeddings = nn.Embedding(num_items, num_features)

        self.user_biases = nn.Embedding(num_users, 1)
        self.item_biases = nn.Embedding(num_items, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        nn.init.normal_(self.user_embeddings.weight, std=0.1)
        nn.init.normal_(self.item_embeddings.weight, std=0.1)
        nn.init.zeros_(self.user_biases.weight)
        nn.init.zeros_(self.item_biases.weight)

    def forward(self, user_indices, item_indices):
        user_vec = self.user_embeddings(user_indices)
        item_vec = self.item_embeddings(item_indices)
        user_bias = self.user_biases(user_indices).squeeze() # squeeze to extract one bias
        item_bias = self.item_biases(item_indices).squeeze()

        dot_product = (user_vec * item_vec).sum(dim=1)
        prediction = self.global_bias + user_bias + item_bias + dot_product
        return prediction

    @torch.no_grad()
    def predict_all_scores(self, user_idx):
        """ predict the scores for all items for a given user """
        user_vec = self.user_embeddings(user_idx)
        user_bias = self.user_biases(user_idx).squeeze()
        dot_product = torch.matmul(self.item_embeddings.weight, user_vec)
        all_scores = self.global_bias + user_bias + self.item_biases.weight.squeeze() + dot_product
        return all_scores

    def get_item_vectors(self, item_indices):
        return self.item_embeddings(item_indices)

    @torch.no_grad()
    def predict_from_user_vector(self, user_vector, bias_scale = .5):
        dot_products = torch.matmul(self.item_embeddings.weight, user_vector)
        raw_scores = self.global_bias + (self.item_biases.weight.squeeze() * bias_scale) + dot_products
        bounded_scores = torch.clamp(raw_scores, min=1.0, max=10.0)
        return bounded_scores

