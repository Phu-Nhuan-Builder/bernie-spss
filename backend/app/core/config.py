from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    REDIS_URL: str = "redis://localhost:6379/0"
    MAX_UPLOAD_MB: int = 50
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,https://spss.phunhuanbuilder.com,https://bernie-spss.vercel.app"
    ENVIRONMENT: str = "development"
    CLOUDFLARE_R2_ACCOUNT_ID: str = ""
    CLOUDFLARE_R2_ACCESS_KEY: str = ""
    CLOUDFLARE_R2_SECRET_KEY: str = ""
    CLOUDFLARE_R2_BUCKET: str = "bernie-spss-uploads"

    # AI Layer — NVIDIA NIM
    NVIDIA_NIM_API_KEY: str = ""
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_NIM_MODEL: str = "meta/llama-3.1-70b-instruct"

    # Session TTL (seconds) — default 1 hour
    SESSION_TTL_SECONDS: int = 3600
    SESSION_MAX_COUNT: int = 100

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


settings = Settings()
