import google.generativeai as genai
from app.core.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("models/gemini-3-flash-preview")

def generate_sql(prompt: str):
    response = model.generate_content(prompt)
    print("SQL Generation Response:", response)
    return response.text
def generate_text(prompt: str):
    response = model.generate_content(prompt)
    
    if not response or not response.text:
        return "Could not generate response"

    return response.text.strip()