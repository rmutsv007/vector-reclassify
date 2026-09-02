from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFields,
    QgsMapLayerType,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
)


@dataclass(frozen=True)
class ReclassifyConfig:
    layer_ids: tuple[str, ...]
    source_field: str
    target_field: str
    rules: dict[str, str]
    keep_unmatched: bool
    selected_only: bool
    output_path: str | None
    output_type: str
    output_format: str
    temporary_output: bool


@dataclass
class LayerResult:
    layer_id: str
    layer_name: str
    success: bool
    result_layer: QgsVectorLayer | None = None
    feature_count: int = 0
    matched_count: int = 0
    error_message: str | None = None


@dataclass
class RuleCoverage:
    layer_name: str
    total: int = 0
    matched: int = 0
    unmatched: int = 0
    error_message: str | None = None


def reclassify_vector_layers(config: ReclassifyConfig) -> list[LayerResult]:
    """Reclassify one or more layers using the same rule set.

    Every layer is processed independently: a failure on one layer is
    recorded in its LayerResult and does not stop the remaining layers.
    """
    if not config.layer_ids:
        raise ValueError("Select at least one vector layer.")
    if not config.target_field.strip():
        raise ValueError("Target field name is required.")

    is_batch = len(config.layer_ids) > 1
    output_target = _validate_and_prepare_output_target(config, is_batch)

    results: list[LayerResult] = []
    for layer_id in config.layer_ids:
        layer = QgsProject.instance().mapLayer(layer_id)
        layer_name = layer.name() if layer is not None else layer_id
        try:
            result_layer, feature_count, matched_count = _reclassify_single_layer(
                layer, config, output_target, is_batch
            )
            results.append(
                LayerResult(
                    layer_id=layer_id,
                    layer_name=layer_name,
                    success=True,
                    result_layer=result_layer,
                    feature_count=feature_count,
                    matched_count=matched_count,
                )
            )
        except ValueError as exc:
            results.append(
                LayerResult(
                    layer_id=layer_id,
                    layer_name=layer_name,
                    success=False,
                    error_message=str(exc),
                )
            )
    return results


def preview_rule_coverage(
    layer: QgsVectorLayer,
    source_field: str,
    rules: dict[str, str],
    selected_only: bool,
) -> RuleCoverage:
    """Count how many features would match the current rules without writing anything."""
    layer_name = layer.name() if layer is not None else "?"
    try:
        if not isinstance(layer, QgsVectorLayer):
            raise ValueError("Selected layer is not a valid vector layer.")
        field_index = layer.fields().indexOf(source_field)
        if field_index == -1:
            raise ValueError(f"Field '{source_field}' was not found.")
        features = _collect_features(layer, selected_only)
    except ValueError as exc:
        return RuleCoverage(layer_name=layer_name, error_message=str(exc))

    total = 0
    matched = 0
    for feature in features:
        total += 1
        if _normalize_key(feature[field_index]) in rules:
            matched += 1
    return RuleCoverage(
        layer_name=layer_name,
        total=total,
        matched=matched,
        unmatched=total - matched,
    )


def _validate_and_prepare_output_target(
    config: ReclassifyConfig, is_batch: bool
) -> Path | None:
    if config.temporary_output:
        return None

    if not config.output_path or not config.output_path.strip():
        raise ValueError(
            "Output folder is required when temporary output is disabled."
            if is_batch
            else "Output path is required when temporary output is disabled."
        )

    output_target = Path(config.output_path.strip())
    if is_batch:
        if output_target.suffix:
            raise ValueError(
                "Choose an output folder (not a file) when processing multiple layers."
            )
        output_target.mkdir(parents=True, exist_ok=True)
    elif not output_target.parent.exists():
        raise ValueError("Output folder does not exist.")

    return output_target


