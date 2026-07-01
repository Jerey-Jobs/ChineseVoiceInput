"""现代浅色主题 QSS 样式表 — 参考 GetIn 风格：白底、圆角卡片、蓝色强调"""

DARK_STYLE = """
/* 全局 */
QWidget {
    background-color: #f5f5f7;
    color: #1d1d1f;
    font-size: 10pt;
    font-family: -apple-system, "PingFang SC", "Helvetica Neue", sans-serif;
}

/* 输入框 */
QLineEdit {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 10px 14px;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border-color: #007aff;
}

/* 按钮 */
QPushButton {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 8px 18px;
    color: #1d1d1f;
    font-weight: 500;
}
QPushButton:hover {
    background: #f0f0f2;
    border-color: #007aff;
}
QPushButton:pressed {
    background: #e8e8ed;
}
QPushButton#accent {
    background: #007aff;
    color: #ffffff;
    border: none;
    font-weight: bold;
}
QPushButton#accent:hover {
    background: #0056cc;
}
QPushButton#danger {
    background: transparent;
    border: 1px solid #ff3b30;
    color: #ff3b30;
}
QPushButton#danger:hover {
    background: #ff3b30;
    color: #ffffff;
}

/* 侧边导航按钮 */
QPushButton#nav-btn {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    text-align: left;
    font-weight: 500;
    color: #6e6e73;
}
QPushButton#nav-btn:hover {
    background: #e8e8ed;
    color: #1d1d1f;
}
QPushButton#nav-btn[active="true"] {
    background: #007aff;
    color: #ffffff;
}

/* 下拉框 */
QComboBox {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 10px 36px 10px 14px;
    color: #1d1d1f;
    min-height: 20px;
    outline: none;
}
QComboBox:hover { border-color: #007aff; }
QComboBox:focus { border-color: #007aff; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    border-left: 1px solid #e0e0e0;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #6e6e73;
}
/* 下拉弹出层 */
QComboBox QAbstractItemView,
QComboBox QListView {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 6px;
    margin: 0;
    outline: none;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView::item,
QComboBox QListView::item {
    background-color: #ffffff;
    padding: 10px 14px;
    min-height: 36px;
    color: #1d1d1f;
    border-radius: 8px;
    margin: 2px 0;
}
QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected {
    background-color: #007aff;
    color: #ffffff;
}
QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:hover {
    background-color: #f0f0f2;
}

/* 分组卡片 */
QGroupBox {
    border: none;
    border-radius: 14px;
    background: #ffffff;
    margin-top: 26px;
    padding: 24px 20px 20px 20px;
    font-weight: bold;
    font-size: 10pt;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 20px;
    padding: 0 8px;
    color: #6e6e73;
}

/* 复选框 */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #1d1d1f;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #d1d1d6;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #007aff;
    border-color: #007aff;
}

/* 单选按钮 */
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #d1d1d6;
    border-radius: 9px;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    background: #007aff;
    border-color: #007aff;
}

/* 标签 */
QLabel {
    background: transparent;
    color: #1d1d1f;
}
QLabel#subtitle {
    color: #6e6e73;
    font-size: 10pt;
}
QLabel#status {
    color: #34c759;
    font-size: 10pt;
}
QLabel#error {
    color: #ff3b30;
    font-size: 10pt;
}

/* 统计卡片数值 */
QLabel#stat-value {
    font-size: 21pt;
    font-weight: bold;
    color: #1d1d1f;
}
QLabel#stat-label {
    font-size: 10pt;
    color: #6e6e73;
}

/* 侧边栏 */
QWidget#sidebar {
    background: #ffffff;
    border-right: 1px solid #e8e8ed;
}

/* 滚动条 */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.15);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0, 0, 0, 0.3);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* 列表 */
QListWidget {
    background: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 8px;
}

/* 文本编辑框 */
QTextEdit {
    background: #ffffff;
    color: #1d1d1f;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 8px;
}
QTextEdit:focus {
    border-color: #007aff;
}

/* 工具提示 */
QToolTip {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 6px 10px;
    color: #1d1d1f;
    font-size: 10pt;
}
"""

OVERLAY_STYLE = """
QWidget#overlay {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid #e0e0e0;
    border-radius: 12px;
}
QLabel#transcript {
    background: transparent;
    color: #1d1d1f;
    font-size: 10pt;
    padding: 16px 24px;
}
QLabel#indicator {
    background: #34c759;
    border-radius: 5px;
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
}
"""
