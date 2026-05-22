# This file was removed as it is no longer needed. The API logic resides in src/api.py
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
resp = requests.get(url)
print(resp.json())
