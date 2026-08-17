"""
legacy_contract.ingestion — artifact ingestion package.

Convenience re-exports for the most common ingestion operations.
"""
from legacy_contract.ingestion.ingester import ArtifactIngester, ArtifactInventory, ArtifactRecord


def ingest_directory(path: str) -> "ArtifactInventory":
    """
    Convenience function: ingest all legacy artifacts in *path*.

    Equivalent to:
        ArtifactIngester().ingest_directory(path)

    Returns
    -------
    ArtifactInventory
        Combined IR graph + per-artifact records.
    """
    return ArtifactIngester().ingest_directory(path)


__all__ = [
    "ArtifactIngester",
    "ArtifactInventory",
    "ArtifactRecord",
    "ingest_directory",
]
