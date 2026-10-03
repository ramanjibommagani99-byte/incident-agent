import os; from dotenv import load_dotenv; load_dotenv()
from openai import OpenAI; client = OpenAI()
print(client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-6-astra"), input="Reply with exactly: API connection OK").output_text)
