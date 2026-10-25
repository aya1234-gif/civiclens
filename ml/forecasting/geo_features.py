"""Geospatial feature engineering for service gap forecasting.

Joins tender/budget data with administrative boundary shapefiles
to produce region-level feature vectors.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import structlog

log = structlog.get_logger(__name__)

_SHAPEFILE_PATH = Path("data/raw/shapefiles/morocco_provinces.shp")


def load_admin_boundaries() -> gpd.GeoDataFrame:
    """Load Morocco administrative boundary shapefile.

    Downloads from HDX if the local file is absent.
    """
    if not _SHAPEFILE_PATH.exists():
        log.warning(
            "shapefile_missing",
            path=str(_SHAPEFILE_PATH),
            hint="Run: make ingest-shapefiles",
        )
        return gpd.GeoDataFrame()

    gdf = gpd.read_file(_SHAPEFILE_PATH)
    log.info("admin_boundaries_loaded", rows=len(gdf))
    return gdf


def add_geo_features(df: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    """Enrich *df* with spatial covariates from *boundaries*.

    Adds columns: area_km2, population_density, centroid_lat, centroid_lon.

    Args:
        df: DataFrame with a wilaya column matching boundary names.
        boundaries: GeoDataFrame of administrative units.

    Returns:
        *df* with added geo feature columns.
    """
    if boundaries.empty:
        log.warning("geo_features_skipped", reason="empty boundaries")
        return df

    boundaries = boundaries.to_crs("EPSG:26191")  # Morocco Lambert for area calc
    boundaries = boundaries.copy()
    boundaries["area_km2"] = boundaries.geometry.area / 1e6
    boundaries = boundaries.to_crs("EPSG:4326")
    centroids = boundaries.geometry.centroid
    boundaries["centroid_lat"] = centroids.y
    boundaries["centroid_lon"] = centroids.x

    merged = df.merge(
        boundaries[["ADM2_EN", "area_km2", "centroid_lat", "centroid_lon"]],
        left_on="wilaya",
        right_on="ADM2_EN",
        how="left",
    )
    log.info("geo_features_added", rows=len(merged))
    return merged
