from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import Qgis, QgsProject

from .reclassifier import reclassify_vector_layers
from .vector_reclassify_dialog import VectorReclassifyDialog


class VectorReclassifyPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.toolbar = None
        self.plugin_dir = Path(__file__).resolve().parent

    def initGui(self):
        icon_path = self.plugin_dir / "icon.png"
        self.action = QAction(
            QIcon(str(icon_path)),
            "Vector Reclassify",
            self.iface.mainWindow(),
        )
        self.action.setObjectName("vectorReclassifyAction")
        self.action.setStatusTip(
            "Reclassify vector attribute values into a new field across one or more layers"
        )
        self.action.triggered.connect(self.run)
        self.toolbar = self.iface.addToolBar("Vector Reclassify")
        self.toolbar.setObjectName("VectorReclassifyToolbar")
        self.toolbar.addAction(self.action)
        self.iface.addPluginToVectorMenu("&Vector Reclassify", self.action)

    def unload(self):
        if self.action is None:
            return
        self.iface.removePluginVectorMenu("&Vector Reclassify", self.action)
        if self.toolbar is not None:
            self.toolbar.removeAction(self.action)
            self.toolbar.deleteLater()
            self.toolbar = None
        self.action = None

    def run(self):
        dialog = VectorReclassifyDialog(self.iface.mainWindow())
        if not dialog.exec_():
            return

        try:
            config = dialog.config()
        except ValueError as exc:
            QMessageBox.critical(self.iface.mainWindow(), "Vector Reclassify", str(exc))
            return

        try:
            results = reclassify_vector_layers(config)
        except ValueError as exc:
            QMessageBox.critical(self.iface.mainWindow(), "Vector Reclassify", str(exc))
            return
        except Exception as exc:  # pragma: no cover - QGIS runtime path
            QMessageBox.critical(self.iface.mainWindow(), "Vector Reclassify", str(exc))
            return

        succeeded = [result for result in results if result.success]
        failed = [result for result in results if not result.success]

        for result in succeeded:
            QgsProject.instance().addMapLayer(result.result_layer)

        if succeeded:
            summary = "; ".join(
                f"{result.layer_name}: {result.feature_count} features "
                f"({result.matched_count} matched)"
                for result in succeeded
            )
            self.iface.messageBar().pushMessage(
                "Vector Reclassify",
                f"Completed {len(succeeded)} layer(s). {summary}",
                level=Qgis.Success,
                duration=6,
            )

        if failed:
            details = "\n".join(
                f"- {result.layer_name}: {result.error_message}" for result in failed
            )
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Vector Reclassify",
                f"{len(failed)} of {len(results)} layer(s) failed:\n{details}",
            )
