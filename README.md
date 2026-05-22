[general]
name=Vector Reclassify
qgisMinimumVersion=3.28
qgisMaximumVersion=3.99
description=Reclassify vector attribute values into a new field and save as a new layer.
version=0.1.5
author=Passakorn Poonkerd
email=pussakorn8899@gmail.com
about=Adds a QGIS plugin dialog to map source attribute values to new class values and export the result as a new vector layer.
category=Vector
icon=icon.png
homepage=https://github.com/rmutsv007/vector-reclassify
tracker=https://github.com/rmutsv007/vector-reclassify/issues
repository=https://github.com/rmutsv007/vector-reclassify

changelog=0.1.5 Adjusted multiline boolean conditions to resolve Flake8 W503 informational items.
	0.1.4 Added trailing newlines to Python files to fix Flake8 W292 informational items.
	0.1.3 Cleaned Python formatting to address informational code-quality items.
	0.1.2 Added a dedicated top toolbar button for the plugin action.
	0.1.1 Repository metadata updated, PNG icon added, drag-and-drop rule editing preserved across mode switches.
	0.1.0 Initial release with exact-match vector reclassification, temporary output by default, and export packaging scaffold.
experimental=False
deprecated=False
hasProcessingProvider=False
tags=vector,reclassify,attribute,classification