"""
gemini_key_pool.py
==================
Production-grade multi-key Gemini API pool built on the new
google-genai SDK (package: google-genai, import: from google import genai).

Install:
    pip install google-genai

Features:
  - Per-key quota tracking (RPM + RPD sliding windows)
  - Automatic cooldown on rate-limit (429) / quota / server (5xx) errors
  - Exponential backoff with jitter
  - Auth-error key retirement (no wasted retries on dead keys)
  - Thread-safe via RLock
  - Structured logging
  - Health diagnostics
  - Full type annotations
  - Context-manager support with proper client cleanup

Usage:
    from gemini_key_pool import GeminiKeyPool, PoolConfig

    pool = GeminiKeyPool.from_env()
    response = pool.generate("Hello, Gemini!")
    print(response.text)
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("gemini_key_pool")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] gemini_key_pool: %(message)s")
    )
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class PoolConfig:
    """
    Tunable parameters for the key pool.

    Attributes:
        model_name                : Gemini model string.
        rpm_limit                 : Max requests per minute per key (free tier = 15).
        rpd_limit                 : Max requests per day per key (free tier = 1500).
        max_retries               : Total retry attempts before raising.
        base_backoff_s            : Base seconds for exponential backoff.
        max_backoff_s             : Ceiling for backoff sleep.
        jitter_fraction           : Random jitter as a fraction of backoff delay (0-1).
        rate_limit_cooldown_s     : Park duration after a 429 rate-limit response.
        quota_cooldown_s          : Park duration after daily quota exhaustion.
        server_error_cooldown_s   : Park duration after 5xx server errors.
        generation_config         : Default types.GenerateContentConfig for every call.
    """
    model_name: str = "gemini-2.5-flash"
    rpm_limit: int = 15
    rpd_limit: int = 1500
    max_retries: int = 5
    base_backoff_s: float = 1.0
    max_backoff_s: float = 60.0
    jitter_fraction: float = 0.25
    rate_limit_cooldown_s: float = 65.0      # slightly > 60 s to clear the 1-min window
    quota_cooldown_s: float = 3_600.0        # 1 h: retry after daily quota refresh
    server_error_cooldown_s: float = 30.0
    generation_config: types.GenerateContentConfig | None = None


# ---------------------------------------------------------------------------
# Key state
# ---------------------------------------------------------------------------
class KeyStatus(Enum):
    HEALTHY = auto()
    RATE_LIMITED = auto()
    QUOTA_EXHAUSTED = auto()
    SERVER_ERROR = auto()
    RETIRED = auto()          # permanent: auth failure or repeated hard errors


@dataclass
class _KeyState:
    """Internal per-key bookkeeping. Not part of the public API."""
    key: str
    client: genai.Client = field(init=False)
    status: KeyStatus = KeyStatus.HEALTHY
    cooldown_until: float = 0.0           # monotonic seconds
    failures: int = 0
    _minute_window: list[float] = field(default_factory=list)
    _day_window: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Each key owns its own Client instance: no global configure() calls
        self.client = genai.Client(api_key=self.key)

    # ------------------------------------------------------------------ #
    # Availability
    # ------------------------------------------------------------------ #
    def is_available(self) -> bool:
        if self.status == KeyStatus.RETIRED:
            return False
        if self.cooldown_until > time.monotonic():
            return False
        # cooldown has expired: restore health
        if self.status != KeyStatus.HEALTHY:
            self.status = KeyStatus.HEALTHY
            self.failures = 0
        return True

    # ------------------------------------------------------------------ #
    # Sliding-window quota accounting
    # ------------------------------------------------------------------ #
    def _prune_windows(self) -> None:
        now = time.monotonic()
        self._minute_window = [t for t in self._minute_window if now - t < 60]
        self._day_window    = [t for t in self._day_window    if now - t < 86_400]

    def can_request(self, rpm_limit: int, rpd_limit: int) -> bool:
        self._prune_windows()
        return (
            len(self._minute_window) < rpm_limit
            and len(self._day_window) < rpd_limit
        )

    def record_request(self) -> None:
        now = time.monotonic()
        self._minute_window.append(now)
        self._day_window.append(now)

    # ------------------------------------------------------------------ #
    # Failure markers
    # ------------------------------------------------------------------ #
    def mark_rate_limited(self, cooldown_s: float) -> None:
        self.status = KeyStatus.RATE_LIMITED
        self.failures += 1
        self.cooldown_until = time.monotonic() + cooldown_s
        logger.warning(
            "Key …%s rate-limited; cooling down %.0f s", self.key[-6:], cooldown_s
        )

    def mark_quota_exhausted(self, cooldown_s: float) -> None:
        self.status = KeyStatus.QUOTA_EXHAUSTED
        self.failures += 1
        self.cooldown_until = time.monotonic() + cooldown_s
        logger.error(
            "Key …%s quota exhausted; parking %.0f s (%.1f min)",
            self.key[-6:], cooldown_s, cooldown_s / 60,
        )

    def mark_server_error(self, cooldown_s: float) -> None:
        self.status = KeyStatus.SERVER_ERROR
        self.failures += 1
        self.cooldown_until = time.monotonic() + cooldown_s
        logger.warning(
            "Key …%s server error; cooling down %.0f s", self.key[-6:], cooldown_s
        )

    def mark_retired(self) -> None:
        self.status = KeyStatus.RETIRED
        self.cooldown_until = float("inf")
        logger.error(
            "Key …%s is invalid/unauthorised: retired permanently.", self.key[-6:]
        )

    def mark_success(self) -> None:
        self.status = KeyStatus.HEALTHY
        self.failures = 0
        self.cooldown_until = 0.0

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------
class GeminiKeyPool:
    """
    Thread-safe pool of Gemini API keys built on the new google-genai SDK.

    Each key owns its own genai.Client instance. The pool selects the
    healthiest available key for every request and handles all error
    classification, cooldowns, and retries internally.
    """

    def __init__(
        self,
        api_keys: list[str],
        config: PoolConfig | None = None,
    ) -> None:
        if not api_keys:
            raise ValueError("GeminiKeyPool requires at least one API key.")
        self._config = config or PoolConfig()
        self._keys: list[_KeyState] = [_KeyState(key=k) for k in api_keys]
        self._lock = threading.RLock()
        logger.info(
            "Pool initialised: %d key(s), model=%s",
            len(self._keys), self._config.model_name,
        )

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #
    @classmethod
    def from_env(
        cls,
        prefix: str = "GEMINI_API_KEY",
        config: PoolConfig | None = None,
    ) -> "GeminiKeyPool":
        """
        Load keys from environment variables.

        Reads GEMINI_API_KEY_1, GEMINI_API_KEY_2, … stopping at the
        first missing index. Falls back to a bare GEMINI_API_KEY when
        no numbered variants exist.

        Recommended .env layout:
            GEMINI_API_KEY_1=AIza...
            GEMINI_API_KEY_2=AIza...
            GEMINI_API_KEY_3=AIza...
        """
        keys: list[str] = []
        idx = 1
        while True:
            val = os.getenv(f"{prefix}_{idx}", "").strip()
            if not val:
                break
            keys.append(val)
            idx += 1
        if not keys:
            bare = os.getenv(prefix, "").strip()
            if bare:
                keys.append(bare)
        if not keys:
            raise EnvironmentError(
                f"No Gemini API keys found. "
                f"Set {prefix}_1, {prefix}_2, … in your environment."
            )
        logger.info("Loaded %d key(s) from env (prefix=%s)", len(keys), prefix)
        return cls(api_keys=keys, config=config)

    @classmethod
    def from_list(
        cls,
        keys: list[str],
        config: PoolConfig | None = None,
    ) -> "GeminiKeyPool":
        """Convenience constructor from a plain Python list."""
        return cls(api_keys=keys, config=config)

    # ------------------------------------------------------------------ #
    # Key selection
    # ------------------------------------------------------------------ #
    def _next_key(self) -> _KeyState | None:
        """
        Return the healthiest available key (fewest failures, within quota).
        Returns None when every key is on cooldown or retired.
        """
        cfg = self._config
        with self._lock:
            candidates = [
                k for k in self._keys
                if k.is_available() and k.can_request(cfg.rpm_limit, cfg.rpd_limit)
            ]
            if not candidates:
                return None
            return min(candidates, key=lambda k: k.failures)

    # ------------------------------------------------------------------ #
    # Backoff helper
    # ------------------------------------------------------------------ #
    def _backoff(self, attempt: int) -> None:
        cfg = self._config
        delay = min(cfg.base_backoff_s * (2 ** attempt), cfg.max_backoff_s)
        jitter = delay * cfg.jitter_fraction * random.random()
        time.sleep(delay + jitter)

    # ------------------------------------------------------------------ #
    # Error classification helper
    # ------------------------------------------------------------------ #
    @staticmethod
    def _http_status(exc: APIError) -> int | None:
        """Extract the HTTP status code from a google.genai APIError."""
        for attr in ("code", "status_code"):
            val = getattr(exc, attr, None)
            if isinstance(val, int):
                return val
        return None

    # ------------------------------------------------------------------ #
    # Core generate
    # ------------------------------------------------------------------ #
    def generate(
        self,
        contents: str | list[Any],
        *,
        config: types.GenerateContentConfig | None = None,
        stream: bool = False,
    ) -> Any:
        """
        Send a prompt to Gemini, automatically rotating keys on failure.

        Parameters
        ----------
        contents : str or list
            Passed directly to client.models.generate_content().
            Accepts plain strings, list[types.Content], list[types.Part],
            or list of dicts: whatever the new SDK supports.
        config   : types.GenerateContentConfig
            Per-call override; falls back to pool-level generation_config.
        stream   : bool
            If True, calls generate_content_stream() and returns an iterator.

        Returns
        -------
        types.GenerateContentResponse  (or a streaming iterator)

        Raises
        ------
        RuntimeError  when all retries across all keys are exhausted.
        """
        cfg = self._config
        effective_config = config or cfg.generation_config
        last_exc: Exception | None = None

        for attempt in range(cfg.max_retries):
            key_state = self._next_key()

            # All keys parked: wait for the soonest cooldown to expire
            if key_state is None:
                with self._lock:
                    active = [
                        k.cooldown_until for k in self._keys
                        if k.status != KeyStatus.RETIRED
                    ]
                if not active:
                    raise RuntimeError(
                        "GeminiKeyPool: all keys have been retired (auth failures). "
                        "Check your API keys."
                    )
                wait = max(0.0, min(active) - time.monotonic()) + 1.0
                logger.warning(
                    "All keys parked: waiting %.1f s (attempt %d/%d).",
                    wait, attempt + 1, cfg.max_retries,
                )
                time.sleep(wait)
                continue

            with self._lock:
                key_state.record_request()
            masked = f"…{key_state.key[-6:]}"

            try:
                logger.debug("Attempt %d: key %s", attempt + 1, masked)

                call_kwargs: dict[str, Any] = {
                    "model": cfg.model_name,
                    "contents": contents,
                }
                if effective_config is not None:
                    call_kwargs["config"] = effective_config

                if stream:
                    response = key_state.client.models.generate_content_stream(
                        **call_kwargs
                    )
                else:
                    response = key_state.client.models.generate_content(
                        **call_kwargs
                    )

                with self._lock:
                    key_state.mark_success()
                logger.debug("Success: attempt %d, key %s", attempt + 1, masked)
                return response

            # ---- 4xx client errors (rate-limit, quota, auth) -------------
            except ClientError as exc:
                last_exc = exc
                status = self._http_status(exc)
                err_lower = str(exc).lower()

                if status == 429 or "resource_exhausted" in err_lower:
                    with self._lock:
                        if "daily" in err_lower or "per day" in err_lower:
                            key_state.mark_quota_exhausted(cfg.quota_cooldown_s)
                        else:
                            key_state.mark_rate_limited(cfg.rate_limit_cooldown_s)
                elif status in (401, 403) or any(
                    kw in err_lower
                    for kw in ("api key", "invalid", "permission", "unauthenticated")
                ):
                    with self._lock:
                        key_state.mark_retired()
                else:
                    logger.warning("4xx error (status=%s) on key %s: %s", status, masked, exc)
                    with self._lock:
                        key_state.mark_server_error(cfg.server_error_cooldown_s)

                self._backoff(attempt)

            # ---- 5xx server errors ---------------------------------------
            except ServerError as exc:
                last_exc = exc
                logger.warning("Server error on key %s: %s", masked, exc)
                with self._lock:
                    key_state.mark_server_error(cfg.server_error_cooldown_s)
                self._backoff(attempt)

            # ---- unexpected / network errors -----------------------------
            except Exception as exc:
                last_exc = exc
                err_lower = str(exc).lower()
                if any(
                    kw in err_lower
                    for kw in ("api key", "invalid", "permission", "unauthenticated")
                ):
                    with self._lock:
                        key_state.mark_retired()
                else:
                    logger.error("Unexpected error on key %s: %s", masked, exc)
                    with self._lock:
                        key_state.mark_server_error(cfg.server_error_cooldown_s)
                self._backoff(attempt)

        raise RuntimeError(
            f"GeminiKeyPool exhausted all {cfg.max_retries} retries. "
            f"Last error: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------ #
    # Health / diagnostics
    # ------------------------------------------------------------------ #
    def health(self) -> list[dict[str, Any]]:
        """
        Thread-safe snapshot of every key's current state.

        Returns a list of dicts with keys:
            key_suffix, status, failures, cooldown_remaining_s,
            rpm_used_last_min, rpd_used_today
        """
        now = time.monotonic()
        with self._lock:
            return [
                {
                    "key_suffix": k.key[-8:],
                    "status": k.status.name,
                    "failures": k.failures,
                    "cooldown_remaining_s": round(max(0.0, k.cooldown_until - now), 1),
                    "rpm_used_last_min": len([t for t in k._minute_window if now - t < 60]),
                    "rpd_used_today":    len([t for t in k._day_window    if now - t < 86_400]),
                }
                for k in self._keys
            ]

    def healthy_count(self) -> int:
        """Number of keys not currently on cooldown or retired."""
        with self._lock:
            return sum(1 for k in self._keys if k.is_available())

    def log_health(self) -> None:
        """Write a human-readable health table to the logger at INFO level."""
        rows = self.health()
        logger.info("=== GeminiKeyPool Health (%d key(s)) ===", len(rows))
        for r in rows:
            logger.info(
                "  key=…%-8s  status=%-17s  failures=%d  "
                "cooldown=%.0fs  rpm=%d/min  rpd=%d/day",
                r["key_suffix"], r["status"], r["failures"],
                r["cooldown_remaining_s"], r["rpm_used_last_min"], r["rpd_used_today"],
            )

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Close all underlying genai.Client HTTP connections."""
        with self._lock:
            for k in self._keys:
                k.close()
        logger.info("GeminiKeyPool closed: all clients released.")

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #
    def __enter__(self) -> "GeminiKeyPool":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# One-liner factory
# ---------------------------------------------------------------------------
def build_pool_from_env(
    model_name: str = "gemini-2.5-flash",
    rpm_limit: int = 15,
    rpd_limit: int = 1500,
    max_retries: int = 5,
    generation_config: types.GenerateContentConfig | None = None,
) -> GeminiKeyPool:
    """
    Convenience factory: reads GEMINI_API_KEY_1, _2, … from the environment.

    Example:
        pool = build_pool_from_env()
        print(pool.generate("Hello").text)
    """
    cfg = PoolConfig(
        model_name=model_name,
        rpm_limit=rpm_limit,
        rpd_limit=rpd_limit,
        max_retries=max_retries,
        generation_config=generation_config,
    )
    return GeminiKeyPool.from_env(config=cfg)