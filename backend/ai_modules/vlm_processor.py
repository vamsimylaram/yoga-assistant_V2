import google.generativeai as genai
import json
from PIL import Image
import os

class YogaVLMProcessor:
    def __init__(self, api_key=None):
        # Initialize with your API key. You can pass it directly or use an environment variable.
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API Key is missing. Please set GEMINI_API_KEY.")
        
        genai.configure(api_key=self.api_key)
        
        # Using the flash model for low latency and high multimodal performance
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def identify_pose(self, image_path):
        """
        Takes an image path (2D or 3D), analyzes it using Gemini, 
        and returns a structured JSON dictionary with the pose details.
        """
        try:
            image = Image.open(image_path)
        except Exception as e:
            return {"error": f"Failed to load image: {str(e)}"}

        # We use a strict prompt to ensure the output is pure JSON
        # so it seamlessly feeds into your RAG pipeline.
        prompt = """
        You are an expert yoga instructor and computer vision assistant. 
        Analyze the provided image (which may be a 2D photograph or a 3D/CGI render) and identify the yoga pose.
        
        Return ONLY a valid JSON object with no markdown formatting or extra text. Use this exact schema:
        {
            "pose_name": "Standard English name of the pose",
            "sanskrit_name": "Sanskrit name if known, else null",
            "is_3d_render": true/false based on image style,
            "alignment_notes": "Brief observation of the posture in the image"
        }
        """

        try:
            response = self.model.generate_content([prompt, image])
            
            # Clean up the response just in case the model adds markdown code blocks
            clean_text = response.text.strip().removeprefix('```json').removesuffix('```').strip()
            
            pose_data = json.loads(clean_text)
            return pose_data
            
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON from VLM", "raw_response": response.text}
        except Exception as e:
            return {"error": f"VLM API Error: {str(e)}"}

# --- Example Usage ---
if __name__ == "__main__":
    vlm = YogaVLMProcessor(api_key="YOUR_API_KEY_HERE")
    
    # Test it with a dummy image path
    # result = vlm.identify_pose("test_yoga_image.jpg")
    # print(result['pose_name']) # This goes straight to your FAISS RAG!