import os
import time
import base64
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
api_token = os.environ["CLOUDFLARE_API_TOKEN"]

model = "@cf/black-forest-labs/flux-1-schnell"

url = (
    "https://api.cloudflare.com/client/v4/"
    f"accounts/{account_id}/ai/run/{model}"
)

headers = {
    "Authorization": f"Bearer {api_token}"
}

payload = {
    "prompt": (
        "Traditional Ethiopian coffee ceremony, "
        "clay jebena, warm morning sunlight, "
        "cinematic composition, realistic photography"
    ),
    "steps": 4
}

start = time.perf_counter()

response = httpx.post(
    url,
    headers=headers,
    json=payload,
    timeout=120
)

response.raise_for_status()

result = response.json()

image = base64.b64decode(
    result["result"]["image"]
)

path = Path("outputs/smoke/keyframe.jpg")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(image)

print(f"Latency: {time.perf_counter() - start:.2f}s")
print(f"Saved to {path}")
