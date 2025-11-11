import os
import pickle
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


def build_document_corpus(ind_df):
    ids = []
    docs = []

    for _, row in ind_df.iterrows():
        ind_id = row["id"]
        name = str(row["name"])
        unit = str(row.get("unit", ""))
        source_note = str(row.get("sourceNote", ""))
        topics = str(row.get("topics", ""))

        # Extract metadata from indicator ID for better matching
        id_parts = []
        if ".FE" in ind_id:
            id_parts.append("female")
        if ".MA" in ind_id:
            id_parts.append("male")
        if ".ZG" in ind_id:
            id_parts.append("growth rate annual percentage")
        if ".ZS" in ind_id:
            id_parts.append("percentage share")
        if ".CD" in ind_id:
            id_parts.append("current US dollars")
        if ".KD" in ind_id:
            id_parts.append("constant US dollars")
        if ".PP" in ind_id:
            id_parts.append("PPP purchasing power parity")
        if ".PC" in ind_id:
            id_parts.append("per capita")
        if "1524" in ind_id:
            id_parts.append("ages 15-24 youth")
        if "65UP" in ind_id:
            id_parts.append("ages 65 and above elderly")

        metadata = " ".join(id_parts)

        # Build document with weighted fields
        title = f"{name} {unit}".strip()
        doc = f"{title}. {metadata}. {source_note}. Topics: {topics}".strip()

        ids.append(ind_id)
        docs.append(doc)

    return ids, docs


class IndicatorIndex:
    def __init__(self, model_name="all-mpnet-base-v2"):
        self.model_name = model_name
        self.ids = []
        self.docs = []
        self.model = None
        self.index = None
        self.embeddings = None


    def build(self, ind_df):
        self.ids, self.docs = build_document_corpus(ind_df)
        self.model = SentenceTransformer(self.model_name)
        self.embeddings = self.model.encode(self.docs, normalize_embeddings=True, show_progress_bar=True)

        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(self.embeddings.astype('float32'))

    def search(self, query, top_k=30):
        # Expand query with synonyms for better matching
        query_expanded = query

        # Add common synonyms
        if "female" in query.lower():
            query_expanded += " women girls"
        if "male" in query.lower():
            query_expanded += " men boys"
        if "population" in query.lower():
            query_expanded += " people inhabitants"
        if "gdp" in query.lower():
            query_expanded += " gross domestic product economy"
        if "unemployment" in query.lower():
            query_expanded += " jobless without work"
        if "inflation" in query.lower():
            query_expanded += " cpi consumer price index"
        if "65+" in query:
            query_expanded += " ages 65 and above elderly older senior"
        if "15-24" in query:
            query_expanded += " youth young ages 15 to 24"

        query_vec = self.model.encode([query_expanded], normalize_embeddings=True).astype('float32')

        # Fetch more candidates for better filtering
        search_k = min(top_k * 2, len(self.ids))
        distances, indices = self.index.search(query_vec, search_k)

        results = []
        for idx, i in enumerate(indices[0]):
            if idx >= top_k:
                break
            results.append((self.ids[i], float(distances[0][idx])))

        return results

    def save(self, path):
        os.makedirs(path, exist_ok=True)

        metadata = {
            'model_name': self.model_name,
            'ids': self.ids,
            'docs': self.docs
        }

        with open(os.path.join(path, 'metadata.pkl'), 'wb') as f:
            pickle.dump(metadata, f)

        faiss.write_index(self.index, os.path.join(path, 'faiss.index'))
        np.save(os.path.join(path, 'embeddings.npy'), self.embeddings)

    def load(self, path):
        with open(os.path.join(path, 'metadata.pkl'), 'rb') as f:
            metadata = pickle.load(f)

        self.model_name = metadata['model_name']
        self.ids = metadata['ids']
        self.docs = metadata['docs']

        self.model = SentenceTransformer(self.model_name)
        self.index = faiss.read_index(os.path.join(path, 'faiss.index'))
        self.embeddings = np.load(os.path.join(path, 'embeddings.npy'))
