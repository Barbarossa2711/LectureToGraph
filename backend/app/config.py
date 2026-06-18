from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neo4j (the bundled staging database)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Credentials handed to the browser for neovis.js (direct bolt connection).
    # Neo4j Community has no RBAC, so these are the standard credentials — fine
    # for a local single-user tool. The browser reaches bolt on the host port.
    neo4j_browser_uri: str = "bolt://localhost:7687"
    neo4j_browser_user: str = "neo4j"
    neo4j_browser_password: str = "password"

    # Per-job workspace where uploaded PDFs and generated artifacts live.
    workspace_dir: Path = Path("/tmp/lecturetograph")

    # PDF rendering
    pdf_render_dpi: int = 110
    pdf_max_pages_per_batch: int = 5
    pdf_image_max_edge: int = 1568  # clamp to the stricter provider limit

    # Agent loop
    agent_max_turns: int = 60
    agent_max_tokens: int = 8192

    # Providers / models
    default_provider: str = "anthropic"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"          # stage 1 (reasoning heavy)
    anthropic_model_fast: str = "claude-sonnet-4-6"   # cheaper later stages

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4"
    openai_model_fast: str = "gpt-5.4-mini"


settings = Settings()
