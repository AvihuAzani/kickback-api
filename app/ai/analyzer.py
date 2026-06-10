import base64
import json
import asyncio
from typing import Optional
from google import genai
from google.genai import types
from ..config import settings

SYSTEM_PROMPT = """You are an AI football referee assistant analyzing real-time video frames from a neighborhood football game.

Your job is to detect the following events and report them immediately:
- GOAL: Ball fully crosses the goal line
- FOUL: Illegal tackle, push, trip, or dangerous play
- HANDBALL: Ball touches a player's hand/arm (excluding goalkeeper in their area)
- YELLOW_CARD: Serious foul or unsporting behavior
- RED_CARD: Violent conduct or second yellow

Respond ONLY with a JSON object in this exact format (no markdown, no extra text):
{
  "event": "GOAL" | "FOUL" | "HANDBALL" | "YELLOW_CARD" | "RED_CARD" | "NONE",
  "confidence": 0.0-1.0,
  "description": "Brief description in Hebrew",
  "team": "A" | "B" | null,
  "player": "description of player if visible" | null
}

If nothing notable is happening, return {"event": "NONE", "confidence": 1.0, "description": "", "team": null, "player": null}

Be conservative — only report events you are highly confident about (confidence > 0.8).
Context: This is a neighborhood street football game, not professional."""


class FootballAnalyzer:
    def __init__(self):
        self.client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self):
        if settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key)

    async def analyze_frame(
        self,
        frame_b64: str,
        camera_position: str,
        team_a_name: str,
        team_b_name: str,
        attack_direction: str,
    ) -> dict:
        """Analyze a single frame and return detected event."""
        if not self.client:
            return {"event": "NONE", "confidence": 1.0, "description": "AI not configured", "team": None, "player": None}

        context = f"Camera position: {camera_position}. {team_a_name} attacks {attack_direction}. {team_b_name} attacks the opposite direction."

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.0-flash",
                contents=[
                    types.Content(parts=[
                        types.Part(text=f"{SYSTEM_PROMPT}\n\n{context}"),
                        types.Part(inline_data=types.Blob(
                            mime_type="image/jpeg",
                            data=base64.b64decode(frame_b64),
                        )),
                    ])
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )
            text = response.text.strip()
            # Strip markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except json.JSONDecodeError:
            return {"event": "NONE", "confidence": 0.0, "description": "Parse error", "team": None, "player": None}
        except Exception as e:
            return {"event": "NONE", "confidence": 0.0, "description": str(e), "team": None, "player": None}


analyzer = FootballAnalyzer()
