from __future__ import annotations

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from qgis.core import QgsMapLayerType, QgsProject, QgsVectorLayer

from .reclassifier import ReclassifyConfig


ITEM_KIND_ROLE = Qt.UserRole
ITEM_KIND_GROUP = "group"
ITEM_KIND_SOURCE = "source"
UNASSIGNED_GROUP_LABEL = "Unassigned"


class RuleTreeWidget(QTreeWidget):
    rulesDropped = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.rulesDropped.emit()


class VectorReclassifyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vector Reclassify")
        self.resize(760, 520)

        self.layer_combo = QComboBox()
        self.source_field_combo = QComboBox()
        self.target_field_edit = QLineEdit("reclass")
        self.output_type_combo = QComboBox()
        self.output_type_combo.addItems(["String", "Integer", "Double"])
        self.keep_unmatched_checkbox = QCheckBox(
            "Keep original value when no rule matches"
        )
        self.keep_unmatched_checkbox.setChecked(True)
        self.selected_only_checkbox = QCheckBox("Use selected features only")
        self.temporary_output_checkbox = QCheckBox("Save as temporary file")
        self.temporary_output_checkbox.setChecked(True)
        self.output_path_edit = QLineEdit()
        self.rule_mode_combo = QComboBox()
        self.rule_mode_combo.addItems(["Table", "Drag and drop"])
        self.rule_mode_stack = QStackedWidget()
        self.rules_table = QTableWidget(0, 2)
        self.rules_table.setHorizontalHeaderLabels(["From value", "To value"])
        self.rules_table.horizontalHeader().setStretchLastSection(True)
        self.rules_tree = RuleTreeWidget()
        self.rules_tree.setHeaderLabel("Drag source values into target classes")
        self.rules_tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.rules_tree.setDragEnabled(True)
        self.rules_tree.setAcceptDrops(True)
        self.rules_tree.setDropIndicatorShown(True)
        self.rules_tree.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self._known_target_values = []
        self._active_rule_mode = "Table"
        self._updating_rule_view = False

        self._build_layout()
        self._connect_signals()
        self._rebuild_rule_editor([])
        self.refresh_layers()

    def _build_layout(self):
        main_layout = QVBoxLayout(self)

        form_group = QGroupBox("Inputs")
        form_layout = QFormLayout(form_group)
        form_layout.addRow("Vector layer", self.layer_combo)
        form_layout.addRow("Source field", self.source_field_combo)
        form_layout.addRow("New field name", self.target_field_edit)
        form_layout.addRow("Output field type", self.output_type_combo)
        form_layout.addRow("", self.keep_unmatched_checkbox)
        form_layout.addRow("", self.selected_only_checkbox)
        main_layout.addWidget(form_group)

        rules_group = QGroupBox("Reclassify rules")
        rules_layout = QVBoxLayout(rules_group)
        rules_layout.addWidget(
            QLabel("Create exact-match mappings from source values to target values.")
        )
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Editing mode"))
        mode_layout.addWidget(self.rule_mode_combo)
        mode_layout.addStretch(1)
        rules_layout.addLayout(mode_layout)

        table_page = QVBoxLayout()
        table_page.addWidget(self.rules_table)

        self.table_rule_buttons = QHBoxLayout()
        self.add_rule_button = QPushButton("Add rule")
        self.remove_rule_button = QPushButton("Remove selected")
        self.load_unique_button = QPushButton("Load unique values")
        self.table_rule_buttons.addWidget(self.add_rule_button)
        self.table_rule_buttons.addWidget(self.remove_rule_button)
        self.table_rule_buttons.addWidget(self.load_unique_button)
        self.table_rule_buttons.addStretch(1)
        table_page.addLayout(self.table_rule_buttons)

        table_page_widget = QGroupBox()
        table_page_widget.setFlat(True)
        table_page_widget.setLayout(table_page)

        drag_drop_page = QVBoxLayout()
        drag_drop_page.addWidget(
            QLabel("Create target classes, then drag source values under each class.")
        )
        drag_drop_page.addWidget(self.rules_tree)

        self.drag_drop_rule_buttons = QHBoxLayout()
        self.add_class_button = QPushButton("Add class")
        self.remove_drag_item_button = QPushButton("Remove selected")
        self.drag_drop_load_unique_button = QPushButton("Load unique values")
        self.drag_drop_rule_buttons.addWidget(self.add_class_button)
        self.drag_drop_rule_buttons.addWidget(self.remove_drag_item_button)
        self.drag_drop_rule_buttons.addWidget(self.drag_drop_load_unique_button)
        self.drag_drop_rule_buttons.addStretch(1)
        drag_drop_page.addLayout(self.drag_drop_rule_buttons)

        drag_drop_page_widget = QGroupBox()
        drag_drop_page_widget.setFlat(True)
        drag_drop_page_widget.setLayout(drag_drop_page)

        self.rule_mode_stack.addWidget(table_page_widget)
        self.rule_mode_stack.addWidget(drag_drop_page_widget)
        rules_layout.addWidget(self.rule_mode_stack)
        main_layout.addWidget(rules_group)

        output_group = QGroupBox("Output")
        output_layout = QGridLayout(output_group)
        output_layout.addWidget(self.temporary_output_checkbox, 0, 0, 1, 3)
        self.output_format_label = QLabel("Temporary file type")
        output_layout.addWidget(self.output_format_label, 1, 0)
        self.output_format_value_label = QLabel("Shapefile (.shp)")
        output_layout.addWidget(self.output_format_value_label, 1, 1, 1, 2)
        output_layout.addWidget(self.output_path_edit, 2, 1)
        self.browse_button = QPushButton("Browse")
        output_layout.addWidget(self.browse_button, 2, 2)
        output_layout.addWidget(QLabel("Output file"), 2, 0)
        main_layout.addWidget(output_group)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.layer_combo.currentIndexChanged.connect(self._populate_fields)
        self.rule_mode_combo.currentTextChanged.connect(self._switch_rule_mode)
        self.add_rule_button.clicked.connect(self._add_rule_row)
        self.remove_rule_button.clicked.connect(self._remove_selected_rows)
        self.load_unique_button.clicked.connect(self._load_unique_values)
        self.add_class_button.clicked.connect(self._add_target_class)
        self.remove_drag_item_button.clicked.connect(self._remove_drag_drop_selection)
        self.drag_drop_load_unique_button.clicked.connect(self._load_unique_values)
        self.browse_button.clicked.connect(self._browse_output_path)
        self.temporary_output_checkbox.toggled.connect(self._sync_output_mode)
        self.rules_table.itemChanged.connect(self._refresh_target_value_dropdowns)
        self.rules_tree.itemChanged.connect(self._handle_drag_drop_item_changed)
        self.rules_tree.rulesDropped.connect(self._normalize_drag_drop_tree)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def refresh_layers(self):
        self.layer_combo.clear()
        vector_layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if (
                isinstance(layer, QgsVectorLayer) and
                layer.type() == QgsMapLayerType.VectorLayer
            ):
                vector_layers.append(layer)

        for layer in sorted(vector_layers, key=lambda item: item.name().lower()):
            self.layer_combo.addItem(layer.name(), layer.id())

        self._populate_fields()
        self._sync_output_mode()

    def config(self) -> ReclassifyConfig:
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            raise ValueError(
                "No vector layer is available in the current QGIS project."
            )

        output_path = self.output_path_edit.text().strip() or None
        if not self.temporary_output_checkbox.isChecked() and not output_path:
            raise ValueError("Output path is required.")

        rules = self._read_rules()
        return ReclassifyConfig(
            layer_id=layer_id,
            source_field=self.source_field_combo.currentText(),
            target_field=self.target_field_edit.text().strip(),
            rules=rules,
            keep_unmatched=self.keep_unmatched_checkbox.isChecked(),
            selected_only=self.selected_only_checkbox.isChecked(),
            output_path=output_path,
            output_type=self.output_type_combo.currentText(),
            output_format=self._selected_output_format(output_path),
            temporary_output=self.temporary_output_checkbox.isChecked(),
        )

    def accept(self):
        try:
            self.config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid input", str(exc))
            return
        super().accept()

    def _populate_fields(self):
        self.source_field_combo.clear()
        layer = self._current_layer()
        if layer is None:
            return
        for field in layer.fields():
            self.source_field_combo.addItem(field.name())

    def _add_rule_row(self, source_value: str = "", target_value: str = ""):
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)
        self.rules_table.setItem(row, 0, QTableWidgetItem(source_value))
        self._set_target_value_editor(row, target_value)
        self._refresh_target_value_dropdowns()

    def _remove_selected_rows(self):
        selected_rows = sorted(
            {index.row() for index in self.rules_table.selectedIndexes()},
            reverse=True,
        )
        for row in selected_rows:
            self.rules_table.removeRow(row)
        self._refresh_target_value_dropdowns()

    def _load_unique_values(self):
        layer = self._current_layer()
        source_field = self.source_field_combo.currentText()
        if layer is None or not source_field:
            QMessageBox.warning(
                self,
                "Missing input",
                "Choose a vector layer and source field first.",
            )
            return

        field_index = layer.fields().indexOf(source_field)
        unique_values = sorted(
            layer.uniqueValues(field_index),
            key=lambda value: str(value),
        )
        rules = [("" if value is None else str(value), "") for value in unique_values]
        self._rebuild_rule_editor(rules)

    def _browse_output_path(self):
        if self.temporary_output_checkbox.isChecked():
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save reclassified layer",
            self.output_path_edit.text().strip(),
            "GeoPackage (*.gpkg);;Shapefile (*.shp);;GeoJSON (*.geojson)",
        )
        if path:
            self.output_path_edit.setText(path)

    def _sync_output_mode(self):
        temporary_output = self.temporary_output_checkbox.isChecked()
        self.output_format_label.setVisible(temporary_output)
        self.output_format_value_label.setVisible(temporary_output)
        self.output_path_edit.setEnabled(not temporary_output)
        self.browse_button.setEnabled(not temporary_output)
        if temporary_output:
            self.output_path_edit.setText("Temporary file (.shp)")
            return
        if self.output_path_edit.text().startswith("Temporary file ("):
            self.output_path_edit.clear()

    def _read_rules(self) -> dict[str, str]:
        rules = self._capture_rule_rows()
        self._sync_known_target_values(rules)
        if self.rule_mode_combo.currentText() == "Table":
            self._rebuild_rule_editor(rules)

        rule_map = {}
        for row, (source_value, target_value) in enumerate(rules, start=1):
            source_value = source_value.strip()
            target_value = target_value.strip()
            if not source_value and not target_value:
                continue
            if not source_value or not target_value:
                raise ValueError(
                    f"Rule row {row} must contain both source and target values."
                )
            if source_value in rule_map:
                raise ValueError(
                    f"Rule row {row} duplicates source value '{source_value}'."
                )
            rule_map[source_value] = target_value
        return rule_map

    def _capture_rule_rows(self) -> list[tuple[str, str]]:
        if self._active_rule_mode == "Drag and drop":
            return self._capture_drag_drop_rows()

        rules = []
        for row in range(self.rules_table.rowCount()):
            source_item = self.rules_table.item(row, 0)
            source_value = source_item.text().strip() if source_item else ""
            target_value = self._target_value_text(row)
            rules.append((source_value, target_value))
        return rules

    def _capture_drag_drop_rows(self) -> list[tuple[str, str]]:
        rules = []
        self._sync_known_target_values_from_tree()
        for index in range(self.rules_tree.topLevelItemCount()):
            group_item = self.rules_tree.topLevelItem(index)
            group_name = self._group_name(group_item)
            if group_name == UNASSIGNED_GROUP_LABEL:
                for child_index in range(group_item.childCount()):
                    source_item = group_item.child(child_index)
                    rules.append((source_item.text(0).strip(), ""))
                continue
            for child_index in range(group_item.childCount()):
                source_item = group_item.child(child_index)
                rules.append((source_item.text(0).strip(), group_name))
        return rules

    def _add_target_class(self):
        value, accepted = QInputDialog.getText(self, "Add class", "Class name")
        class_name = value.strip() if accepted else ""
        if not class_name:
            return
        if class_name in self._known_target_values:
            QMessageBox.warning(self, "Duplicate class", "This class already exists.")
            return
        self._known_target_values.append(class_name)
        self._rebuild_rule_editor(self._capture_rule_rows())

    def _remove_drag_drop_selection(self):
        current_item = self.rules_tree.currentItem()
        if current_item is None:
            return

        item_kind = current_item.data(0, ITEM_KIND_ROLE)
        unassigned_item = self._unassigned_group_item()
        if item_kind == ITEM_KIND_SOURCE:
            if (
                current_item.parent() is not None and
                current_item.parent() != unassigned_item
            ):
                current_item.parent().removeChild(current_item)
                unassigned_item.addChild(current_item)
            return

        group_name = self._group_name(current_item)
        if group_name == UNASSIGNED_GROUP_LABEL:
            return

        while current_item.childCount() > 0:
            child = current_item.takeChild(0)
            unassigned_item.addChild(child)
        index = self.rules_tree.indexOfTopLevelItem(current_item)
        self.rules_tree.takeTopLevelItem(index)
        self._known_target_values = [
            value for value in self._known_target_values if value != group_name
        ]
        self._normalize_drag_drop_tree()

    def _switch_rule_mode(self, mode_name: str):
        if self._updating_rule_view or mode_name == self._active_rule_mode:
            return

        rules = self._capture_rule_rows()
        self._sync_known_target_values(rules)
        self._active_rule_mode = mode_name
        self.rule_mode_stack.setCurrentIndex(0 if mode_name == "Table" else 1)
        self._rebuild_rule_editor(rules)

    def _rebuild_rule_editor(self, rules: list[tuple[str, str]]):
        self._sync_known_target_values(rules)
        self._updating_rule_view = True
        try:
            if self._active_rule_mode == "Drag and drop":
                self._populate_drag_drop_rules(rules)
            else:
                self._populate_table_rules(rules)
        finally:
            self._updating_rule_view = False

    def _populate_table_rules(self, rules: list[tuple[str, str]]):
        self.rules_table.blockSignals(True)
        self.rules_table.setRowCount(0)
        for source_value, target_value in rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            self.rules_table.setItem(row, 0, QTableWidgetItem(source_value))
            self._set_target_value_editor(row, target_value)
        self.rules_table.blockSignals(False)
        self._refresh_target_value_dropdowns()

    def _populate_drag_drop_rules(self, rules: list[tuple[str, str]]):
        self.rules_tree.blockSignals(True)
        self.rules_tree.clear()

        unassigned_item = self._create_group_item(
            UNASSIGNED_GROUP_LABEL,
            editable=False,
        )
        self.rules_tree.addTopLevelItem(unassigned_item)

        group_items = {UNASSIGNED_GROUP_LABEL: unassigned_item}
        for target_value in self._known_target_values:
            if target_value == UNASSIGNED_GROUP_LABEL:
                continue
            group_item = self._create_group_item(target_value, editable=True)
            group_items[target_value] = group_item
            self.rules_tree.addTopLevelItem(group_item)

        for source_value, target_value in rules:
            source_text = source_value.strip()
            target_text = target_value.strip()
            if not source_text and not target_text:
                continue
            parent_item = group_items.get(target_text, unassigned_item)
            parent_item.addChild(self._create_source_item(source_text))

        self.rules_tree.expandAll()
        self.rules_tree.blockSignals(False)

    def _create_group_item(self, label: str, editable: bool) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label])
        item.setData(0, ITEM_KIND_ROLE, ITEM_KIND_GROUP)
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled
        if editable:
            flags |= Qt.ItemIsEditable
        item.setFlags(flags)
        return item

    def _create_source_item(self, source_value: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([source_value])
        item.setData(0, ITEM_KIND_ROLE, ITEM_KIND_SOURCE)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        return item

    def _sync_known_target_values(self, rules: list[tuple[str, str]]):
        ordered_values = []
        seen = set()
        for value in self._known_target_values:
            cleaned = value.strip()
            if cleaned and cleaned != UNASSIGNED_GROUP_LABEL and cleaned not in seen:
                seen.add(cleaned)
                ordered_values.append(cleaned)
        for _source_value, target_value in rules:
            cleaned = target_value.strip()
            if cleaned and cleaned != UNASSIGNED_GROUP_LABEL and cleaned not in seen:
                seen.add(cleaned)
                ordered_values.append(cleaned)
        self._known_target_values = ordered_values

    def _sync_known_target_values_from_tree(self):
        values = []
        for index in range(self.rules_tree.topLevelItemCount()):
            group_name = self._group_name(self.rules_tree.topLevelItem(index))
            if group_name and group_name != UNASSIGNED_GROUP_LABEL:
                values.append(group_name)
        self._sync_known_target_values([("", value) for value in values])

    def _handle_drag_drop_item_changed(self, item: QTreeWidgetItem, _column: int):
        if self._updating_rule_view or item.data(0, ITEM_KIND_ROLE) != ITEM_KIND_GROUP:
            return
        self._normalize_drag_drop_tree()

    def _normalize_drag_drop_tree(self):
        if self._updating_rule_view:
            return

        rules = []
        group_names = []

        def visit(item: QTreeWidgetItem, current_group: str = ""):
            item_kind = item.data(0, ITEM_KIND_ROLE)
            item_text = item.text(0).strip()
            if item_kind == ITEM_KIND_GROUP:
                group_name = item_text or "Class"
                if current_group and current_group != UNASSIGNED_GROUP_LABEL:
                    group_name = current_group
                if (
                    group_name != UNASSIGNED_GROUP_LABEL and
                    group_name not in group_names
                ):
                    group_names.append(group_name)
                for child_index in range(item.childCount()):
                    visit(item.child(child_index), group_name)
                return

            source_text = item_text
            if source_text:
                target_value = (
                    "" if current_group == UNASSIGNED_GROUP_LABEL else current_group
                )
                rules.append((source_text, target_value))
            for child_index in range(item.childCount()):
                visit(item.child(child_index), current_group)

        for index in range(self.rules_tree.topLevelItemCount()):
            visit(self.rules_tree.topLevelItem(index), UNASSIGNED_GROUP_LABEL)

        self._known_target_values = []
        self._sync_known_target_values([("", value) for value in group_names] + rules)
        self._populate_drag_drop_rules(rules)

    def _group_name(self, item: QTreeWidgetItem | None) -> str:
        if item is None:
            return ""
        label = item.text(0).strip()
        if not label:
            return "Class"
        return label

    def _unassigned_group_item(self) -> QTreeWidgetItem | None:
        for index in range(self.rules_tree.topLevelItemCount()):
            item = self.rules_tree.topLevelItem(index)
            if self._group_name(item) == UNASSIGNED_GROUP_LABEL:
                return item
        return None

    def _set_target_value_editor(self, row: int, target_value: str = ""):
        combo_box = QComboBox()
        combo_box.setEditable(True)
        combo_box.setInsertPolicy(QComboBox.NoInsert)
        combo_box.lineEdit().editingFinished.connect(
            self._refresh_target_value_dropdowns
        )
        combo_box.activated.connect(self._refresh_target_value_dropdowns)
        self.rules_table.setCellWidget(row, 1, combo_box)
        self._populate_target_value_dropdown(combo_box, target_value)

    def _refresh_target_value_dropdowns(self, *_args):
        if self._updating_rule_view:
            return
        self._sync_known_target_values(
            [
                ("", self._target_value_text(row))
                for row in range(self.rules_table.rowCount())
            ]
        )
        target_values = list(self._known_target_values)
        for row in range(self.rules_table.rowCount()):
            combo_box = self.rules_table.cellWidget(row, 1)
            if combo_box is None:
                continue
            current_value = combo_box.currentText().strip()
            self._populate_target_value_dropdown(
                combo_box,
                current_value,
                target_values,
            )

    def _populate_target_value_dropdown(
        self,
        combo_box: QComboBox,
        current_value: str,
        target_values: list[str] | None = None,
    ):
        values = list(target_values or self._known_target_values)
        if current_value and current_value not in values:
            values.append(current_value)

        combo_box.blockSignals(True)
        combo_box.clear()
        combo_box.addItem("")
        for value in values:
            combo_box.addItem(value)
        combo_box.setCurrentText(current_value)
        combo_box.blockSignals(False)

    def _target_value_text(self, row: int) -> str:
        combo_box = self.rules_table.cellWidget(row, 1)
        if combo_box is None:
            return ""
        return combo_box.currentText().strip()

    def _current_layer(self) -> QgsVectorLayer | None:
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            return None
        layer = QgsProject.instance().mapLayer(layer_id)
        return layer if isinstance(layer, QgsVectorLayer) else None

    def _selected_output_format(self, output_path: str | None) -> str:
        if self.temporary_output_checkbox.isChecked():
            return "Shapefile"
        if not output_path:
            raise ValueError("Output path is required.")

        suffix = output_path.lower()
        if suffix.endswith(".gpkg"):
            return "GeoPackage"
        if suffix.endswith(".shp"):
            return "Shapefile"
        if suffix.endswith(".geojson") or suffix.endswith(".json"):
            return "GeoJSON"
        raise ValueError("Output file must end with .gpkg, .shp, or .geojson.")
