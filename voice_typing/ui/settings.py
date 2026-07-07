"""VoiceType 主窗口 — 侧边导航 + 多页面"""

import subprocess
import os

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QByteArray, QSize, QRect, QRectF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QPushButton,
    QSystemTrayIcon, QMenu, QAction, QApplication, QMessageBox,
    QListWidget, QListWidgetItem, QScrollArea, QCheckBox,
    QRadioButton, QButtonGroup, QStackedWidget, QFrame,
    QStyledItemDelegate, QStyle, QListView,
)

from voice_typing.core.config import load_config, save_config
from voice_typing.engine.alibaba import AlibabaEngine
from voice_typing.engine.volcengine import VolcengineEngine
from voice_typing.core.vocabulary import sync_vocabulary


class _DarkComboBox(QComboBox):
    """暗色主题 QComboBox：showPopup 时把外层容器变透明，消除白边"""

    def __init__(self, parent=None):
        super().__init__(parent)
        view = QListView()
        view.setSpacing(2)
        self.setView(view)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        """禁用滚轮切换选项，必须点击才能更改"""
        event.ignore()

    def showPopup(self):
        super().showPopup()
        # 弹出后容器才真正存在，此时取 view 的 parent 容器并设透明
        container = self.view().parentWidget()
        if container is not None:
            container.setAttribute(Qt.WA_TranslucentBackground, True)
            container.setWindowFlags(
                container.windowFlags()
                | Qt.FramelessWindowHint
                | Qt.NoDropShadowWindowHint
            )
            container.setStyleSheet("background: transparent; border: none;")
            container.show()


def _draw_logo(painter, size):
    """绘制「笔意留白」logo：圆角暗底 + 缺口绿色圆弧"""
    bg = QColor(13, 13, 13)
    accent = QColor(34, 197, 94)

    corner = max(2.0, size * 0.22)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(bg))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(QRectF(0, 0, size, size), corner, corner)

    # 弧形笔触：小尺寸用更粗的笔以保持气场，大尺寸用更纤细比例
    if size <= 18:
        stroke_w = size * 0.14
        margin = size * 0.15
    elif size <= 32:
        stroke_w = size * 0.105
        margin = size * 0.17
    else:
        stroke_w = size * 0.075
        margin = size * 0.18

    diameter = size - 2 * margin
    rect = QRectF(margin, margin, diameter, diameter)

    pen = QPen(accent, stroke_w)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    # Qt drawArc：0° 在 3 点钟方向，正值逆时针，单位 1/16°
    # 缺口约 55°，置于右上（约 1 点钟方向），整圈空 305°
    start_angle = int(57.5 * 16)
    span_angle = int(305 * 16)
    painter.drawArc(rect, start_angle, span_angle)


