from dotenv import load_dotenv
import os

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")

if openai_key:
    print(" API Key loaded successfully!")
    print(" Your Key:", openai_key)
else:
    print(" API Key not found!")
