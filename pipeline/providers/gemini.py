
import base64
import io
import wave

from pathlib import Path

from google import genai

from pipeline.core.config import settings, require_env
from pipeline.core.logger import logger
from pipeline.core.retry import run_with_retry


class GeminiProvider:
    VERSION = "1.0"

    def __init__(self):
        self.client = genai.Client(
        api_key=require_env("GEMINI_API_KEY"),
        http_options= {
            "api_version": settings.gemini_api_version,
            "timeout": int(settings.request_timeout * 1000),
            },
        )

        self.tts_model = settings.gemini_tts_model

    def generate_speech(
        self,
        *,
        text: str,
        voice: str,
        style: str,
        output_path: Path,
        shot_id: str,
    ) -> Path:

        if not text.strip():
            raise ValueError("Narration text cannot be empty")

        parameters = {
            "text": text,
            "voice": voice,
            "style": style,
            "api_version": settings.gemini_api_version,
            "response_format": "audio/wav",
        }

        def generate(attempt: int) -> Path:
            with logger.model_call(
                stage="narration",
                provider="google",
                model=self.tts_model,
                parameters=parameters,
                seed=None,
                shot_id=shot_id,
                attempt=attempt,
            ) as record:

                interaction = self.client.interactions.create(
                    model=self.tts_model,
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
                                            "style": style,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                    response_format={
                        "type": "audio",
                        "mime_type": "audio/wav",
                    },
                    generation_config={
                        "speech_config": [
                            {"voice": voice}
                        ]
                    },
                )

                output_audio = interaction.output_audio

                if not output_audio or not output_audio.data:
                    raise RuntimeError(
                        f"{shot_id}: Gemini returned no audio"
                    )

                audio = base64.b64decode(
                    output_audio.data
                )

                # Validate the WAV before publishing it.
                try:
                    with wave.open(
                        io.BytesIO(audio), "rb"
                    ) as wav:
                        frames = wav.getnframes()
                        sample_rate = wav.getframerate()

                        if frames == 0:
                            raise ValueError("Empty audio")

                        duration = frames / sample_rate

                except (wave.Error, EOFError) as error:
                    raise RuntimeError(
                        f"{shot_id}: Invalid WAV response"
                    ) from error

                output_path.parent.mkdir(
                    parents=True, exist_ok=True
                )

                temporary_path = output_path.with_suffix(
                    ".tmp"
                )

                temporary_path.write_bytes(audio)
                temporary_path.replace(output_path)

                record["output_path"] = str(output_path)
                record["audio_duration_seconds"] = duration
                record["interaction_id"] = getattr(
                    interaction, "id", None
                )

                return output_path

        return run_with_retry(generate)