def _make_tray_icon():
    """生成多尺寸 QIcon — 用于托盘和窗口标题"""
    icon = QIcon()
    for size in (16, 22, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        _draw_logo(p, size)
        p.end()
        icon.addPixmap(pix)
    return icon


def _make_eye_icon(visible=True):
    """生成眼睛图标（SVG）"""
    if visible:
        svg_data = """
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"
                  fill="#9ca3af"/>
        </svg>
        """
    else:
        svg_data = """
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"
                  fill="#9ca3af"/>
        </svg>
        """

    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


CARD_BG = QColor("#ffffff")
CARD_HOVER = QColor("#f0f0f2")
CARD_SELECTED = QColor("#22c55e")
CARD_TEXT = QColor("#1d1d1f")
CARD_TEXT_SELECTED = QColor("#ffffff")
CARD_RADIUS = 10
CARD_PADDING_H = 14
CARD_PADDING_V = 12
CARD_MARGIN_V = 4
CARD_MAX_LINES = 3
CARD_MIN_HEIGHT = 48


class CardDelegate(QStyledItemDelegate):
    """卡片式列表项 — 自适应高度，最多 3 行，超出省略号"""

    def _text_width(self, option):
        w = option.rect.width()
        return max(w - 2 * CARD_PADDING_H, 100)

    def _calc_lines(self, fm, text, width):
        if not text:
            return 1, text
        r = fm.boundingRect(QRect(0, 0, int(width), 99999), Qt.TextWordWrap, text)
        line_h = fm.lineSpacing()
        needed = max(1, (r.height() + line_h - 1) // line_h)
        if needed <= CARD_MAX_LINES:
            return needed, text
        # 二分查找截断点 + 省略号
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            candidate = text[:mid] + "..."
            cr = fm.boundingRect(QRect(0, 0, int(width), 99999), Qt.TextWordWrap, candidate)
            cl = max(1, (cr.height() + line_h - 1) // line_h)
            if cl <= CARD_MAX_LINES:
                lo = mid
            else:
                hi = mid - 1
        return CARD_MAX_LINES, text[:lo] + "..." if lo > 0 else "..."

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect
        selected = option.state & QStyle.State_Selected
        hovered = option.state & QStyle.State_MouseOver

        if selected:
            bg = CARD_SELECTED
        elif hovered:
            bg = CARD_HOVER
        else:
            bg = CARD_BG

        fm = painter.fontMetrics()
        text = index.data(Qt.DisplayRole) or ""
        text_w = self._text_width(option)
        _, display_text = self._calc_lines(fm, text, text_w)

        line_h = fm.lineSpacing()
        r = fm.boundingRect(QRect(0, 0, int(text_w), 99999), Qt.TextWordWrap, display_text)
        text_h = max(line_h, r.height())
        card_h = text_h + 2 * CARD_PADDING_V

        content_rect = QRect(
            rect.x(),
            rect.y() + CARD_MARGIN_V,
            rect.width(),
            card_h,
        )
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(content_rect, CARD_RADIUS, CARD_RADIUS)

        text_color = CARD_TEXT_SELECTED if selected else CARD_TEXT
        painter.setPen(text_color)
        text_rect = content_rect.adjusted(CARD_PADDING_H, CARD_PADDING_V, -CARD_PADDING_H, -CARD_PADDING_V)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, display_text)

        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole) or ""
        fm = option.fontMetrics
        text_w = self._text_width(option)
        _, display_text = self._calc_lines(fm, text, text_w)
        line_h = fm.lineSpacing()
        r = fm.boundingRect(QRect(0, 0, int(text_w), 99999), Qt.TextWordWrap, display_text)
        text_h = max(line_h, r.height())
        card_h = text_h + 2 * CARD_PADDING_V
        return QSize(0, card_h + 2 * CARD_MARGIN_V)


class SettingsWindow(QWidget):
    """VoiceType 主窗口 — 侧边导航 + 多页面"""

    engine_changed = pyqtSignal(object)

    def __init__(self, config, hotkey_manager):
        super().__init__()
        self._config = config
        self._hotkey = hotkey_manager
        self._engine = None
        self._nav_btns = []
        self._new_hotkey_keys = None

        self._init_ui()
        self._init_tray()
        self._apply_config()
        self._create_engine()
        self._select_nav(0)  # 默认显示主页

    # ---------- UI 框架 ----------

    def _init_ui(self):
        self.setWindowTitle("VoiceType")
        self.setMinimumSize(1000, 620)
        self.resize(1000, 680)
        self.setWindowIcon(_make_tray_icon())

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 侧边栏 ----
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        # Logo
        from voice_typing import __version__, __dev__
        logo = QLabel("VoiceType")
        logo.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d1d1f; padding: 8px 8px 4px 8px;")
        sidebar_layout.addWidget(logo)

        ver_text = f"v{__version__}-dev" if __dev__ else f"v{__version__}"
        ver_label = QLabel(ver_text)
        ver_label.setStyleSheet("font-size: 10pt; color: #8e8e93; padding: 0 8px 8px 8px;")
        sidebar_layout.addWidget(ver_label)

        # 导航按钮
        nav_items = [
            ("主页面", 0),
            ("历史记录", 1),
            ("词典", 2),
        ]
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav-btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self._select_nav(i))
            sidebar_layout.addWidget(btn)
            self._nav_btns.append(btn)

        sidebar_layout.addStretch()

        # 引擎状态指示
        status_row = QHBoxLayout()
        self._sidebar_indicator = QLabel()
        self._sidebar_indicator.setFixedSize(8, 8)
        self._sidebar_indicator.setStyleSheet(
            "background: #666; border-radius: 4px; min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px;"
        )
        status_row.addWidget(self._sidebar_indicator)
        self._sidebar_engine_label = QLabel("引擎未就绪")
        self._sidebar_engine_label.setStyleSheet("font-size: 10pt; color: #6e6e73;")
        status_row.addWidget(self._sidebar_engine_label)
        status_row.addStretch()
        sidebar_layout.addLayout(status_row)

        # 退出按钮（左下角）
        self._sidebar_quit_btn = QPushButton("退出程序")
        self._sidebar_quit_btn.setStyleSheet("QPushButton { background: #ff3b30; color: white; border-radius: 8px; padding: 8px; }")
        self._sidebar_quit_btn.clicked.connect(self._quit_app)
        sidebar_layout.addWidget(self._sidebar_quit_btn)

        root.addWidget(sidebar)

        # ---- 分割线 ----
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("QFrame { color: #ffffff; }")
        root.addWidget(sep)

        # ---- 内容区 ----
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_home_page())
        self._stack.addWidget(self._build_history_page())
        self._stack.addWidget(self._build_dictionary_page())
        root.addWidget(self._stack)

    # ---------- 导航 ----------

    def _select_nav(self, index):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if index == 0:
            self._refresh_home()
        elif index == 1:
            self._refresh_history()

    # ---------- Page 0: 主界面 ----------

    def _build_home_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical {
                background: #ffffff; width: 8px; border-radius: 4px; margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #444; border-radius: 4px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #666; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(16)

        title = QLabel("使用统计")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d1d1f;")
        layout.addWidget(title)

        layout.addSpacing(8)

        # 4 个统计卡片
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)

        stats_defs = [
            ("total_seconds", "使用时长", "分钟", "#22c55e"),
            ("total_characters", "输入字数", "字", "#3b82f6"),
            ("total_sessions", "录音次数", "次", "#f59e0b"),
            ("efficiency", "输入效率", "字/分钟", "#a78bfa"),
        ]

        self._stat_labels = {}
        for key, label_text, unit, color in stats_defs:
            card = self._make_stat_card(key, label_text, unit, color)
            cards_layout.addWidget(card, 1)

        layout.addWidget(cards_widget)

        layout.addSpacing(16)

        # 当前引擎信息
        engine_card = QGroupBox("当前状态")
        elayout = QVBoxLayout(engine_card)
        elayout.setSpacing(8)

        self._home_engine_name = QLabel("")
        self._home_engine_name.setStyleSheet("font-size: 10pt; font-weight: bold;")
        elayout.addWidget(self._home_engine_name)

        self._home_engine_status = QLabel("")
        self._home_engine_status.setObjectName("subtitle")
        elayout.addWidget(self._home_engine_status)

        layout.addWidget(engine_card)

        # 嵌入设置内容（不带自己的 scroll）
        settings_widget = self._build_settings_content(layout)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._status_label = QLabel("")
        self._status_label.setObjectName("status")
        self._status_label.setContentsMargins(40, 8, 40, 8)
        outer.addWidget(self._status_label)
        return page

    def _make_stat_card(self, key, label_text, unit, color):
        card = QGroupBox("")
        card.setStyleSheet("QGroupBox { border: none; border-radius: 16px; background: #ffffff; padding: 20px; }")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("stat-label")
        layout.addWidget(label)

        value_label = QLabel("--")
        value_label.setStyleSheet(f"font-size: 21pt; font-weight: bold; color: {color};")
        layout.addWidget(value_label)

        unit_label = QLabel(unit)
        unit_label.setStyleSheet("font-size: 10pt; color: #8e8e93;")
        layout.addWidget(unit_label)

        self._stat_labels[key] = value_label
        return card

    def _refresh_home(self):
        """刷新主页统计和引擎状态"""
        stats = self._config.get("stats", {})
        total_sec = stats.get("total_seconds", 0)
        total_chars = stats.get("total_characters", 0)
        total_sessions = stats.get("total_sessions", 0)
        total_min = total_sec / 60.0

        if total_min < 0.1 and total_sec > 0:
            self._stat_labels["total_seconds"].setText("< 0.1")
        else:
            self._stat_labels["total_seconds"].setText(f"{total_min:.1f}")
        self._stat_labels["total_characters"].setText(str(total_chars))
        self._stat_labels["total_sessions"].setText(str(total_sessions))

        if total_min > 0 and total_chars > 0:
            efficiency = total_chars / total_min
            self._stat_labels["efficiency"].setText(f"{efficiency:.0f}")
        else:
            self._stat_labels["efficiency"].setText("--")

        if self._engine and self._engine.is_available():
            self._home_engine_name.setText(f"引擎已就绪：{self._engine.name}")
            self._home_engine_status.setText("快捷键可用，随时可以开始语音输入")
            self._sidebar_indicator.setStyleSheet(
                "background: #22c55e; border-radius: 4px; min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px;"
            )
            self._sidebar_engine_label.setText("引擎就绪")
        else:
            self._home_engine_name.setText("引擎未就绪")
            self._home_engine_status.setText("请到「设置」页面配置 API Key 或下载本地模型")
            self._sidebar_indicator.setStyleSheet(
                "background: #666; border-radius: 4px; min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px;"
            )
            self._sidebar_engine_label.setText("未就绪")

    # ---------- Page 1: 历史记录 ----------

    def _build_history_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(16)

        title_row = QHBoxLayout()
        title = QLabel("历史记录")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d1d1f;")
        title_row.addWidget(title)
        title_row.addStretch()

        copy_btn = QPushButton("复制选中")
        copy_btn.clicked.connect(self._copy_history_item)
        title_row.addWidget(copy_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_history)
        title_row.addWidget(clear_btn)
        layout.addLayout(title_row)

        hint = QLabel("所有历史记录仅保存在本地设备上")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        self._history_list = QListWidget()
        self._history_list.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        self._history_list.setItemDelegate(CardDelegate())
        self._history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        layout.addWidget(self._history_list)

        self._history_empty_label = QLabel("暂无历史记录")
        self._history_empty_label.setObjectName("subtitle")
        self._history_empty_label.setAlignment(Qt.AlignCenter)
        self._history_empty_label.hide()
        layout.addWidget(self._history_empty_label)

        return page

    def _refresh_history(self):
        self._history_list.clear()
        history = self._config.get("history", [])
        if not history:
            self._history_list.hide()
            self._history_empty_label.show()
            return
        self._history_list.show()
        self._history_empty_label.hide()
        for entry in history:
            text = entry.get("text", "")
            ts = entry.get("timestamp", "")
            engine = entry.get("engine", "")
            chars = entry.get("chars", 0)
            meta_parts = []
            if ts:
                meta_parts.append(ts)
            if engine:
                meta_parts.append(engine)
            if chars:
                meta_parts.append(f"{chars}字")
            meta = "  ·  ".join(meta_parts)
            display = f"{text}\n{meta}" if meta else text
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, text)
            self._history_list.addItem(item)

    def _copy_history_item(self):
        item = self._history_list.currentItem()
        if item:
            text = item.data(Qt.UserRole)
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), timeout=2)

    def _clear_history(self):
        self._config["history"] = []
        save_config(self._config)
        self._history_list.clear()
        self._history_list.hide()
        self._history_empty_label.show()

    # ---------- Page 2: 词典 ----------

    def _build_dictionary_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(16)

        title_row = QHBoxLayout()
        title = QLabel("自定义词典")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d1d1f;")
        title_row.addWidget(title)
        title_row.addStretch()

        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self._delete_dict_item)
        title_row.addWidget(del_btn)
        layout.addLayout(title_row)

        hint = QLabel("添加专业词汇，提升 ASR 识别准确率")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._dict_list = QListWidget()
        self._dict_list.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        self._dict_list.setItemDelegate(CardDelegate())
        self._dict_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._dict_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        layout.addWidget(self._dict_list)

        self._dict_empty_label = QLabel("暂无词条，添加专业词汇以提升识别准确率")
        self._dict_empty_label.setObjectName("subtitle")
        self._dict_empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._dict_empty_label)

        term_row = QHBoxLayout()
        self._dict_term_input = QLineEdit()
        self._dict_term_input.setPlaceholderText("输入词汇（如：CUDA、rviz）")
        term_row.addWidget(self._dict_term_input)

        add_btn = QPushButton("添加")
        add_btn.setObjectName("accent")
        add_btn.clicked.connect(self._add_dict_item)
        add_btn.setFixedWidth(80)
        term_row.addWidget(add_btn)

        sync_btn = QPushButton("同步热词")
        sync_btn.setFixedWidth(80)
        sync_btn.setStyleSheet("QPushButton { background: #007aff; color: white; }")
        sync_btn.clicked.connect(self._sync_hotwords)
        term_row.addWidget(sync_btn)

        self._dict_status = QLabel("")
        self._dict_status.setObjectName("status")
        term_row.addWidget(self._dict_status)
        layout.addLayout(term_row)

        layout.addStretch()
        return page

    def _refresh_dict_list(self):
        self._dict_list.clear()
        vocab = self._config.get("custom_vocabulary", [])
        for item_data in vocab:
            if isinstance(item_data, dict):
                term = item_data.get("term", "")
            else:
                term = str(item_data)
            list_item = QListWidgetItem(term)
            list_item.setData(Qt.UserRole, {"term": term})
            self._dict_list.addItem(list_item)
        has_items = self._dict_list.count() > 0
        self._dict_list.setVisible(has_items)
        self._dict_empty_label.setVisible(not has_items)

    def _add_dict_item(self):
        term = self._dict_term_input.text().strip()
        if not term:
            self._dict_status.setText("请输入词汇")
            QTimer.singleShot(2000, lambda: self._dict_status.setText(""))
            return

        for i in range(self._dict_list.count()):
            data = self._dict_list.item(i).data(Qt.UserRole)
            if data and data.get("term") == term:
                self._dict_status.setText(f"'{term}' 已存在")
                QTimer.singleShot(2000, lambda: self._dict_status.setText(""))
                return

        item = QListWidgetItem(term)
        item.setData(Qt.UserRole, {"term": term})
        self._dict_list.addItem(item)
        self._dict_list.show()
        self._dict_empty_label.hide()
        self._dict_term_input.clear()
        self._save_dict()

    def _delete_dict_item(self):
        item = self._dict_list.currentItem()
        if item:
            self._dict_list.takeItem(self._dict_list.row(item))
            if self._dict_list.count() == 0:
                self._dict_list.hide()
                self._dict_empty_label.show()
            self._save_dict()

    def _save_dict(self):
        vocab = []
        for i in range(self._dict_list.count()):
            data = self._dict_list.item(i).data(Qt.UserRole)
            term = data.get("term") if data else self._dict_list.item(i).text()
            vocab.append({"term": term})
        self._config["custom_vocabulary"] = vocab

        # 同步热词表
        engine_type = self._config.get("engine", "alibaba")
        api_key = self._config.get("alibaba_api_key", "")
        hotwords = [v["term"] for v in vocab]
        if engine_type == "alibaba" and hotwords and api_key:
            phrase_id = sync_vocabulary(
                api_key=api_key,
                hotwords=hotwords,
                phrase_id=self._config.get("phrase_id", ""),
            )
            if phrase_id:
                self._config["phrase_id"] = phrase_id

        save_config(self._config)
        self._dict_status.setText("已保存")
        QTimer.singleShot(2000, lambda: self._dict_status.setText(""))

    def _sync_hotwords(self):
        """手动同步热词到阿里云"""
        print("[热词] 同步按钮被点击")
        api_key = self._config.get("alibaba_api_key", "")
        if not api_key:
            print("[热词] 无 API Key")
            self._dict_status.setText("请先配置阿里云 API Key")
            QTimer.singleShot(3000, lambda: self._dict_status.setText(""))
            return
        vocab = self._config.get("custom_vocabulary", [])
        hotwords = [v["term"] for v in vocab if v.get("term")]
        if not hotwords:
            print("[热词] 词库为空")
            self._dict_status.setText("词库为空")
            QTimer.singleShot(2000, lambda: self._dict_status.setText(""))
            return
        print(f"[热词] 开始同步 {len(hotwords)} 个热词...")
        self._dict_status.setText("正在同步热词...")
        QApplication.processEvents()
        phrase_id = sync_vocabulary(
            api_key=api_key,
            hotwords=hotwords,
            phrase_id=self._config.get("phrase_id", ""),
        )
        if phrase_id:
            self._config["phrase_id"] = phrase_id
            save_config(self._config)
            print(f"[热词] 同步成功! phrase_id={phrase_id}")
            self._dict_status.setText(f"同步成功！{len(hotwords)} 个热词")
        else:
            print("[热词] 同步失败")
            self._dict_status.setText("同步失败")
        QTimer.singleShot(3000, lambda: self._dict_status.setText(""))

    # ---------- Page 3: 设置 ----------

    def _build_settings_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(16)

        self._build_settings_content(layout)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._status_label = QLabel("")
        self._status_label.setObjectName("status")
        self._status_label.setContentsMargins(40, 8, 40, 8)
        outer.addWidget(self._status_label)
        return page

    def _build_settings_content(self, layout):
        """将设置内容写入指定 layout"""
        title = QLabel("设置")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d1d1f;")
        layout.addWidget(title)

        # 引擎选择
        engine_card = QGroupBox("引擎选择")
        elayout = QVBoxLayout(engine_card)

        self._engine_combo = _DarkComboBox()
        self._engine_combo.addItem("阿里云 Paraformer（云端）", "alibaba")
        self._engine_combo.addItem("火山引擎 BigModel（云端）", "volcengine")
        self._engine_combo.currentIndexChanged.connect(self._on_engine_preview)
        elayout.addWidget(self._engine_combo)

        layout.addWidget(engine_card)

        # API 配置
        self._api_card = QGroupBox("API 配置")
        alayout = QVBoxLayout(self._api_card)

        self._api_status = QLabel("")
        self._api_status.setObjectName("status")

        # 阿里云
        self._alibaba_api_widget = QWidget()
        alibaba_api_layout = QVBoxLayout(self._alibaba_api_widget)
        alibaba_api_layout.setContentsMargins(0, 0, 0, 0)
        self._api_wrapper, self._api_input = self._make_password_input(
            "输入阿里云 DashScope API Key", self._api_status
        )
        alibaba_api_layout.addWidget(self._api_wrapper)
        alibaba_link = QLabel('<a href="https://dashscope.console.aliyun.com/" style="color: #22c55e;">前往阿里云 DashScope 控制台获取 API Key</a>')
        alibaba_link.setOpenExternalLinks(True)
        alibaba_api_layout.addWidget(alibaba_link)
        alayout.addWidget(self._alibaba_api_widget)

        # 火山引擎
        self._volc_api_widget = QWidget()
        volc_layout = QVBoxLayout(self._volc_api_widget)
        volc_layout.setContentsMargins(0, 0, 0, 0)
        volc_layout.setSpacing(8)

        volc_asr_label = QLabel("语音识别 (ASR)")
        volc_asr_label.setObjectName("subtitle")
        volc_layout.addWidget(volc_asr_label)

        volc_link = QLabel('<a href="https://console.volcengine.com/ark/" style="color: #22c55e;">前往火山引擎 ARK 控制台获取凭证</a>')
        volc_link.setOpenExternalLinks(True)
        volc_layout.addWidget(volc_link)

        app_id_wrapper, self._volc_app_id_input = self._make_password_input("App ID（X-Api-App-Key）— 旧版认证")
        volc_layout.addWidget(app_id_wrapper)

        access_token_wrapper, self._volc_access_token_input = self._make_password_input("Access Token（X-Api-Access-Key）— 旧版认证")
        volc_layout.addWidget(access_token_wrapper)

        volc_apikey_wrapper, self._volc_apikey_input = self._make_password_input("API Key（X-Api-Key）— 新版认证，填了优先使用")
        volc_layout.addWidget(volc_apikey_wrapper)

        # Resource ID 选择
        resource_row = QHBoxLayout()
        resource_label = QLabel("Resource ID：")
        resource_row.addWidget(resource_label)
        self._volc_resource_combo = _DarkComboBox()
        self._volc_resource_combo.setEditable(True)
        self._volc_resource_combo.addItem("volc.bigasr.sauc.duration")
        self._volc_resource_combo.addItem("volc.seedasr.sauc.duration")
        # 如果配置中有自定义值，加入并选中
        saved_resource = self._config.get("volc_resource_id", "volc.bigasr.sauc.duration")
        idx = self._volc_resource_combo.findText(saved_resource)
        if idx >= 0:
            self._volc_resource_combo.setCurrentIndex(idx)
        else:
            self._volc_resource_combo.addItem(saved_resource)
            self._volc_resource_combo.setCurrentText(saved_resource)
        self._volc_resource_combo.setStyleSheet("QComboBox { background: #ffffff; color: #1d1d1f; border: 1px solid #e0e0e0; border-radius: 6px; padding: 4px 8px; }")
        resource_row.addWidget(self._volc_resource_combo)
        resource_row.addStretch()
        volc_layout.addLayout(resource_row)

        # 云端热词 ID
        self._volc_hotword_id_input = QLineEdit()
        self._volc_hotword_id_input.setPlaceholderText("云端热词ID（如 1e3a872c-ff82-471b-...，可选）")
        volc_layout.addWidget(self._volc_hotword_id_input)

        self._volc_replace_word_id_input = QLineEdit()
        self._volc_replace_word_id_input.setPlaceholderText("云端替换词ID（如 6d146090-bd8d-454e-...，可选）")
        volc_layout.addWidget(self._volc_replace_word_id_input)

        volc_llm_label = QLabel("文本润色 (豆包大模型)")
        volc_llm_label.setObjectName("subtitle")
        volc_layout.addWidget(volc_llm_label)

        doubao_wrapper, self._doubao_api_key_input = self._make_password_input("豆包 ARK API Key")
        volc_layout.addWidget(doubao_wrapper)

        self._doubao_endpoint_input = QLineEdit()
        self._doubao_endpoint_input.setPlaceholderText("推理接入点 ID（ep-xxxxxxxxxxxx）")
        volc_layout.addWidget(self._doubao_endpoint_input)

        alayout.addWidget(self._volc_api_widget)
        self._volc_api_widget.hide()

        alayout.addWidget(self._api_status)

        layout.addWidget(self._api_card)

        # 快捷键
        hotkey_card = QGroupBox("快捷键")
        hlayout = QVBoxLayout(hotkey_card)
        hrow = QHBoxLayout()
        self._hotkey_btn = QPushButton(self._hotkey_display())
        self._hotkey_btn.setMinimumHeight(44)
        self._hotkey_btn.clicked.connect(self._record_hotkey)
        hrow.addWidget(self._hotkey_btn)
        self._clear_hotkey_btn = QPushButton("清除")
        self._clear_hotkey_btn.setFixedWidth(80)
        self._clear_hotkey_btn.clicked.connect(self._clear_hotkey)
        hrow.addWidget(self._clear_hotkey_btn)
        hlayout.addLayout(hrow)

        # 快捷键模式选择
        mode_row = QHBoxLayout()
        mode_label = QLabel("触发模式：")
        mode_row.addWidget(mode_label)
        self._mode_hold = QPushButton("按住说话")
        self._mode_double = QPushButton("双击触发")
        current_mode = self._config.get("hotkey_mode", "hold")
        self._mode_hold.setCheckable(True)
        self._mode_double.setCheckable(True)
        self._mode_hold.setChecked(current_mode == "hold")
        self._mode_double.setChecked(current_mode == "double_tap")
        mode_style = """
            QPushButton { padding: 6px 12px; border-radius: 8px; border: 1px solid #e0e0e0; }
            QPushButton:checked { background: #007aff; color: white; border: 1px solid #007aff; }
        """
        self._mode_hold.setStyleSheet(mode_style)
        self._mode_double.setStyleSheet(mode_style)
        self._mode_hold.clicked.connect(lambda: self._set_hotkey_mode("hold"))
        self._mode_double.clicked.connect(lambda: self._set_hotkey_mode("double_tap"))
        mode_row.addWidget(self._mode_hold)
        mode_row.addWidget(self._mode_double)
        mode_row.addStretch()
        hlayout.addLayout(mode_row)

        layout.addWidget(hotkey_card)

        # 文本润色模型（独立配置，可选择）
        polish_llm_card = QGroupBox("文本润色模型")
        polish_llm_layout = QVBoxLayout(polish_llm_card)

        # 模型选择按钮
        polish_model_row = QHBoxLayout()
        polish_model_label = QLabel("润色引擎：")
        polish_model_row.addWidget(polish_model_label)
        self._polish_model_btns = {}
        current_polish = self._config.get("polish_model", "qwen")
        polish_btn_css = """
            QPushButton { padding: 6px 12px; border-radius: 8px; border: 1px solid #e0e0e0; }
            QPushButton:checked { background: #007aff; color: white; border: 1px solid #007aff; }
        """
        for model_id, model_name in [("qwen", "阿里 Qwen"), ("doubao", "豆包"), ("deepseek", "DeepSeek")]:
            btn = QPushButton(model_name)
            btn.setCheckable(True)
            btn.setChecked(model_id == current_polish)
            btn.setStyleSheet(polish_btn_css)
            btn.clicked.connect(lambda checked, m=model_id: self._set_polish_model(m))
            self._polish_model_btns[model_id] = btn
            polish_model_row.addWidget(btn)
        polish_model_row.addStretch()
        polish_llm_layout.addLayout(polish_model_row)

        # 各模型的配置区域（根据选择动态显示）
        from PyQt5.QtWidgets import QStackedWidget

        self._polish_config_stack = QStackedWidget()

        # Qwen 配置
        qwen_widget = QLabel("使用上方阿里云 API Key 进行润色（无需额外配置）")
        qwen_widget.setObjectName("subtitle")
        qwen_widget.setWordWrap(True)
        self._polish_config_stack.addWidget(qwen_widget)  # index 0

        # 豆包配置
        from PyQt5.QtWidgets import QWidget as _QW
        doubao_widget = _QW()
        doubao_layout = QVBoxLayout(doubao_widget)
        doubao_layout.setContentsMargins(0, 0, 0, 0)
        doubao_key_wrapper, self._polish_doubao_key_input = self._make_password_input("豆包 API Key")
        doubao_layout.addWidget(doubao_key_wrapper)
        self._polish_doubao_endpoint_input = QLineEdit()
        self._polish_doubao_endpoint_input.setPlaceholderText("豆包 Endpoint ID（如 ep-xxx）")
        doubao_layout.addWidget(self._polish_doubao_endpoint_input)
        self._polish_config_stack.addWidget(doubao_widget)  # index 1

        # DeepSeek 配置
        deepseek_widget = _QW()
        deepseek_layout = QVBoxLayout(deepseek_widget)
        deepseek_layout.setContentsMargins(0, 0, 0, 0)
        deepseek_wrapper, self._deepseek_api_key_input = self._make_password_input("DeepSeek API Key")
        deepseek_layout.addWidget(deepseek_wrapper)
        self._polish_config_stack.addWidget(deepseek_widget)  # index 2

        # 设置当前显示
        model_index = {"qwen": 0, "doubao": 1, "deepseek": 2}
        self._polish_config_stack.setCurrentIndex(model_index.get(current_polish, 0))
        polish_llm_layout.addWidget(self._polish_config_stack)

        polish_llm_hint = QLabel("选择用哪个模型来润色语音转写结果")
        polish_llm_hint.setObjectName("subtitle")
        polish_llm_layout.addWidget(polish_llm_hint)
        layout.addWidget(polish_llm_card)

        # 润色强度
        polish_card = QGroupBox("润色强度")
        playout = QVBoxLayout(polish_card)
        playout.setSpacing(6)

        self._polish_group = QButtonGroup(self)
        self._polish_light = QRadioButton("轻度 — 仅删明显语气词，一字不改")
        self._polish_medium = QRadioButton("中度 — 删语气词、修正标点，保留原文（推荐）")
        self._polish_strong = QRadioButton("重度 — 删语气词、理顺表达、修正标点")
        self._polish_group.addButton(self._polish_light, 0)
        self._polish_group.addButton(self._polish_medium, 1)
        self._polish_group.addButton(self._polish_strong, 2)
        playout.addWidget(self._polish_light)
        playout.addWidget(self._polish_medium)
        playout.addWidget(self._polish_strong)
        polish_hint = QLabel("润色力度调节")
        polish_hint.setObjectName("subtitle")
        playout.addWidget(polish_hint)
        layout.addWidget(polish_card)

        # 自定义语音风格（多模式）
        style_card = QGroupBox("自定义语音风格")
        style_layout = QVBoxLayout(style_card)
        style_hint = QLabel("选择或自定义润色模式，每个模式可配置独立的提示词")
        style_hint.setObjectName("subtitle")
        style_hint.setWordWrap(True)
        style_layout.addWidget(style_hint)

        # 模式切换按钮行
        style_mode_row = QHBoxLayout()
        self._style_modes = self._config.get("style_modes", {
            "日常": "如果有明显的逻辑异常，可以优化下语句变成通顺的语句",
            "专业": "",
        })
        # 确保配置中有
        if "style_modes" not in self._config:
            self._config["style_modes"] = self._style_modes
        self._style_mode_btns = {}
        current_style_mode = self._config.get("current_style_mode", "日常")
        style_btn_css = """
            QPushButton { padding: 6px 14px; border-radius: 8px; border: 1px solid #e0e0e0; }
            QPushButton:checked { background: #007aff; color: white; border: 1px solid #007aff; }
        """
        for mode_name in self._style_modes:
            btn = QPushButton(mode_name)
            btn.setCheckable(True)
            btn.setChecked(mode_name == current_style_mode)
            btn.setStyleSheet(style_btn_css)
            btn.clicked.connect(lambda checked, m=mode_name: self._switch_style_mode(m))
            self._style_mode_btns[mode_name] = btn
            style_mode_row.addWidget(btn)

        # 添加新模式按钮
        add_mode_btn = QPushButton("+")
        add_mode_btn.setFixedWidth(36)
        add_mode_btn.clicked.connect(self._add_style_mode)
        style_mode_row.addWidget(add_mode_btn)
        style_mode_row.addStretch()
        style_layout.addLayout(style_mode_row)

        # 多行文本框
        from PyQt5.QtWidgets import QTextEdit
        self._custom_style_input = QTextEdit()
        self._custom_style_input.setPlaceholderText("输入该模式的润色提示词（如：用简洁专业的技术文档风格）")
        self._custom_style_input.setMaximumHeight(100)
        self._custom_style_input.setStyleSheet("QTextEdit { background: #ffffff; color: #1d1d1f; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px; }")
        self._custom_style_input.setText(self._style_modes.get(current_style_mode, ""))
        style_layout.addWidget(self._custom_style_input)
        layout.addWidget(style_card)

        # 开机启动
        autostart_card = QGroupBox("开机启动")
        alayout_auto = QVBoxLayout(autostart_card)
        self._autostart_check = QCheckBox("开机自动启动 VoiceType")
        alayout_auto.addWidget(self._autostart_check)
        layout.addWidget(autostart_card)

        layout.addStretch()

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._cancel_btn = QPushButton("重置")
        self._cancel_btn.setMinimumWidth(100)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)

        self._apply_btn = QPushButton("确定")
        self._apply_btn.setObjectName("accent")
        self._apply_btn.setMinimumWidth(100)
        self._apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self._apply_btn)

        btn_row.addStretch()
        self._quit_btn = QPushButton("退出程序")
        self._quit_btn.setMinimumWidth(100)
        self._quit_btn.setStyleSheet("QPushButton { background: #ff3b30; color: white; }")
        self._quit_btn.clicked.connect(self._quit_app)
        btn_row.addWidget(self._quit_btn)

        layout.addLayout(btn_row)

    # ---------- 托盘 ----------

    def _init_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_tray_icon())
        self._tray.setToolTip("VoiceType — 语音输入")

        menu = QMenu()
        show_action = menu.addAction("显示主窗口")
        menu.addSeparator()
        quit_action = menu.addAction("退出 VoiceType")

        def _on_menu_triggered(action):
            if action == quit_action:
                self._quit_app()
            elif action == show_action:
                self._show_window()

        menu.triggered.connect(_on_menu_triggered)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # ---------- 引擎 ----------

    def _make_password_input(self, placeholder, status_label=None):
        """创建普通文本输入框"""
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        layout.addWidget(input_field)

        if status_label is not None:
            def on_text_changed(text):
                if text and len(text) > 10:
                    status_label.setText("API Key 已填写")
                else:
                    status_label.setText("")
            input_field.textChanged.connect(on_text_changed)

        return wrapper, input_field

    def _create_engine(self):
        engine_type = self._config.get("engine", "alibaba")
        if engine_type == "alibaba":
            engine = AlibabaEngine(
                api_key=self._config.get("alibaba_api_key", ""),
                phrase_id=self._config.get("phrase_id", ""),
            )
            engine.initialize()
        elif engine_type == "volcengine":
            vocab = self._config.get("custom_vocabulary", [])
            hotwords = [v["term"] for v in vocab if v.get("term")]
            engine = VolcengineEngine(
                app_id=self._config.get("volc_asr_app_id", ""),
                access_token=self._config.get("volc_asr_access_token", ""),
                hotwords=hotwords,
                resource_id=self._config.get("volc_resource_id", ""),
                api_key=self._config.get("volc_api_key", ""),
                hotword_id=self._config.get("volc_hotword_id", ""),
                replace_word_id=self._config.get("volc_replace_word_id", ""),
            )
            engine.initialize()
        else:
            engine = AlibabaEngine(
                api_key=self._config.get("alibaba_api_key", ""),
                phrase_id=self._config.get("phrase_id", ""),
            )
            engine.initialize()
        self._engine = engine
        self.engine_changed.emit(self._engine)

    # ---------- 配置应用 ----------

    def _apply_config(self):
        engine = self._config.get("engine", "alibaba")
        idx = self._engine_combo.findData(engine)
        if idx >= 0:
            self._engine_combo.setCurrentIndex(idx)

        self._api_input.setText(self._config.get("alibaba_api_key", ""))
        self._volc_app_id_input.setText(self._config.get("volc_asr_app_id", ""))
        self._volc_access_token_input.setText(self._config.get("volc_asr_access_token", ""))
        self._volc_apikey_input.setText(self._config.get("volc_api_key", ""))
        self._volc_hotword_id_input.setText(self._config.get("volc_hotword_id", ""))
        self._volc_replace_word_id_input.setText(self._config.get("volc_replace_word_id", ""))

        self._on_engine_preview()

        self._autostart_check.setChecked(self._config.get("autostart", False))

        strength = self._config.get("polish_strength", "medium")
        btn = {"light": self._polish_light, "medium": self._polish_medium, "strong": self._polish_strong}.get(strength)
        if btn:
            btn.setChecked(True)

        self._doubao_api_key_input.setText(self._config.get("doubao_api_key", ""))
        self._doubao_endpoint_input.setText(self._config.get("doubao_endpoint_id", ""))
        self._deepseek_api_key_input.setText(self._config.get("deepseek_api_key", ""))

        # 润色模型配置区
        self._polish_doubao_key_input.setText(self._config.get("doubao_api_key", ""))
        self._polish_doubao_endpoint_input.setText(self._config.get("doubao_endpoint_id", ""))

        self._custom_style_input.setText(self._config.get("custom_style_prompt", ""))

        self._refresh_dict_list()

    # ---------- 事件处理 ----------

    def _on_engine_preview(self, index=None):
        engine_type = self._engine_combo.currentData()
        if engine_type == "volcengine":
            self._alibaba_api_widget.hide()
            self._volc_api_widget.show()
        else:
            self._alibaba_api_widget.show()
            self._volc_api_widget.hide()

    def _on_apply(self):
        engine_type = self._engine_combo.currentData()
        self._config["engine"] = engine_type
        self._config["alibaba_api_key"] = self._api_input.text()
        self._config["volc_asr_app_id"] = self._volc_app_id_input.text()
        self._config["volc_asr_access_token"] = self._volc_access_token_input.text()
        self._config["volc_api_key"] = self._volc_apikey_input.text()
        self._config["volc_hotword_id"] = self._volc_hotword_id_input.text().strip()
        self._config["volc_replace_word_id"] = self._volc_replace_word_id_input.text().strip()
        self._config["volc_resource_id"] = self._volc_resource_combo.currentText().strip()

        autostart = self._autostart_check.isChecked()
        self._config["autostart"] = autostart
        self._set_autostart(autostart)

        if self._polish_light.isChecked():
            self._config["polish_strength"] = "light"
        elif self._polish_strong.isChecked():
            self._config["polish_strength"] = "strong"
        else:
            self._config["polish_strength"] = "medium"

        self._config["doubao_api_key"] = self._doubao_api_key_input.text()
        self._config["doubao_endpoint_id"] = self._doubao_endpoint_input.text()
        self._config["deepseek_api_key"] = self._deepseek_api_key_input.text()

        # 同步润色区的配置（润色区和引擎区共享 doubao key）
        if self._polish_doubao_key_input.text():
            self._config["doubao_api_key"] = self._polish_doubao_key_input.text()
        if self._polish_doubao_endpoint_input.text():
            self._config["doubao_endpoint_id"] = self._polish_doubao_endpoint_input.text()

        # 保存当前风格模式的提示词
        current_mode = self._config.get("current_style_mode", "日常")
        self._style_modes[current_mode] = self._custom_style_input.toPlainText().strip()
        self._config["style_modes"] = self._style_modes
        self._config["custom_style_prompt"] = self._custom_style_input.toPlainText().strip()

        if self._new_hotkey_keys is not None:
            self._config["hotkey"] = self._new_hotkey_keys
            self._new_hotkey_keys = None

        # 自定义词库（从词典页同步）
        vocab = []
        hotwords = []
        for i in range(self._dict_list.count()):
            data = self._dict_list.item(i).data(Qt.UserRole)
            term = data.get("term") if data else self._dict_list.item(i).text()
            vocab.append({"term": term})
            hotwords.append(term)
        self._config["custom_vocabulary"] = vocab

        if engine_type == "alibaba" and hotwords and self._config.get("alibaba_api_key"):
            self._status_label.setText("正在同步热词表...")
            QApplication.processEvents()
            phrase_id = sync_vocabulary(
                api_key=self._config.get("alibaba_api_key"),
                hotwords=hotwords,
                phrase_id=self._config.get("phrase_id", ""),
            )
            if phrase_id:
                self._config["phrase_id"] = phrase_id
            else:
                self._status_label.setText("热词同步失败（识别仍可用，热词不生效）")
                QTimer.singleShot(3000, lambda: self._update_status())
        elif not vocab:
            self._config["phrase_id"] = ""

        save_config(self._config)
        self._create_engine()
        self._update_status()
        self._refresh_dict_list()

        self._status_label.setText("设置已保存并应用")
        QTimer.singleShot(2000, lambda: self._update_status())

    def _on_cancel(self):
        self._new_hotkey_keys = None
        self._hotkey.set_hotkey(self._config.get("hotkey", []))
        self._apply_config()
        self._status_label.setText("已重置为上次保存的设置")
        QTimer.singleShot(2000, lambda: self._update_status())

    def _set_polish_model(self, model_id):
        """切换润色模型"""
        self._config["polish_model"] = model_id
        for mid, btn in self._polish_model_btns.items():
            btn.setChecked(mid == model_id)
        model_index = {"qwen": 0, "doubao": 1, "deepseek": 2}
        self._polish_config_stack.setCurrentIndex(model_index.get(model_id, 0))
        from voice_typing.core.config import save_config
        save_config(self._config)

    def _switch_style_mode(self, mode_name):
        """切换风格模式"""
        # 保存当前模式的提示词
        current = self._config.get("current_style_mode", "日常")
        self._style_modes[current] = self._custom_style_input.toPlainText().strip()
        # 切换
        self._config["current_style_mode"] = mode_name
        self._config["style_modes"] = self._style_modes
        self._config["custom_style_prompt"] = self._style_modes.get(mode_name, "")
        self._custom_style_input.setText(self._style_modes.get(mode_name, ""))
        # 更新按钮状态
        for name, btn in self._style_mode_btns.items():
            btn.setChecked(name == mode_name)
        from voice_typing.core.config import save_config
        save_config(self._config)

    def _add_style_mode(self):
        """添加新的风格模式"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新增模式", "模式名称：")
        if ok and name.strip():
            name = name.strip()
            if name in self._style_modes:
                return
            self._style_modes[name] = ""
            self._config["style_modes"] = self._style_modes
            # 创建按钮
            style_btn_css = """
                QPushButton { padding: 6px 14px; border-radius: 8px; border: 1px solid #e0e0e0; }
                QPushButton:checked { background: #007aff; color: white; border: 1px solid #007aff; }
            """
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet(style_btn_css)
            btn.clicked.connect(lambda checked, m=name: self._switch_style_mode(m))
            self._style_mode_btns[name] = btn
            # 插入到 + 按钮前面（倒数第2个位置）
            # 直接切换到新模式
            self._switch_style_mode(name)

    def _set_hotkey_mode(self, mode):
        """切换快捷键触发模式"""
        self._config["hotkey_mode"] = mode
        self._hotkey.set_mode(mode)
        self._mode_hold.setChecked(mode == "hold")
        self._mode_double.setChecked(mode == "double_tap")
        from voice_typing.core.config import save_config
        save_config(self._config)

    def _record_hotkey(self):
        self._hotkey_btn.setText("按下快捷键组合...")
        self._hotkey_btn.setStyleSheet("border-color: #22c55e; color: #22c55e;")
        self._hotkey.stop()

        def on_done(keys):
            if len(keys) >= 1:
                self._new_hotkey_keys = keys
                self._hotkey.set_hotkey(keys)
            self._hotkey_btn.setText(self._hotkey_display())
            self._hotkey_btn.setStyleSheet("")
            self._hotkey.start()

        from voice_typing.core.hotkey import HotkeyManager
        self._record_listener = HotkeyManager.record_key_sequence(on_done)

    def _clear_hotkey(self):
        self._new_hotkey_keys = []
        self._hotkey_btn.setText("点击设置快捷键")
        self._hotkey.set_hotkey([])

    _VK_LABELS = {269025067: "Fn"}

    @classmethod
    def _key_label(cls, s):
        if s.startswith("vk:"):
            vk = int(s[3:])
            if vk in cls._VK_LABELS:
                return cls._VK_LABELS[vk]
            return f"Key({vk})"
        return s.upper()

    def _hotkey_display(self):
        if self._new_hotkey_keys is not None:
            keys = self._new_hotkey_keys
        else:
            keys = self._config.get("hotkey", [])
        if not keys:
            return "点击设置快捷键"
        return " + ".join(self._key_label(k) for k in keys)

    def _update_status(self):
        if self._engine and self._engine.is_available():
            self._status_label.setText(f"引擎就绪: {self._engine.name}")
        else:
            self._status_label.setText("引擎未就绪，请配置 API Key 或下载本地模型")

    # ---------- 托盘事件 ----------

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
    AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "voice-typing.desktop")

    def _set_autostart(self, enable: bool):
        if enable:
            os.makedirs(self.AUTOSTART_DIR, exist_ok=True)
            with open(self.AUTOSTART_FILE, "w") as f:
                f.write("""[Desktop Entry]
Type=Application
Name=VoiceType
Exec=/usr/bin/voice-typing
Icon=voice-typing
Terminal=false
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
""")
        else:
            if os.path.exists(self.AUTOSTART_FILE):
                os.remove(self.AUTOSTART_FILE)

    def _quit_app(self):
        # DEBUG: 确认退出方法被调用
        with open('/tmp/voice_quit_debug.txt', 'w') as f:
            f.write('quit called')
        import os, signal
        self._tray.hide()
        try:
            self._hotkey.stop()
        except Exception:
            pass
        os.kill(os.getpid(), signal.SIGKILL)

    def closeEvent(self, event):
        # 按住 Shift 点关闭 = 真正退出
        from PyQt5.QtWidgets import QApplication as _QApp
        if _QApp.keyboardModifiers() & Qt.ShiftModifier:
            self._quit_app()
            return
        event.ignore()
        self.hide()
