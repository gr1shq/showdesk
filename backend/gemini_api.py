import requests
import json
import base64
import os
from typing import Optional

class GeminiAPI:
    """
    Direct REST API calls to Gemini
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        self.model = "gemini-3-flash-preview"
        
    def generate_text(self, prompt: str) -> str:
        """
        Simple text generation
        """
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract text from response
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def generate_with_image(self, prompt: str, image_base64: str) -> str:
        """
        Generate with text + image (multimodal)
        This is the CORE of SHOWDESK - screen analysis!
        """
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        # Remove data URL prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            }]
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def detect_subject(self, content: str) -> dict:
        """
        Detect what subject is being taught
        """
        prompt = f"""
Analyze this educational content and respond with ONLY valid JSON:

{{
    "subject": "one of: coding, history, science, math, language, art, business, other",
    "topic": "specific topic being taught",
    "level": "beginner, intermediate, or advanced",
    "concepts": ["concept1", "concept2", "concept3"]
}}

Content to analyze:
{content[:2000]}

Remember: Response must be ONLY the JSON object, nothing else.
"""
        
        response = self.generate_text(prompt)
        
        # Clean up response and parse JSON
        try:
            # Remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('```')[1]
                if cleaned.startswith('json'):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        # except:
        #     # Fallback if parsing fails
        #     return {
        #         "subject": "unknown",
        #         "topic": "Unable to detect",
        #         "level": "unknown",
        #         "concepts": []
        #     }
        except Exception as e:
            # This will print the actual reason it failed in your terminal
            print(f"DEBUG: Parsing failed. Gemini actually said: {response}")
            return {
                "subject": "unknown",
                "topic": str(e),
                "level": "unknown",
                "concepts": []
            }

# TEST IT NOW
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    gemini = GeminiAPI()
    
    print("=" * 50)
    print("TEST 1: Simple Text Generation")
    print("=" * 50)
    result = gemini.generate_text("Explain what a Python function is in one sentence.")
    print(result)
    print()
    
    print("=" * 50)
    print("TEST 2: Subject Detection")
    print("=" * 50)
    sample_content = """
    In this tutorial, we'll learn about React hooks. 
    Hooks are functions that let you use state and other React features 
    in functional components. We'll cover useState and useEffect.
    """
    subject = gemini.detect_subject(sample_content)
    print(json.dumps(subject, indent=2))
    print()
    
    print("✅ If you see results above, Gemini API is working!")