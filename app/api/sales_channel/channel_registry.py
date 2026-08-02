"""Explicit mapping between public channel routes and external SQL tables.

The HTTP client selects only country and provider combinations declared here.
It never supplies a database or table name, which keeps infrastructure details
out of the API and prevents arbitrary access to the SQL Server instance.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.api.sales_channel.sku.service import SkuModelConfig
from app.models.external.ofisis.ecomm import (
    MxRappiSku,
    PeyaPromoSku,
    PeyaSku,
    RappiSku,
)


class CountryCode(StrEnum):
    PERU = "pe"
    MEXICO = "mx"


class ProviderCode(StrEnum):
    RAPPI = "rappi"
    PEYA = "peya"


@dataclass(frozen=True)
class SalesChannelDefinition:
    country: CountryCode
    provider: ProviderCode
    display_name: str
    sku_config: SkuModelConfig

    @property
    def base_prefix(self) -> str:
        return f"/{self.country.value}/{self.provider.value}"

    @property
    def sku_prefix(self) -> str:
        return f"{self.base_prefix}/skus"


RAPPI_PERU = SalesChannelDefinition(
    country=CountryCode.PERU,
    provider=ProviderCode.RAPPI,
    display_name="Rappi Peru",
    sku_config=SkuModelConfig(
        model=RappiSku,
        external_id_field="id_rappi",
        updated_at_field="updated_at",
        channel_name="Rappi Peru",
        external_id_matches_sku=True,
    ),
)

RAPPI_MEXICO = SalesChannelDefinition(
    country=CountryCode.MEXICO,
    provider=ProviderCode.RAPPI,
    display_name="Rappi Mexico",
    sku_config=SkuModelConfig(
        model=MxRappiSku,
        external_id_field="id_rappi",
        updated_at_field="updated_at",
        channel_name="Rappi Mexico",
        external_id_matches_sku=True,
    ),
)

PEYA_PERU = SalesChannelDefinition(
    country=CountryCode.PERU,
    provider=ProviderCode.PEYA,
    display_name="Peya Peru",
    sku_config=SkuModelConfig(
        model=PeyaSku,
        external_id_field="id_peya",
        updated_at_field="modified_at",
        channel_name="Peya Peru",
        promotion_model=PeyaPromoSku,
        external_id_matches_sku=True,
    ),
)

# This registry is the source of truth for supported country/provider pairs.
SALES_CHANNELS = {
    (channel.country, channel.provider): channel
    for channel in (RAPPI_PERU, RAPPI_MEXICO, PEYA_PERU)
}


def get_sales_channel(
    country: CountryCode,
    provider: ProviderCode,
) -> SalesChannelDefinition:
    """Return a configured channel; unsupported combinations fail explicitly."""
    try:
        return SALES_CHANNELS[(country, provider)]
    except KeyError as exc:
        raise ValueError(
            f"Canal no configurado: {country.value}/{provider.value}"
        ) from exc
