import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Load env from backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

api_key = os.environ.get("GEMINI_API_KEY")
print(f"Testing API Key: {api_key[:5]}...{api_key[-5:]}")

if not api_key:
    print("Error: GEMINI_API_KEY not found in environment!")
    exit(1)

genai.configure(api_key=api_key)

try:
    print("Discovering best available model...")
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Priority list
    preferred = ['models/gemini-1.5-flash', 'models/gemini-flash-latest', 'models/gemini-1.5-pro', 'models/gemini-pro']
    model_name = "gemini-1.5-flash"
    for p in preferred:
        if p in models:
            model_name = p
            break
    
    print(f"Selected Model: {model_name}")
    print(f"Attempting to connect to {model_name}...")
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello! Say 'Connection Successful' if you can read this.")
    print(f"AI Response: {response.text}")
    print("\nSUCCESS! Your AI Assistant is now ready to use.")
except Exception as e:
    print(f"Connection Failed: {str(e)}")
