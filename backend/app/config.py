from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Bundled staging database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Credentials handed to the browser for neovis.js (direct bolt connection).
    # Neo4j Community has no RBAC, so these are the standard credentials — fine
    # for a local single-user tool. The browser reaches bolt on the host port.
    neo4j_browser_uri: str = "bolt://localhost:7687"
    neo4j_browser_user: str = "neo4j"
    neo4j_browser_password: str = "password"

    # Holds uploaded PDFs and generated artifacts, one subdirectory per job
    workspace_dir: Path = Path("/tmp/lecturetograph")

    pdf_render_dpi: int = 110
    pdf_max_pages_per_batch: int = 5
    pdf_image_max_edge: int = 1568  # clamp to the stricter provider limit

    agent_max_turns: int = 60
    agent_max_tokens: int = 8192

    default_provider: str = "anthropic"

    # <provider>_model is the preselected model. Together with <provider>_model_fast
    # it fills the model dropdown when the provider's model list cannot be fetched.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"
    anthropic_model_fast: str = "claude-sonnet-4-6"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4"
    openai_model_fast: str = "gpt-5.4-mini"

    # A private, OpenAI-compatible endpoint (a university cluster behind an
    # OpenWebUI gateway here). Leaving the base URL empty hides the provider
    # from the UI, so an unconfigured install behaves exactly as before.
    cluster_base_url: str | None = None            # must end in /api/v1 for OpenWebUI
    cluster_api_key: str | None = None
    cluster_label: str = "Hochschul-Cluster"
    cluster_model: str = "ultrabrain"
    cluster_model_fast: str | None = None
    # Self-signed certificate: point at the server certificate. Only if that
    # cannot be made to work, disable verification with cluster_verify_ssl.
    cluster_ca_bundle: Path | None = None
    cluster_verify_ssl: bool = True


settings = Settings()
