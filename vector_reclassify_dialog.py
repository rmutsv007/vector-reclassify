from __future__ import annotations

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
    layer_id: str
    source_field: str
    target_field: str
    rules: dict[str, str]
    keep_unmatched: bool
    selected_only: bool
    output_path: str | None
    output_type: str
    output_format: str
    temporary_output: bool


def reclassify_vector_layer(config: ReclassifyConfig) -> tuple[QgsVectorLayer, int]:
    layer = QgsProject.instance().mapLayer(config.layer_id)
    if (
        not isinstance(layer, QgsVectorLayer)
        or layer.type() != QgsMapLayerType.VectorLayer
    ):
        raise ValueError("Selected layer is not a valid vector layer.")

    if not config.target_field.strip():
        raise ValueError("Target field name is required.")
    if layer.fields().indexOf(config.target_field) != -1:
        raise ValueError("Target field already exists. Choose a new field name.")

    source_index = layer.fields().indexOf(config.source_field)
    if source_index == -1:
        raise ValueError("Source field was not found in the selected layer.")

    output_path = _resolve_output_path(config)
    if output_path.exists():
        raise ValueError("Output file already exists. Choose a new path.")
    if not output_path.parent.exists():
        raise ValueError("Output folder does not exist.")

    features = _collect_features(layer, config.selected_only)
    output_fields = QgsFields(layer.fields())
    output_fields.append(_build_target_field(config.target_field, config.output_type))

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = _driver_name_from_format(config.output_format)
    options.fileEncoding = "UTF-8"
    display_name = _layer_display_name(config, output_path)
    options.layerName = _storage_layer_name(config, output_path)

    writer = QgsVectorFileWriter.create(
        str(output_path),
        output_fields,
        layer.wkbType(),
        layer.crs(),
        QgsProject.instance().transformContext(),
        options,
    )
    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise ValueError(writer.errorMessage() or "Could not create the output layer.")

    feature_count = 0
    for feature in features:
        source_value = feature[source_index]
        reclassified_value = _resolve_output_value(source_value, config)
        new_feature = QgsFeature(output_fields)
        new_feature.setGeometry(feature.geometry())
        new_feature.setAttributes(feature.attributes() + [reclassified_value])
        if not writer.addFeature(new_feature):
            del writer
            raise ValueError("Could not write a feature to the output layer.")
        feature_count += 1

    del writer

    layer_uri = str(output_path)
    if output_path.suffix.lower() == ".gpkg":
        layer_uri = f"{output_path}|layername={options.layerName}"

    result_layer = QgsVectorLayer(layer_uri, display_name, "ogr")
    if not result_layer.isValid():
        raise ValueError(
            "Output layer was created but could not be loaded back into QGIS."
        )

    QgsProject.instance().addMapLayer(result_layer)
    return result_layer, feature_count


def _collect_features(layer: QgsVectorLayer, selected_only: bool):
    if selected_only:
        if layer.selectedFeatureCount() == 0:
            raise ValueError(
                "Selected features only is enabled, but no features are selected."
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


def _resolve_output_path(config: ReclassifyConfig) -> Path:
    if config.temporary_output:
        extension = _extension_from_format(config.output_format)
        return _next_available_temporary_path(extension)

    if not config.output_path or not config.output_path.strip():
        raise ValueError("Output path is required when temporary output is disabled.")

    output_path = Path(config.output_path.strip())
    if output_path.suffix:
        return output_path
    return output_path.with_suffix(_extension_from_format(config.output_format))


def _layer_display_name(config: ReclassifyConfig, output_path: Path) -> str:
    if config.temporary_output:
        return "vector reclassify"
    return output_path.stem


def _storage_layer_name(config: ReclassifyConfig, output_path: Path) -> str:
    if config.temporary_output:
        return "vector_reclassify"
    return output_path.stem


def _next_available_temporary_path(extension: str) -> Path:
    temp_dir = Path(gettempdir())
    base_name = "vector_reclassify"
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
