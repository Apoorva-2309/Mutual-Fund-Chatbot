"""Test if Groq API key is set and working."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv("GROQ_API_KEY", "")
is_set = bool(key and key != "gsk_your_groq_api_key_here")
print(f"Key set: {is_set}")
if is_set:
    print(f"Key prefix: {key[:10]}...")
else:
    print("Key not set or still placeholder")

# Test LLM service
print("\nTesting LLM service...")
from backend.llm import llm_service

if llm_service is None:
    print("LLM service not initialized")
else:
    print("LLM service initialized successfully")
    chunks = [
        {
            "text": "The expense ratio of HDFC Large Cap Fund Direct Growth is 1.03%.",
            "metadata": {"source_url": "https://groww.in/test"},
        }
    ]
    try:
        answer = llm_service.generate(
            "What is the expense ratio of HDFC Large Cap Fund?",
            chunks,
        )
        print(f"Answer: {answer}")
        print("Result: PASS")
    except Exception as e:
        print(f"Error: {e}")
        print("Result: FAIL")
