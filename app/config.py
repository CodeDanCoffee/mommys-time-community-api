from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, read from environment / a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Apple Sign In — the identity token is verified against these.
    apple_bundle_id: str = "com.codedancoffee.mommys-time"
    apple_issuer: str = "https://appleid.apple.com"
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"

    # Our own session tokens.
    jwt_secret: str = "dev-only-secret-change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    session_days: int = 60

    database_url: str = "sqlite:///./community.db"

    # Dev-only: allow logging in with a raw Apple user id (no real token).
    allow_dev_login: bool = False


settings = Settings()
