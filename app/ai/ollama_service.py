"""Minimal Ollama client (local inference only). Raises typed errors for every failure."""

import httpx


class OllamaError(Exception):
    """Base class; the message is safe to show to API consumers."""


class OllamaUnavailableError(OllamaError):
    pass


class OllamaModelNotFoundError(OllamaError):
    pass


class OllamaTimeoutError(OllamaError):
    pass


class OllamaInvalidResponseError(OllamaError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 60.0,
                 http_client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._http_client = http_client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.1, "num_predict": 300},
        }
        client = self._http_client or httpx.Client(timeout=self.timeout)
        try:
            response = client.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        except httpx.ConnectError:
            raise OllamaUnavailableError(
                f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is "
                "installed and running (`ollama serve`)."
            ) from None
        except httpx.TimeoutException:
            raise OllamaTimeoutError(
                f"Ollama did not respond within {self.timeout:g} seconds."
            ) from None
        except httpx.HTTPError:
            raise OllamaUnavailableError("The request to Ollama failed.") from None
        finally:
            if self._http_client is None:
                client.close()

        if response.status_code == 404:
            raise OllamaModelNotFoundError(
                f"Ollama model '{self.model}' is not available. "
                f"Download it with `ollama pull {self.model}`."
            )
        if response.status_code >= 400:
            raise OllamaUnavailableError(f"Ollama returned HTTP {response.status_code}.")
        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError):
            raise OllamaInvalidResponseError("Ollama returned an unreadable response.") from None
        if not isinstance(content, str):
            raise OllamaInvalidResponseError("Ollama returned an unreadable response.")
        return content
