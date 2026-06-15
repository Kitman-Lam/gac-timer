import json

from PySide6.QtCore import Signal, Qt, QRect, QModelIndex
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)
from PySide6.QtWidgets import QStyleOptionButton, QStyle
from PySide6.QtGui import QPainter

class CheckableHeaderView(QHeaderView):
    checkbox_clicked = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self._is_checked = False
        self.setSectionsClickable(True)
        
    def paintSection(self, painter, rect, logicalIndex):
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex == 0:
            # 计算和表格单元格中复选框相同的位置
            y_offset = 10 + 4  # 往下移4px
            x_offset = 5  # 往右移5px
            opt = QStyleOptionButton()
            opt.rect = QRect(rect.x() + (rect.width() - 16) // 2 + x_offset, rect.y() + y_offset, 16, 16)
            opt.state = QStyle.State_Enabled | (QStyle.State_On if self._is_checked else QStyle.State_Off)
            self.style().drawControl(QStyle.CE_CheckBox, opt, painter)
            
    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if index == 0:
            self._is_checked = not self._is_checked
            self.checkbox_clicked.emit(self._is_checked)
            self.updateSection(0)
        else:
            super().mousePressEvent(event)
            
    def is_all_checked(self):
        return self._is_checked
        
    def set_all_checked(self, checked):
        if self._is_checked != checked:
            self._is_checked = checked
            self.updateSection(0)

class NoClippingDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setStyleSheet("""
                QLineEdit {
                    border: none;
                    background-color: #FFFFFF;
                    padding: 0px 6px;
                    font-size: 15px;
                    font-family: "Microsoft YaHei", "Inter", "Segoe UI", sans-serif;
                }
            """)
            editor.setFixedHeight(50)
            
            col = index.column()
            if col in (2, 3):
                editor.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
            else:
                editor.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

from app.core.database import DatabaseManager
from app.ui.theme import (
    BG_INPUT,
    BG_SURFACE,
    BORDER_DEFAULT,
    FONT_FAMILY,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class _TemplateSelectDialog(QDialog):
    def __init__(self, templates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("加载会议计划")
        self.setMinimumWidth(360)
        self._selected_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._list = QListWidget()
        self._templates = templates
        for t in templates:
            item = QListWidgetItem(t.name)
            item.setData(Qt.UserRole, t.id)
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(self.accept)
        self._list.setStyleSheet(
            f"QListWidget {{ background-color: #FFFFFF; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; outline: none; }}"
            f"QListWidget::item {{ padding: 8px 12px; border-radius: 4px; }}"
            f"QListWidget::item:selected {{ background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; }}"
            f"QListWidget::item:hover {{ background-color: {BG_SURFACE}; }}"
        )
        layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("primaryBtn")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def accept(self):
        current = self._list.currentItem()
        if current:
            self._selected_id = current.data(Qt.UserRole)
        super().accept()

    def selected_template_id(self):
        return self._selected_id


class _TemplateManageDialog(QDialog):
    edit_requested = Signal(int)

    def __init__(self, templates, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理会议计划")
        self.setMinimumWidth(360)
        self._db = db

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._list = QListWidget()
        self._templates = list(templates)
        self._refresh_list()
        self._list.setStyleSheet(
            f"QListWidget {{ background-color: #FFFFFF; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; outline: none; }}"
            f"QListWidget::item {{ padding: 8px 12px; border-radius: 4px; }}"
            f"QListWidget::item:selected {{ background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; }}"
            f"QListWidget::item:hover {{ background-color: {BG_SURFACE}; }}"
        )
        layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        edit_btn = QPushButton("编辑计划")
        edit_btn.setObjectName("primaryBtn")
        edit_btn.clicked.connect(self._on_edit)
        rename_btn = QPushButton("修改名称")
        rename_btn.setObjectName("secondaryBtn")
        rename_btn.clicked.connect(self._on_rename)
        delete_btn = QPushButton("删除选中")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.clicked.connect(self._on_delete)
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(rename_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _refresh_list(self):
        self._list.clear()
        for t in self._templates:
            item = QListWidgetItem(t.name)
            item.setData(Qt.UserRole, t.id)
            self._list.addItem(item)

    def _on_edit(self):
        current = self._list.currentItem()
        if current is None:
            QMessageBox.warning(self, "提示", "请先选择一个计划")
            return
        template_id = current.data(Qt.UserRole)
        self.edit_requested.emit(template_id)
        self.accept()

    def _on_rename(self):
        current = self._list.currentItem()
        if current is None:
            QMessageBox.warning(self, "提示", "请先选择一个计划")
            return
        template_id = current.data(Qt.UserRole)
        name, ok = QInputDialog.getText(
            self, "修改名称", "新的会议名称：",
            text=current.text()
        )
        if ok and name.strip() and name.strip() != current.text():
            self._db.update_template(template_id, name.strip())
            current.setText(name.strip())
            for t in self._templates:
                if t.id == template_id:
                    t.name = name.strip()
                    break
            QMessageBox.information(self, "提示", "名称已修改")

    def _on_delete(self):
        current = self._list.currentItem()
        if current is None:
            return
        template_id = current.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "删除计划", "确定删除该计划？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._db.delete_template(template_id)
            self._templates = [t for t in self._templates if t.id != template_id]
            self._refresh_list()


class ConfigPanel(QWidget):
    meeting_ready = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._topics: list[dict] = []
        self._topic_counter = 0
        self._editing_template_id: int | None = None
        self._editing_template_name: str = ""
        self._db = DatabaseManager()

        raw = self._db.get_setting("defaults")
        if raw:
            try:
                defaults = json.loads(raw)
                self._default_presentation = defaults.get("presentation_minutes", 10)
                self._default_qa = defaults.get("qa_minutes", 5)
            except (json.JSONDecodeError, TypeError):
                self._default_presentation = 10
                self._default_qa = 5
        else:
            self._default_presentation = 10
            self._default_qa = 5

        self._setup_ui()

    def reload_defaults(self):
        raw = self._db.get_setting("defaults")
        if raw:
            try:
                defaults = json.loads(raw)
                self._default_presentation = defaults.get("presentation_minutes", 10)
                self._default_qa = defaults.get("qa_minutes", 5)
            except (json.JSONDecodeError, TypeError):
                self._default_presentation = 10
                self._default_qa = 5
        else:
            self._default_presentation = 10
            self._default_qa = 5

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(12)

        meeting_name_label = QLabel("会议名称")
        meeting_name_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SMALL}px; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        main_layout.addWidget(meeting_name_label)

        self._meeting_name_edit = QLineEdit()
        self._meeting_name_edit.setPlaceholderText("输入会议名称")
        self._meeting_name_edit.setStyleSheet(
            f"QLineEdit {{ background-color: {BG_INPUT}; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER_DEFAULT}; border-radius: 6px; "
            f"padding: 12px 16px; font-size: 16px; font-family: '{FONT_FAMILY}'; }}"
            f"QLineEdit:focus {{ border: 2px solid {PRIMARY}; }}"
        )
        main_layout.addWidget(self._meeting_name_edit)

        self._empty_label = QLabel("\n暂无议题，请在下方添加")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_MEDIUM}px; "
            f"font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        main_layout.addWidget(self._empty_label, 1)

        self._topic_list = QTableWidget()
        self._topic_list.setColumnCount(4)
        self._topic_list.setHorizontalHeaderLabels(["", "议题", "汇报时间（分钟）", "讨论时间（分钟）"])
        self._topic_checkable_header = CheckableHeaderView(self._topic_list)
        self._topic_list.setHorizontalHeader(self._topic_checkable_header)
        self._topic_checkable_header.checkbox_clicked.connect(self._on_header_clicked)
        self._topic_list.verticalHeader().setVisible(False)
        self._topic_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._topic_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._topic_list.setAlternatingRowColors(True)
        self._topic_list.setDragDropMode(QAbstractItemView.InternalMove)
        self._topic_list.setDefaultDropAction(Qt.MoveAction)
        self._topic_list.setDragEnabled(True)
        self._topic_list.setAcceptDrops(True)
        self._topic_list.setDropIndicatorShown(True)
        self._topic_list.setShowGrid(False)
        self._topic_list.verticalHeader().setDefaultSectionSize(50)
        self._topic_list.setItemDelegate(NoClippingDelegate())
        self._topic_list.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        self._topic_list.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Fixed
        )
        self._topic_list.setColumnWidth(0, 36)
        self._topic_list.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self._topic_list.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self._topic_list.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self._topic_list.setStyleSheet(
            f"QTableWidget {{ background-color: #FFFFFF; "
            f"border: 1px solid {BORDER_DEFAULT}; "
            f"border-radius: 8px; gridline-color: transparent; outline: none; }}"
            f"QTableWidget::item {{ padding: 10px 12px; border: none; }}"
            f"QTableWidget::item:selected {{ "
            f"background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; }}"
            f"QTableWidget::item:alternate {{ background-color: {BG_SURFACE}; }}"
            f"QTableWidget QLineEdit {{ padding: 15px 6px; border: none; "
            f"background-color: #FFFFFF; min-height: 50px; "
            f"font-size: {FONT_SIZE_MEDIUM}px; font-family: '{FONT_FAMILY}'; }}"
        )
        self._topic_list.model().rowsMoved.connect(self._on_topics_reordered)
        self._topic_list.cellDoubleClicked.connect(self._on_topic_double_clicked)
        self._topic_list.cellChanged.connect(self._on_topic_cell_changed)
        self._topic_list.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._topic_list.setVisible(False)
        main_layout.addWidget(self._topic_list, 1)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)

        self._save_template_btn = QPushButton("保存会议计划")
        self._save_template_btn.setObjectName("secondaryBtn")
        self._save_template_btn.clicked.connect(self._on_save_template)
        row1_layout.addWidget(self._save_template_btn)

        self._load_template_btn = QPushButton("加载会议计划")
        self._load_template_btn.setObjectName("secondaryBtn")
        self._load_template_btn.clicked.connect(self._on_load_template)
        row1_layout.addWidget(self._load_template_btn)

        self._manage_template_btn = QPushButton("管理会议计划")
        self._manage_template_btn.setObjectName("secondaryBtn")
        self._manage_template_btn.clicked.connect(self._on_manage_template)
        row1_layout.addWidget(self._manage_template_btn)

        self._delete_btn = QPushButton("删除选中")
        self._delete_btn.setObjectName("secondaryBtn")
        self._delete_btn.clicked.connect(self._on_delete_topic)
        row1_layout.addWidget(self._delete_btn)

        self._add_btn = QPushButton("添加议题")
        self._add_btn.setObjectName("primaryBtn")
        self._add_btn.clicked.connect(self._on_add_topic)
        row1_layout.addWidget(self._add_btn)

        main_layout.addLayout(row1_layout)

        self._start_btn = QPushButton("开始会议")
        self._start_btn.setObjectName("primaryBtn")
        self._start_btn.setFixedHeight(36)
        self._start_btn.clicked.connect(self._on_start_meeting)
        main_layout.addWidget(self._start_btn)

    def _refresh_topic_list(self):
        self._topic_list.setRowCount(0)
        if not self._topics:
            self._empty_label.setVisible(True)
            self._topic_list.setVisible(False)
            return
        self._empty_label.setVisible(False)
        self._topic_list.setVisible(True)
        self._topic_list.setRowCount(len(self._topics))
        for i, topic_data in enumerate(self._topics):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(
                Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
            )
            chk_item.setCheckState(Qt.Unchecked)
            self._topic_list.setItem(i, 0, chk_item)

            name_item = QTableWidgetItem(topic_data["name"])
            name_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable
                | Qt.ItemIsEditable | Qt.ItemIsDragEnabled
            )
            self._topic_list.setItem(i, 1, name_item)

            pres_item = QTableWidgetItem(str(topic_data["presentation_minutes"]))
            pres_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable
                | Qt.ItemIsEditable | Qt.ItemIsDragEnabled
            )
            pres_item.setTextAlignment(Qt.AlignCenter)
            self._topic_list.setItem(i, 2, pres_item)

            qa_item = QTableWidgetItem(str(topic_data["qa_minutes"]))
            qa_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable
                | Qt.ItemIsEditable | Qt.ItemIsDragEnabled
            )
            qa_item.setTextAlignment(Qt.AlignCenter)
            self._topic_list.setItem(i, 3, qa_item)

    def _on_topic_double_clicked(self, row: int, col: int):
        if col in (1, 2, 3):
            item = self._topic_list.item(row, col)
            if item:
                self._topic_list.editItem(item)

    def _on_topic_cell_changed(self, row: int, col: int):
        if row < 0 or row >= len(self._topics):
            return
        if col == 1:
            item = self._topic_list.item(row, 1)
            if item:
                new_name = item.text().strip()
                if new_name:
                    self._topics[row]["name"] = new_name
                else:
                    item.setText(self._topics[row]["name"])
        elif col == 2:
            item = self._topic_list.item(row, 2)
            if item:
                try:
                    val = int(item.text().strip())
                    if val > 0:
                        self._topics[row]["presentation_minutes"] = val
                    else:
                        item.setText(str(self._topics[row]["presentation_minutes"]))
                except ValueError:
                    item.setText(str(self._topics[row]["presentation_minutes"]))
        elif col == 3:
            item = self._topic_list.item(row, 3)
            if item:
                try:
                    val = int(item.text().strip())
                    if val > 0:
                        self._topics[row]["qa_minutes"] = val
                    else:
                        item.setText(str(self._topics[row]["qa_minutes"]))
                except ValueError:
                    item.setText(str(self._topics[row]["qa_minutes"]))

    def _on_header_clicked(self, checked: bool):
        new_state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self._topic_list.rowCount()):
            self._topic_list.item(i, 0).setCheckState(new_state)

    def _on_selection_changed(self, selected, deselected):
        for index in selected.indexes():
            row = index.row()
            chk_item = self._topic_list.item(row, 0)
            if chk_item:
                chk_item.setCheckState(Qt.Checked)
        for index in deselected.indexes():
            row = index.row()
            chk_item = self._topic_list.item(row, 0)
            if chk_item:
                chk_item.setCheckState(Qt.Unchecked)

    def _on_add_topic(self):
        self._topic_counter += 1
        name = f"议题 {self._topic_counter}"

        topic_data = {
            "name": name,
            "presentation_minutes": self._default_presentation,
            "qa_minutes": self._default_qa,
        }
        self._topics.append(topic_data)
        self._refresh_topic_list()
        self._topic_list.selectRow(self._topic_list.rowCount() - 1)

    def _on_delete_topic(self):
        rows_to_delete = []
        for i in range(self._topic_list.rowCount()):
            chk_item = self._topic_list.item(i, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                rows_to_delete.append(i)

        if not rows_to_delete:
            QMessageBox.warning(self, "提示", "请先勾选要删除的议题")
            return

        count = len(rows_to_delete)
        reply = QMessageBox.question(
            self, "删除议题",
            f"确定删除选中的 {count} 个议题？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in sorted(rows_to_delete, reverse=True):
                self._topics.pop(row)
            self._refresh_topic_list()

    def _on_topics_reordered(self):
        new_topics = []
        for i in range(self._topic_list.rowCount()):
            name_item = self._topic_list.item(i, 1)
            pres_item = self._topic_list.item(i, 2)
            qa_item = self._topic_list.item(i, 3)
            if name_item:
                name = name_item.text().strip()
                pres = int(pres_item.text().strip()) if pres_item else self._default_presentation
                qa = int(qa_item.text().strip()) if qa_item else self._default_qa
                new_topics.append({
                    "name": name,
                    "presentation_minutes": pres,
                    "qa_minutes": qa,
                })
        self._topics = new_topics

    def _on_save_template(self):
        if not self._topics:
            QMessageBox.warning(self, "提示", "当前没有议题可保存")
            return

        from datetime import datetime
        name = self._meeting_name_edit.text().strip()
        if not name:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self._editing_template_id is not None:
            self._db.delete_template_topics(self._editing_template_id)
            self._db.update_template(self._editing_template_id, name)
            for i, topic_data in enumerate(self._topics):
                self._db.create_template_topic(
                    self._editing_template_id, i,
                    topic_data["name"],
                    topic_data["presentation_minutes"],
                    topic_data["qa_minutes"],
                )
            self._editing_template_id = None
            self._editing_template_name = ""
            self._save_template_btn.setText("保存会议计划")
            self._save_template_btn.setStyleSheet("")
            QMessageBox.information(self, "提示", "会议计划已更新")
            self._clear_meeting_form()
            return

        template = self._db.create_template(name)
        for i, topic_data in enumerate(self._topics):
            self._db.create_template_topic(
                template.id, i,
                topic_data["name"],
                topic_data["presentation_minutes"],
                topic_data["qa_minutes"],
            )
        QMessageBox.information(self, "提示", "会议计划已保存")
        self._clear_meeting_form()

    def _on_load_template(self):
        templates = self._db.list_templates()
        if not templates:
            QMessageBox.information(self, "提示", "暂无会议计划")
            return
        dialog = _TemplateSelectDialog(templates, self)
        if dialog.exec() == QDialog.Accepted:
            template_id = dialog.selected_template_id()
            if template_id is not None:
                template = self._db.get_template(template_id)
                if template:
                    self._meeting_name_edit.setText(template.name)
                template_topics = self._db.get_template_topics(template_id)
                topics = [
                    {
                        "name": t.name,
                        "presentation_minutes": t.presentation_minutes,
                        "qa_minutes": t.qa_minutes,
                    }
                    for t in template_topics
                ]
                self.set_topics_from_template(topics)

    def _on_manage_template(self):
        templates = self._db.list_templates()
        dialog = _TemplateManageDialog(templates, self._db, self)
        dialog.edit_requested.connect(self._on_edit_template)
        dialog.exec()

    def _on_edit_template(self, template_id: int):
        template = self._db.get_template(template_id)
        if template is None:
            return
        self._editing_template_id = template_id
        self._editing_template_name = template.name
        self._meeting_name_edit.setText(template.name)

        template_topics = self._db.get_template_topics(template_id)
        self._topics = [
            {
                "name": t.name,
                "presentation_minutes": t.presentation_minutes,
                "qa_minutes": t.qa_minutes,
            }
            for t in template_topics
        ]
        self._topic_counter = len(self._topics)
        self._refresh_topic_list()

        self._save_template_btn.setText("更新计划")
        self._save_template_btn.setStyleSheet(
            f"QPushButton#secondaryBtn {{ background-color: {PRIMARY_LIGHT}; "
            f"color: {PRIMARY}; border: 1px solid {PRIMARY}; }}"
        )

    def _on_start_meeting(self):
        from datetime import datetime
        meeting_name = self._meeting_name_edit.text().strip()
        if not meeting_name:
            meeting_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not self._topics:
            QMessageBox.warning(self, "提示", "请至少添加一个议题")
            return
        config = self.get_meeting_config()
        config["name"] = meeting_name
        print("[DEBUG] ConfigPanel emitting meeting_ready:", config)
        self.meeting_ready.emit(config)
        self._clear_meeting_form()

    def _clear_meeting_form(self):
        self._meeting_name_edit.clear()
        self._topics = []
        self._topic_counter = 0
        self._editing_template_id = None
        self._editing_template_name = ""
        self._save_template_btn.setText("保存会议计划")
        self._save_template_btn.setStyleSheet("")
        self._refresh_topic_list()

    def get_meeting_config(self) -> dict:
        return {
            "name": self._meeting_name_edit.text().strip(),
            "topics": [
                {
                    "name": t["name"],
                    "presentation_minutes": t["presentation_minutes"],
                    "qa_minutes": t["qa_minutes"],
                }
                for t in self._topics
            ],
        }

    def load_meeting(self, meeting_id: int):
        meeting = self._db.get_meeting(meeting_id)
        if meeting is None:
            return
        self._meeting_name_edit.setText(meeting.name)
        topics = self._db.get_topics_by_meeting(meeting_id)
        self._topics = [
            {
                "name": t.name,
                "presentation_minutes": t.presentation_minutes,
                "qa_minutes": t.qa_minutes,
            }
            for t in topics
        ]
        self._topic_counter = len(self._topics)
        self._refresh_topic_list()

    def set_topics_from_template(self, template_topics: list):
        self._topics = [
            {
                "name": t["name"],
                "presentation_minutes": t["presentation_minutes"],
                "qa_minutes": t["qa_minutes"],
            }
            for t in template_topics
        ]
        self._topic_counter = len(self._topics)
        self._refresh_topic_list()