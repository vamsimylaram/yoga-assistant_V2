import os
# We only need the retrieval utilities now!
from utils.rag_utility import load_rag_assets, retrieve_documents 

# Set up asset paths relative to the backend directory
# This assumes rag_processor.py is in backend/ai_modules/ and data is in backend/data/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_PATH = os.path.join(DATA_DIR, "yoga_docs.pkl")
INDEX_PATH = os.path.join(DATA_DIR, "yoga_index.faiss")

class RAGProcessor:
    def __init__(self):
        self.is_ready = False
        self.embedder = None
        self.index = None
        self.docs = None

        print("Loading RAG Knowledge Base...")
        try:
            # 1. Load RAG Assets (Embedder Model, FAISS Index, Pickled Docs)
            model, index, docs = load_rag_assets(INDEX_PATH, DOCS_PATH)
            
            if index is None or docs is None or model is None:
                raise Exception("RAG index, documents, or embedder failed to load.")
            
            self.embedder = model
            self.index = index
            self.docs = docs
            self.is_ready = True
            
            print("✅ RAG Processor fully loaded (Text Database ready).")
            
        except Exception as e:
            print(f"❌ RAGProcessor: Failed to load RAG assets. {e}")
            
    def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        Takes a text query (like the pose name + user question), 
        searches the FAISS index, and returns a string of relevant context.
        """
        if not self.is_ready:
            return "Warning: Knowledge base is offline."

        try:
            # Call your utility function to get the list of matching documents
            retrieved_docs_list = retrieve_documents(query, self.embedder, self.index, self.docs, k=top_k)
            
            if not retrieved_docs_list:
                return "No specific information found in the knowledge base."
            
            # Combine the list of documents into a single string for the final LLM prompt
            context_string = "\n\n".join([str(doc) for doc in retrieved_docs_list])
            return context_string

        except Exception as e:
            print(f"❌ Error during RAG retrieval: {e}")
            return "An error occurred while searching the knowledge base."

if __name__ == '__main__':
    print("This file is intended to be imported as a module.")