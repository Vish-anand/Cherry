import time
import os
from dotenv import load_dotenv

load_dotenv()

print("AWS_BEARER_TOKEN_BEDROCK:", repr(os.getenv("AWS_BEARER_TOKEN_BEDROCK")[:20] + "..."))
print("AWS_REGION:", repr(os.getenv("AWS_REGION")))
print("AWS_BEDROCK_MODEL:", repr(os.getenv("AWS_BEDROCK_MODEL")))

from agent.llm import call_llm

start = time.time()
try:
    print("Calling AWS Bedrock...")
    response = call_llm("hi, respond with hello")
    print("Response:", response)
except Exception as e:
    print("Error during Bedrock call:", e)
print("Time taken:", time.time() - start)
