from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import Qgis

from .joiner import join_layers_by_two_fields
from .join_2field_dialog import JoinTwoFieldDialog


class JoinTwoFieldPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.toolbar = None
        self.plugin_dir = Path(__file__).resolve().parent

    def initGui(self):
        icon_path = self.plugin_dir / "icon.png"
        self.action = QAction(
            QIcon(str(icon_path)),
            "Join Field 2 Field",
            self.iface.mainWindow(),
        )
        self.action.setObjectName("joinTwoFieldAction")
        self.action.setStatusTip(
            "Join attributes between two layers matching on two fields at once"
        )
        self.action.triggered.connect(self.run)
        self.toolbar = self.iface.addToolBar("Join Field 2 Field")
        self.toolbar.setObjectName("JoinTwoFieldToolbar")
        self.toolbar.addAction(self.action)
        self.iface.addPluginToVectorMenu("&Join Field 2 Field", self.action)

    def unload(self):
        if self.action is None:
            return
        self.iface.removePluginVectorMenu("&Join Field 2 Field", self.action)
        if self.toolbar is not None:
            self.toolbar.removeAction(self.action)
            self.toolbar.deleteLater()
            self.toolbar = None
        self.action = None

    def run(self):
        dialog = JoinTwoFieldDialog(self.iface.mainWindow())
        if not dialog.exec_():
            return

        try:
            config = dialog.config()
            result_layer, feature_count, matched_count = join_layers_by_two_fields(config)
        except ValueError as exc:
            QMessageBox.critical(self.iface.mainWindow(), "Join Field 2 Field", str(exc))
            return
        except Exception as exc:  # pragma: no cover - QGIS runtime path
            QMessageBox.critical(self.iface.mainWindow(), "Join Field 2 Field", str(exc))
            return

        self.iface.messageBar().pushMessage(
            "Join Field 2 Field",
            (
                f"Created layer '{result_layer.name()}' with {feature_count} features "
                f"({matched_count} matched)."
            ),
            level=Qgis.Success,
            duration=5,
        )