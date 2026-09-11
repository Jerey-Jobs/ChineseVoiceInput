"""待办事项悬浮窗 — 可拖拽、置顶固定在桌面上的待办列表"""

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QCheckBox, QApplication
)


class TodoFloatWindow(QWidget):
    """待办事项悬浮窗：无边框、置顶、可拖拽"""

    closed = pyqtSignal()

    def __init__(self, todo_items=None, on_change=None, on_mark_done=None):
        super().__init__()
        self._on_change = on_change
        self._on_mark_done = on_mark_done
        self._dragging = False
        self._drag_position = None

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(280, 340)

        self.setStyleSheet("""
            QWidget#todo_card {
                background: rgba(255, 255, 255, 235);
                border: 1px solid #e0e0e0;
                border-radius: 14px;
            }
            QLabel#todo_title {
                font-size: 11pt; font-weight: bold; color: #1d1d1f;
            }
            QPushButton#todo_close {
                background: transparent; border: none; color: #8e8e93;
                font-size: 12pt; font-weight: bold;
            }
            QPushButton#todo_close:hover { color: #ff3b30; }
            QPushButton#todo_sync {
                background: #e8f0fe; border: 1px solid #007aff; border-radius: 6px;
                color: #007aff; font-size: 9pt; font-weight: bold; padding: 2px;
            }
            QPushButton#todo_sync:hover { background: #d0e4fc; }
            QLineEdit#todo_input {
                background: #f5f5f7; border: 1px solid #e0e0e0;
                border-radius: 8px; padding: 6px 10px; color: #1d1d1f;
            }
            QListWidget {
                background: transparent; border: none;
            }
            QListWidget::item {
                padding: 2px 0px;
            }
            QLabel {
                background: transparent;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("todo_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(8)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("待办事项")
        title.setObjectName("todo_title")
        title_row.addWidget(title)
        title_row.addStretch()

        self._sync_btn = QPushButton("同步")
        self._sync_btn.setObjectName("todo_sync")
        self._sync_btn.setFixedSize(48, 22)
        self._sync_btn.setCursor(Qt.PointingHandCursor)
        self._sync_btn.setToolTip("同步到 Google")
        self._sync_btn.clicked.connect(self._sync_to_google)
        title_row.addWidget(self._sync_btn)
        title_row.addSpacing(4)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("todo_close")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self._on_close)
        title_row.addWidget(close_btn)
        layout.addLayout(title_row)

        # 待办列表
        self._list = QListWidget()
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._list)

        # 输入行
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setObjectName("todo_input")
        self._input.setPlaceholderText("添加待办...")
        self._input.returnPressed.connect(self._add_item)
        input_row.addWidget(self._input)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 30)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton { background: #007aff; color: white; border-radius: 15px; font-weight: bold; border: none; }
            QPushButton:hover { background: #0056cc; }
        """)
        add_btn.clicked.connect(self._add_item)
        input_row.addWidget(add_btn)
        layout.addLayout(input_row)

        outer.addWidget(card)

        self._items = todo_items or []
        self._refresh_list()

    # ---------- 数据 ----------

    def set_items(self, items):
        """外部调用：用最新数据刷新悬浮窗显示"""
        self._items = items
        self._refresh_list()

    def _refresh_list(self):
        self._list.clear()
        for item_data in self._items:
            self._add_list_row(item_data)

    def _add_list_row(self, item_data):
        text = item_data.get("text", "")

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row.setMinimumHeight(28)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(2)

        # 用按钮模拟勾选框，勾选即视为完成，移出列表
        check_btn = QPushButton("")
        check_btn.setFixedSize(18, 18)
        check_btn.setCursor(Qt.PointingHandCursor)
        check_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: transparent;
                border: 1.5px solid #c7c7cc; border-radius: 4px;
                padding: 0px;
            }
        """)
        row_layout.addWidget(check_btn)

        important_btn = QPushButton("★" if item_data.get("important") else "☆")
        important_btn.setFixedWidth(18)
        important_btn.setCursor(Qt.PointingHandCursor)
        important_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #ff3b30; font-size: 11px; padding: 0px; }")
        row_layout.addWidget(important_btn)

        label = QLineEdit(text)
        label.setReadOnly(True)
        label.setFrame(False)
        label.setCursor(Qt.IBeamCursor)

        def _apply_label_style():
            base = "background: transparent; border: none; padding: 0px;"
            if item_data.get("important"):
                label.setStyleSheet(base + "color: #ff3b30; font-weight: bold;")
            else:
                label.setStyleSheet(base + "color: #1d1d1f;")
        _apply_label_style()
        row_layout.addWidget(label, 1)

        def toggle_important():
            item_data["important"] = not item_data.get("important", False)
            important_btn.setText("★" if item_data["important"] else "☆")
            _apply_label_style()
            self._notify_change()

        important_btn.clicked.connect(toggle_important)

        def _enter_edit_mode(event):
            label.setReadOnly(False)
            label.setStyleSheet("background: #f5f5f7; border: 1px solid #007aff; border-radius: 4px; padding: 2px 4px; color: #1d1d1f;")
            label.setFocus()
            label.selectAll()

        def _save_edit():
            new_text = label.text().strip()
            if new_text:
                item_data["text"] = new_text
            else:
                label.setText(item_data.get("text", ""))
            label.setReadOnly(True)
            _apply_label_style()
            self._notify_change()

        label.mouseDoubleClickEvent = _enter_edit_mode
        label.editingFinished.connect(_save_edit)

        list_item = QListWidgetItem()
        self._list.addItem(list_item)
        self._list.setItemWidget(list_item, row)
        row.adjustSize()
        list_item.setSizeHint(row.sizeHint())

        def mark_done():
            """勾选完成：从悬浮窗列表移除，通知设置页移入已完成分组"""
            if item_data in self._items:
                self._items.remove(item_data)
            self._refresh_list()
            self._notify_change()
            if self._on_mark_done:
                self._on_mark_done(item_data)

        check_btn.clicked.connect(mark_done)

    def _add_item(self):
        text = self._input.text().strip()
        if not text:
            return
        import time, uuid
        item_data = {
            "text": text, "important": False,
            "created_at": int(time.time() * 1000),
            "local_id": str(uuid.uuid4()),
        }
        self._items.append(item_data)
        self._add_list_row(item_data)
        self._input.clear()
        self._notify_change()

    def _notify_change(self):
        if self._on_change:
            self._on_change(self._items)

    def get_items(self):
        return self._items

    # ---------- 窗口行为 ----------

    def _sync_to_google(self):
        """点击悬浮窗上的同步按钮：异步推送到 Google Tasks，避免卡住 UI"""
        if getattr(self, "_syncing", False):
            return  # 防止重复点击

        self._syncing = True
        self._sync_spin_angle = 0
        self._sync_btn.setEnabled(False)

        # 旋转动画：用不同角度的箭头字符模拟旋转效果
        spin_chars = ["同步", "..."]
        if not hasattr(self, "_sync_spin_timer"):
            self._sync_spin_timer = QTimer(self)
            self._sync_spin_timer.timeout.connect(
                lambda: self._sync_btn.setText(spin_chars[self._tick_spin()])
            )
        self._sync_spin_timer.start(300)

        def _worker():
            try:
                from voice_typing.core.config import load_config, save_config
                from voice_typing.core.google_sync import push_todo_items
                config = load_config()
                ok, msg = push_todo_items(self._items, config.get("todo_done", []))
                # push_todo_items 会原地写入 google_task_id，需要落盘保存
                config["todo_items"] = self._items
                save_config(config)
                print(f"[待办同步] {msg}")
            except Exception as e:
                import traceback
                print(f"[待办同步] 异常: {e}")
                traceback.print_exc()
                ok, msg = False, str(e)
            # 切回主线程更新 UI
            from PyQt5.QtCore import QMetaObject, Qt as _Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "_on_sync_finished", _Qt.QueuedConnection,
                Q_ARG(bool, ok), Q_ARG(str, msg)
            )

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _tick_spin(self):
        self._sync_spin_angle = (self._sync_spin_angle + 1) % 2
        return self._sync_spin_angle

    @pyqtSlot(bool, str)
    def _on_sync_finished(self, ok, msg):
        self._syncing = False
        self._sync_spin_timer.stop()
        self._sync_btn.setText("同步")
        self._sync_btn.setEnabled(True)
        self._sync_btn.setToolTip(msg)

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
