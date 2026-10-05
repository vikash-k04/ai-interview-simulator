import asyncio
import json
import logging
from typing import Dict, Any
import httpx
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiRequestPacer:
    """Space Gemini requests evenly to stay under the configured per-minute limit."""

    def __init__(self, requests_per_minute: int):
        self.interval_seconds = 60.0 / requests_per_minute
        self.next_request_at = 0.0
        self.lock = asyncio.Lock()

    async def wait_turn(self) -> None:
        loop = asyncio.get_running_loop()
        async with self.lock:
            now = loop.time()
            wait_seconds = max(0.0, self.next_request_at - now)
            if wait_seconds > 0:
                logger.info("Gemini request queued for %.1f second(s) to respect the RPM limit.", wait_seconds)
                await asyncio.sleep(wait_seconds)
            self.next_request_at = loop.time() + self.interval_seconds

def clean_json_response(raw_text: str) -> str:
    """Strips markdown code blocks, backticks, and extraneous whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-3.8-flash"
        self.fallback_model = settings.GEMINI_FALLBACK_MODEL.strip()
        self.request_pacer = GeminiRequestPacer(settings.GEMINI_RPM_LIMIT)

    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        try:
            return await self._generate_with_model(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
        except RuntimeError as primary_error:
            # Switch only for temporary provider overload. Quota/billing errors
            # remain visible instead of attempting to route around project limits.
            if (
                "HTTP 503" not in str(primary_error)
                or not self.fallback_model
                or self.fallback_model == self.model
            ):
                raise
            logger.warning(
                "Primary Gemini model is unavailable; retrying this request with configured fallback model %s.",
                self.fallback_model,
            )
            return await self._generate_with_model(
                model=self.fallback_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

    async def _generate_with_model(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Executes a prompt to Google Gemini with JSON enforcement.
        Makes a real Gemini API request; it never fabricates AI results.
        """
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Real Gemini API is required for production.")

        # Use one asynchronous REST request path to avoid duplicate API calls.
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"responseMimeType": "application/json"},
        }
        if not model.startswith("gemini-3."):
            payload["generationConfig"]["temperature"] = temperature

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                for attempt in range(2):
                    try:
                        await self.request_pacer.wait_turn()
                        res = await client.post(
                            url,
                            json=payload,
                            headers={"x-goog-api-key": self.api_key},
                        )
                        res.raise_for_status()
                        data = res.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        cleaned = clean_json_response(raw_text)
                        return json.loads(cleaned)
                    except httpx.HTTPStatusError as e:
                        retryable_statuses = {429, 500, 502, 504}
                        retryable = e.response.status_code in retryable_statuses
                        if e.response.status_code == 429:
                            try:
                                error_body = e.response.json().get("error", {})
                                message = error_body.get("message", "").lower()
                                details = json.dumps(error_body.get("details", [])).lower()
                                quota_exhausted = any(marker in message or marker in details for marker in (
                                    "exceeded your current quota",
                                    "daily quota",
                                    "check your plan and billing",
                                    "free_tier",
                                ))
                                if quota_exhausted:
                                    retryable = False
                            except (ValueError, AttributeError):
                                pass

                        if not retryable or attempt == 1:
                            raise
                        delay = 2 ** attempt
                        logger.warning(
                            "Gemini returned HTTP %s; retrying in %s second(s), attempt %s/1.",
                            e.response.status_code,
                            delay,
                            attempt + 1,
                        )
                        await asyncio.sleep(delay)
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                provider_error = e.response.json().get("error", {})
                reason = provider_error.get("message", "")
                reason_code = provider_error.get("status", "")
            except (ValueError, AttributeError):
                reason = ""
                reason_code = ""

            # Never log request headers, which contain the API key.
            logger.error(
                "Gemini rejected the request (HTTP %s, %s): %s",
                status_code,
                reason_code or "provider error",
                reason[:300],
            )
            detail = f"Gemini rejected the request (HTTP {status_code})."
            if reason:
                detail += f" {reason[:300]}"
            raise RuntimeError(detail) from e
        except Exception as e:
            logger.error("Gemini API request failed (%s).", type(e).__name__)
            raise RuntimeError("Gemini API request failed. Check server configuration and provider availability.") from e

gemini_service = GeminiService()
