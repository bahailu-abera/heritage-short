import os
import time
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

model = "gemini-3.5-flash-lite"
prompt = "Describe an Ethiopian coffee ceremony in one sentence."

start = time.perf_counter()

response = client.models.generate_content(
    model=model,
    contents=prompt
)

latency = time.perf_counter() - start

print(response.text)
print(f"Latency: {latency:.2f} seconds")

record = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "stage": "smoke_test",
    "provider": "google",
    "model": model,
    "parameters": {
        "prompt": prompt
    },
    "seed": None,
    "latency_seconds": round(latency, 3),
    "cost_usd": None,
    "status": "success"
}

with open("runs.jsonl", "a") as file:
    file.write(json.dumps(record) + "\n")
