import os
import time
import base64
import json

from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={"api_version": "v1beta"}
)

model = "gemini-3.8-flash-tts"

text = "ኢትዮጵያ የብዙ ታሪኮችና ባህሎች መገኛ ናት።"

voice = "Kore"
style = "Warm, calm and natural storytelling voice"

start = time.perf_counter()

record = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "stage": "smoke_test_tts",
    "provider": "google",
    "model": model,
    "parameters": {
        "text": text,
        "voice": voice,
        "style": style
    },
    "seed": None,
    "cost_usd": None
}

try:
    interaction = client.interactions.create(
        model=model,
        input=[
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [
                            {
                                "type": "speech_metadata",
                                "style": style
                            }
                        ]
                    }
                ]
            }
        ],
        response_format={
            "type": "audio"
        },
        generation_config={
            "speech_config": [
                {
                    "voice": voice
                }
            ]
        }
    )

    audio = base64.b64decode(
        interaction.output_audio.data
    )

    path = Path("outputs/smoke/narration.wav")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)

    record["status"] = "success"

    print(f"Saved to: {path}")

except Exception as error:
    record["status"] = "failed"
    record["error"] = str(error)
    raise

finally:
    latency = time.perf_counter() - start

    record["latency_seconds"] = round(latency, 3)

    with open("runs.jsonl", "a") as file:
        file.write(json.dumps(record) + "\n")

    print(f"Latency: {latency:.2f} seconds")
