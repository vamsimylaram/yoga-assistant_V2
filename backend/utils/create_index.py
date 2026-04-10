import faiss
import pickle
import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer

# --- Configuration ---
EMBED_MODEL = "all-mpnet-base-v2"
# The source of your RAG data
SOURCE_JSON = "/home/user/majorPrj/yogaAssistant/yoga_knowledge_base_intermediate.json" 
# Output paths (must match the paths used in rag_processor.py)
OUTPUT_MODELS_DIR = "models"
OUTPUT_DOCS_PKL = os.path.join(OUTPUT_MODELS_DIR, "yoga_docs.pkl")
OUTPUT_FAISS = os.path.join(OUTPUT_MODELS_DIR, "yoga_index.faiss")

def build_index():
    print("--- Starting FAISS Index and Document Creation ---")
    
    # 1. Load Source Data and build the corpus
    try:
        with open(SOURCE_JSON, 'r') as f:
            yoga_data = json.load(f)
        
        # Build document list and text list for embedding
        docs = []
        texts_to_embed = []
        for entry in yoga_data:
            # This is the text the RAG will use for retrieval
            text = (
                f"{entry['pose_name']} ({entry['sanskrit_name']}): "
                f"Benefits: {', '.join(entry['benefits_list'])}. "
                f"Instructions: {entry['instructions']}"
            )
            # Add full document (metadata) to docs list
            docs.append(entry) 
            # Add text for embedding
            texts_to_embed.append(text)

        print(f"✅ Loaded {len(docs)} documents from {SOURCE_JSON}.")
        
    except Exception as e:
        print(f"❌ ERROR: Could not load or parse {SOURCE_JSON}. Please ensure it is present and valid JSON. Error: {e}")
        return

    # 2. Load Embedder
    try:
        model = SentenceTransformer(EMBED_MODEL)
        print(f"✅ SentenceTransformer ({EMBED_MODEL}) loaded.")
    except Exception as e:
        print(f"❌ ERROR: Could not initialize SentenceTransformer. Check your environment/installation. Error: {e}")
        return

    # 3. Create Embeddings
    print(f"Creating embeddings for {len(texts_to_embed)} documents...")
    embeddings = model.encode(texts_to_embed, convert_to_numpy=True)
    embeddings = embeddings.astype('float32') # FAISS requires float32
    print(f"Embeddings shape: {embeddings.shape}")

    # 4. Build and Save FAISS Index
    dimension = embeddings.shape[1]
    # Use a simple IndexFlatL2 for demonstration
    index = faiss.IndexFlatL2(dimension) 
    index.add(embeddings)
    
    faiss.write_index(index, OUTPUT_FAISS)
    print(f"✅ FAISS index saved to {OUTPUT_FAISS}.")

    # 5. Save Documents
    with open(OUTPUT_DOCS_PKL, 'wb') as f:
        pickle.dump(docs, f)
    print(f"✅ Document metadata saved to {OUTPUT_DOCS_PKL}.")

    print("--- Index Creation Complete ---")


if __name__ == "__main__":
    if not os.path.exists(OUTPUT_MODELS_DIR):
        os.makedirs(OUTPUT_MODELS_DIR)
    build_index()