def _reclassify_single_layer(
    layer: QgsVectorLayer,
    config: ReclassifyConfig,
    output_target: Path | None,
    is_batch: bool,
) -> tuple[QgsVectorLayer, int, int]:
    if not isinstance(layer, QgsVectorLayer) or layer.type() != QgsMapLayerType.VectorLayer:
        raise ValueError("Selected layer is not a valid vector layer.")

    if layer.fields().indexOf(config.target_field) != -1:
        raise ValueError(
            f"Layer '{layer.name()}': target field already exists. "
            "Choose a new field name."
        )

    source_index = layer.fields().indexOf(config.source_field)
    if source_index == -1:
        raise ValueError(
            f"Layer '{layer.name()}': source field '{config.source_field}' was not found."
        )

    output_path = _resolve_output_path(config, layer, output_target, is_batch)
    if output_path.exists():
        raise ValueError(
            f"Layer '{layer.name()}': output file '{output_path.name}' already exists."
        )

    features = _collect_features(layer, config.selected_only)
    output_fields = QgsFields(layer.fields())
    output_fields.append(_build_target_field(config.target_field, config.output_type))

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = _driver_name_from_format(config.output_format)
    options.fileEncoding = "UTF-8"
    display_name = _layer_display_name(config, output_path, layer, is_batch)
    options.layerName = _storage_layer_name(config, output_path, layer, is_batch)

    writer = QgsVectorFileWriter.create(
        str(output_path),
        output_fields,
        layer.wkbType(),
        layer.crs(),
        QgsProject.instance().transformContext(),
        options,
    )
    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise ValueError(
            f"Layer '{layer.name()}': "
            f"{writer.errorMessage() or 'could not create the output layer.'}"
        )

    feature_count = 0
    matched_count = 0
    for feature in features:
        source_value = feature[source_index]
        rule_key = _normalize_key(source_value)
        if rule_key in config.rules:
            matched_count += 1
        reclassified_value = _resolve_output_value(source_value, config)
        new_feature = QgsFeature(output_fields)
        new_feature.setGeometry(feature.geometry())
        new_feature.setAttributes(feature.attributes() + [reclassified_value])
        if not writer.addFeature(new_feature):
            del writer
            raise ValueError(
                f"Layer '{layer.name()}': could not write a feature to the output layer."
            )
        feature_count += 1

    del writer

    layer_uri = str(output_path)
    if output_path.suffix.lower() == ".gpkg":
        layer_uri = f"{output_path}|layername={options.layerName}"

    result_layer = QgsVectorLayer(layer_uri, display_name, "ogr")
    if not result_layer.isValid():
        raise ValueError(
            f"Layer '{layer.name()}': output was created but could not be loaded "
            "back into QGIS."
        )

    return result_layer, feature_count, matched_count


def _collect_features(layer: QgsVectorLayer, selected_only: bool):
    if selected_only:
        if layer.selectedFeatureCount() == 0:
            raise ValueError(
                f"Layer '{layer.name()}': selected features only is enabled, "
                "but no features are selected."
            )
        return list(layer.getSelectedFeatures())
    return list(layer.getFeatures())


def _build_target_field(field_name: str, output_type: str) -> QgsField:
    normalized_type = output_type.lower()
    if normalized_type == "integer":
        return QgsField(field_name, QVariant.Int)
    if normalized_type == "double":
        return QgsField(field_name, QVariant.Double, len=20, prec=6)
    return QgsField(field_name, QVariant.String, len=255)


def _resolve_output_path(
    config: ReclassifyConfig,
    layer: QgsVectorLayer,
    output_target: Path | None,
    is_batch: bool,
) -> Path:
    extension = _extension_from_format(config.output_format)

    if config.temporary_output:
        base_name = "vector_reclassify"
        if is_batch:
            base_name = f"vector_reclassify_{_sanitize_filename(layer.name())}"
        return _next_available_temporary_path(base_name, extension)

    if is_batch:
        filename = _sanitize_filename(f"{layer.name()}_{config.target_field}")
        return output_target / f"{filename}{extension}"

    if output_target.suffix:
        return output_target
    return output_target.with_suffix(extension)


def _layer_display_name(
    config: ReclassifyConfig, output_path: Path, layer: QgsVectorLayer, is_batch: bool
) -> str:
    if config.temporary_output and not is_batch:
        return "vector reclassify"
    return output_path.stem


def _storage_layer_name(
    config: ReclassifyConfig, output_path: Path, layer: QgsVectorLayer, is_batch: bool
) -> str:
    if config.temporary_output and not is_batch:
        return "vector_reclassify"
    return output_path.stem


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", name).strip("_")
    return cleaned or "layer"


def _next_available_temporary_path(base_name: str, extension: str) -> Path:
    temp_dir = Path(gettempdir())
    candidate = temp_dir / f"{base_name}{extension}"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = temp_dir / f"{base_name}_{index}{extension}"
        if not candidate.exists():
            return candidate
        index += 1


def _driver_name_from_format(output_format: str) -> str:
    normalized_format = output_format.lower()
    if normalized_format == "shapefile":
        return "ESRI Shapefile"
    if normalized_format == "geojson":
        return "GeoJSON"
    if normalized_format == "geopackage":
        return "GPKG"
    raise ValueError(
        "Unsupported output format. Use GeoPackage, Shapefile, or GeoJSON."
    )


def _extension_from_format(output_format: str) -> str:
    normalized_format = output_format.lower()
    if normalized_format == "shapefile":
        return ".shp"
    if normalized_format == "geojson":
        return ".geojson"
    if normalized_format == "geopackage":
        return ".gpkg"
    raise ValueError(
        "Unsupported output format. Use GeoPackage, Shapefile, or GeoJSON."
    )


def _resolve_output_value(source_value, config: ReclassifyConfig):
    rule_key = _normalize_key(source_value)
    if rule_key in config.rules:
        return _cast_output_value(config.rules[rule_key], config.output_type)
    if config.keep_unmatched:
        return _cast_output_value(source_value, config.output_type)
    return None


def _normalize_key(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _cast_output_value(value, output_type: str):
    if value in {None, ""}:
        return None

    normalized_type = output_type.lower()
    text_value = str(value).strip()
    if normalized_type == "integer":
        numeric_value = float(text_value)
        if not numeric_value.is_integer():
            raise ValueError(f"Value '{text_value}' cannot be stored as an integer.")
        return int(numeric_value)
    if normalized_type == "double":
        return float(text_value)
    return text_value
