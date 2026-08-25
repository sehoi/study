"""환경변수 기반 설정.

`.env` 파일 또는 프로세스 환경변수에서 값을 읽는다.
API 키는 코드에 하드코딩하지 않고 `ANTHROPIC_API_KEY` 로만 주입한다.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = None

    # Claude 모델. Opus 5 는 thinking 이 기본 활성화이므로 별도 설정이 필요 없고,
    # temperature / top_p 등 샘플링 파라미터는 400 에러가 나므로 절대 넘기지 않는다.
    claude_model: str = "claude-opus-5"

    # 고객센터 답변은 의도적으로 짧게 유지한다.
    max_tokens: int = 4096

    # 무한 도구 호출 루프 방지용 상한.
    max_tool_iterations: int = 8

    bank_name: str = "한결은행"
    agent_name: str = "하늘"

    @property
    def has_credentials(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """프로세스 전체에서 재사용하는 설정 싱글턴."""
    return Settings()
