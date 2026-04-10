import faiss
import pickle
import json
import os
from sentence_transformers import SentenceTransformer
from google.genai import Client, types 
import torch # We need this for the image model loading too

# --- Configuration ---
EMBED_MODEL = "all-mpnet-base-v2"
GEMINI_MODEL = "gemini-2.5-flash"

# --- Initialization & Loading ---\
# CRITICAL FIX: Accepts faiss_path and docs_path arguments
def load_rag_assets(faiss_path: str, docs_path: str):
    """Loads the Sentence Transformer, FAISS index, and Document dictionary using the provided absolute paths."""
    
    # 1. Load Sentence Transformer
    try:
        model = SentenceTransformer(EMBED_MODEL)
        print("✅ SentenceTransformer embedder loaded.")
    except Exception as e:
        print(f"❌ ERROR: Could not initialize SentenceTransformer. Error: {e}")
        return None, None, None

    # 2. Load FAISS Index
    # CRITICAL FIX: Use the passed faiss_path argument
    try:
        # This will now correctly look for the FAISS file at the faiss_path
        index = faiss.read_index(faiss_path)
    except Exception as e:
        # Crucial for debugging: we use the provided path in the error message
        print(f"❌ ERROR: Could not load FAISS index from {faiss_path}. Error: {e}")
        return model, None, None

    # 3. Load Document Dictionary
    # CRITICAL FIX: Use the passed docs_path argument
    try:
        with open(docs_path, 'rb') as f:
            docs = pickle.load(f)
        
        # We re-create the 'text' key in each doc here for RAG generation
        for doc in docs:
            # Re-create the text field as it's needed for retrieval and generation
            doc["text"] = (
                f"{doc['pose_name']} ({doc['sanskrit_name']}): "
                f"Benefits: {', '.join(doc['benefits_list'])}. "
                f"Instructions: {doc['instructions']}"
            )

    except Exception as e:
        print(f"❌ ERROR: Could not load documents from {docs_path}. Error: {e}")
        # If docs fail to load, we still return model and index if available
        return model, index, None 
    
    # This function now returns a tuple (model, index, docs)
    return model, index, docs

# --- Retrieval Function ---\
def retrieve_documents(query, model, index, docs, k=5):
    """Searches the FAISS index to find the top k most relevant documents."""
    
    if model is None or index is None or docs is None:
        print("Retrieval components not loaded.")
        return []

    # 1. Generate Query Embedding
    # Using .cpu().numpy() to ensure compatibility with FAISS
    query_vector = model.encode([query], convert_to_tensor=True).cpu().numpy()
    
    # 2. Search FAISS Index
    distances, indices = index.search(query_vector, k)
    
    # 3. Retrieve Documents
    retrieved_docs = []
    for doc_id in indices[0]:
        if doc_id >= 0 and doc_id < len(docs):
            # We append the document which contains the 'text' field
            retrieved_docs.append(docs[doc_id])
    
    return retrieved_docs

# --- Generation Function ---\
# CRITICAL FIX: Added optional pose_name argument to match the call in rag_processor.py
def generate_answer(query: str, retrieved_docs: list, client: Client, pose_name: str = None): 
    """Calls the Gemini API to synthesize an answer from retrieved context."""
    if client is None:
        return "Gemini client not available to generate an answer. Check API setup."

    # Build context safely from retrieved docs
    context = ""
    if retrieved_docs and len(retrieved_docs) > 0:
        context = "\n\n".join([d.get("text", "") for d in retrieved_docs if d.get("text")])
    else:
        context = "No relevant yoga documents were retrieved."

    # Create system prompt
    if pose_name:
        system_prompt_text = (
            f"You are a supportive, knowledgeable yoga instructor. The user uploaded a photo "
            f"classified as {pose_name}. Use the provided context to offer personalized guidance "
            f"based on their query. Always start your response by confirming the pose name."
        )
    else:
        system_prompt_text = (
            "You are a helpful and knowledgeable yoga assistant. Use the following context, which provides "
            "pose details and instructions, to answer the user's request for a pose recommendation or information. "
            "Be concise and professional."
        )

    prompt = f"Context:\n{context}\n\nUser: {query}"

    # --- Call Gemini --- #
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt_text,
                max_output_tokens=300
            )
        )

        # ✅ Defensive fix: handle empty or missing responses
        if not resp or not getattr(resp, "text", None):
            return "I couldn't generate an appropriate response at this time. Please try rephrasing your question."

        return str(resp.text).strip()

    except Exception as e:
        return f"Error calling Gemini API: {e}"
