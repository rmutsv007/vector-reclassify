# Changelog

## 0.2.0

- Fixed the plugin entry point, which previously referenced code from an unrelated
  plugin and never loaded the actual Vector Reclassify dialog
- Added multi-layer batch reclassify: pick several layers with checkboxes and run
  the same rule set against all of them; each layer succeeds or fails independently
  and a summary is shown when done
- Added bulk rule editing: assign a target value to multiple selected table rows,
  or move multiple selected values into a class at once in drag-and-drop mode
- Added rule filtering (search box) and highlighting of rows missing a target value
- Added save/load rule presets as JSON, plus a recent-presets menu
- Added a "Preview coverage" action showing matched/unmatched feature counts per
  layer before running
- Dialog now remembers output type/format and checkbox settings between uses
- Output format is now an explicit choice (GeoPackage/Shapefile/GeoJSON) instead of
  being inferred from a typed file extension; batch mode writes to a chosen folder
  with one file per layer

## 0.1.5

- Adjusted multiline boolean conditions to resolve Flake8 W503 informational findings

## 0.1.4

- Added trailing newlines to Python files to resolve Flake8 W292 informational findings

## 0.1.3

- Wrapped Python lines to reduce informational code-quality findings from repository scans

## 0.1.2

- Added a dedicated top toolbar for the plugin action in QGIS

## 0.1.1

- Added repository-ready PNG icon and updated plugin metadata
- Added drag-and-drop rule editing that preserves rules when switching modes
- Added LICENSE to support publishing in the QGIS Plugins Directory

## 0.1.0

- Initial QGIS plugin release
- Exact-match vector attribute reclassification into a new field
- Temporary output enabled by default
- Export support for GeoPackage, Shapefile, and GeoJSON
- Packaging script and plugin icon added for distribution