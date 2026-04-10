import os
import google.generativeai as genai
from ai_modules.vlm_processor import YogaVLMProcessor
from ai_modules.rag_processor import RAGProcessor

class YogaAppController:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        
        # Initialize the sub-systems
        self.vlm = YogaVLMProcessor(api_key=self.api_key)
        
        # Assuming your RAG processor takes the index and docs as initialization parameters
        self.rag = RAGProcessor()
        
        # Initialize the final reasoning LLM (Gemini Flash 2.0 is perfect for fast text generation)
        self.llm = genai.GenerativeModel('gemini-2.5-flash')

    def process_user_request(self, image_path, user_query):
        """
        The main pipeline: 
        Handles both Image+Text (VLM -> RAG -> LLM) and Text-Only (RAG -> LLM)
        """
        pose_name = ""
        alignment_notes = ""
        
        # --- STEP 1: Vision Processing (Only if an image is provided) ---
        if image_path:
            print("1. Processing Image with VLM...")
            pose_data = self.vlm.identify_pose(image_path)
            
            if "error" in pose_data:
                return f"Sorry, I had trouble analyzing the image: {pose_data['error']}"
                
            pose_name = pose_data.get("pose_name", "Unknown Pose")
            alignment_notes = pose_data.get("alignment_notes", "")
            print(f"-> Identified Pose: {pose_name}")
            
            search_query = f"{pose_name}. {user_query}"
        else:
            print("1. No image provided. Processing text-only query...")
            search_query = user_query

        # --- STEP 2: RAG Retrieval ---
        print("2. Retrieving Context from Knowledge Base...")
        retrieved_context = self.rag.retrieve(search_query, top_k=3) 

        # --- STEP 3: Final Answer Generation ---
        print("3. Generating Final Personalized Response...")
        final_prompt = self._build_final_prompt(pose_name, alignment_notes, user_query, retrieved_context)
        
        response = self.llm.generate_content(final_prompt)
        return response.text

    def _build_final_prompt(self, pose_name, alignment_notes, user_query, context):
        """
        Constructs a highly specific prompt, conditionally including image data.
        """
        # Only inject image data into the prompt if an image was actually analyzed
        image_context = ""
        if pose_name:
            image_context = f"""
            [IMAGE ANALYSIS DATA]
            Identified Pose: {pose_name}
            """
            
        return f"""
        You are an expert, empathetic Yoga Instructor AI.
        
        The user has asked a question and may or may not have uploaded an image.
        {image_context}
        
        [USER QUERY]
        "{user_query}"
        
        [RETRIEVED KNOWLEDGE BASE CONTEXT]
        {context}
        
        INSTRUCTIONS:
        1. Answer the user's query clearly and concisely.
        2. ONLY use the facts provided in the [RETRIEVED KNOWLEDGE BASE CONTEXT]. Do not invent health benefits or medical advice.
        3. If the user provided an image (see IMAGE ANALYSIS DATA), tailor your advice to that specific pose.
        4. Structure your response with clear headings or bullet points for readability.
        """

# --- Example Usage ---
if __name__ == "__main__":
    # Ensure your GEMINI_API_KEY is set in your environment variables
    controller = YogaAppController()
    
    test_image = "path/to/user_uploaded_yoga_image.jpg"
    test_query = "Is this pose good for back pain, and what are the instructions?"
    
    final_answer = controller.process_user_request(test_image, test_query)
    
    print("\n=== FINAL AI RESPONSE ===")
    print(final_answer)
