"""Connector registry — factory pattern for creating connectors."""

from engines.connectors.base import (
    CDCConnector,
    ConnectorConfig,
    PullConnector,
)


class ConnectorRegistry:
    """Registry of available connector types."""

    def __init__(self):
        self._pull: dict[str, type[PullConnector]] = {}
        self._cdc: dict[str, type[CDCConnector]] = {}

    def register_pull(
        self, source_type: str, cls: type[PullConnector]
    ) -> None:
        self._pull[source_type] = cls

    def register_cdc(
        self, source_type: str, cls: type[CDCConnector]
    ) -> None:
        self._cdc[source_type] = cls

    def create(
        self, config: ConnectorConfig
    ) -> PullConnector | CDCConnector:
        """Create a connector instance from config."""
        if config.source_type in self._cdc:
            return self._cdc[config.source_type](config)
        if config.source_type in self._pull:
            return self._pull[config.source_type](config)
        raise ValueError(
            f"Unknown source type: {config.source_type}. "
            f"Available: {list(self._pull) + list(self._cdc)}"
        )

    @property
    def available_types(self) -> list[str]:
        return list(self._pull) + list(self._cdc)


# Global registry with built-in connectors
registry = ConnectorRegistry()


def _register_builtins():
    from engines.connectors.postgres_cdc import (
        PostgresCDCConnector,
    )
    from engines.connectors.s3_file import S3FileConnector

    registry.register_cdc("postgresql", PostgresCDCConnector)
    registry.register_pull("s3", S3FileConnector)


_register_builtins()
