"""屏幕下方浮窗 — Siri 风格彩色光晕动画"""

import math
import random
from PyQt5.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient, QRadialGradient,
    QFontMetrics, QPainterPath
)
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QApplication


class SiriGlowWidget(QWidget):
    """Siri 风格动画组件：待机旋转圆环，录音彩色波浪"""

    MODE_IDLE = 0
    MODE_RECORDING = 1

    def __init__(self):
        super().__init__()
        self.setMinimumSize(36, 36)
        self._phase = 0.0
        self._amplitude = 0.0
        self._target_amplitude = 0.0
        self._mode = self.MODE_IDLE

        self._colors = [
            QColor(147, 51, 234),   # 紫
            QColor(59, 130, 246),   # 蓝
            QColor(6, 182, 212),    # 青
            QColor(16, 185, 129),   # 绿
            QColor(236, 72, 153),   # 粉
            QColor(245, 158, 11),   # 橙
        ]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        # 待机时也转动
        self._timer.start(16)

    def start(self):
        self._mode = self.MODE_RECORDING
        self._target_amplitude = 0.8
        if not self._timer.isActive():
            self._timer.start(16)
        self.show()

    def stop(self):
        self._mode = self.MODE_IDLE
        self._target_amplitude = 0.0

    def hide_animation(self):
        """完全隐藏"""
        self._mode = self.MODE_IDLE
        self._target_amplitude = 0.0
        self._amplitude = 0.0
        self.hide()

    def _tick(self):
        self._phase += 0.04
        self._amplitude += (self._target_amplitude - self._amplitude) * 0.1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2

        if self._mode == self.MODE_RECORDING and self._amplitude > 0.05:
            self._draw_waves(painter, w, h, cx, cy)
        else:
            self._draw_spinning_ring(painter, cx, cy)

    def _draw_spinning_ring(self, painter, cx, cy):
        """待机：渐变彩色底色 + 旋转圆点"""
        radius = 14
        dot_radius = 3.5
        n = len(self._colors)

        # 渐变底色圆，颜色随 phase 变化
        idx1 = int(self._phase) % n
        idx2 = (idx1 + 1) % n
        t = self._phase - int(self._phase)
        c1 = self._colors[idx1]
        c2 = self._colors[idx2]
        bg_gradient = QRadialGradient(cx, cy, 28)
        gc1 = QColor(c1.red(), c1.green(), c1.blue(), 140)
        gc2 = QColor(c2.red(), c2.green(), c2.blue(), 70)
        bg_gradient.setColorAt(0, gc1)
        bg_gradient.setColorAt(0.6, gc2)
        bg_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_gradient))
        painter.drawEllipse(QPointF(cx, cy), 28, 28)

        # 旋转圆点 + 拖尾光晕
        for i, color in enumerate(self._colors):
            angle = self._phase * 3 + i * (2 * math.pi / n)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            # 光晕
            glow = QRadialGradient(x, y, 6)
            gc = QColor(color)
            gc.setAlpha(120)
            glow.setColorAt(0, gc)
            glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(x, y), 6, 6)
            # 实心圆点
            alpha = 255 - i * 25
            c = QColor(color)
            c.setAlpha(max(alpha, 100))
            painter.setBrush(QBrush(c))
            r = 4.0 - i * 0.3
            painter.drawEllipse(QPointF(x, y), r, r)

    def _draw_waves(self, painter, w, h, cx, cy):
        """录音：多层彩色波浪线条"""
        for idx, color in enumerate(self._colors):
            offset = idx * (math.pi * 2 / len(self._colors))
            freq = 0.03 + idx * 0.005
            amp = self._amplitude * (8 + idx * 2)
            phase = self._phase * 2 + offset

            # 只画线条
            line_path = QPainterPath()
            line_path.moveTo(0, cy + math.sin(phase) * amp * 0)
            for x in range(0, w + 2, 2):
                y = cy + math.sin(x * freq + phase) * amp * math.sin(math.pi * x / w)
                line_path.lineTo(x, y)

            pen_color = QColor(color)
            pen_color.setAlpha(int(200 * self._amplitude))
            painter.setPen(QPen(pen_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(line_path)

        # 中心发光圆
        glow_radius = 10 + self._amplitude * 6 * math.sin(self._phase * 4)
        gradient = QRadialGradient(cx, cy, glow_radius)
        gradient.setColorAt(0, QColor(255, 255, 255, int(200 * self._amplitude)))
        gradient.setColorAt(0.5, QColor(147, 51, 234, int(100 * self._amplitude)))
        gradient.setColorAt(1, QColor(59, 130, 246, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(cx, cy), glow_radius, glow_radius)


class OverlayWindow(QWidget):
    """半透明浮窗，位于屏幕底部中央"""

    def __init__(self):
        super().__init__()
        self.setObjectName("overlay")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # 拖拽相关
        self._dragging = False
        self._drag_position = None

        # Siri 光晕组件
        self._glow = SiriGlowWidget()
        self._text_received = False

        self._text_label = QLabel("")
        self._text_label.setStyleSheet(
            "color: #f0f0f0; font-size: 11pt; background: transparent; padding: 0px;"
        )
        self._text_label.setWordWrap(False)
        self._text_label.setAlignment(Qt.AlignCenter)
        self._text_label.hide()

        # 布局: 上方光晕，下方文字
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)
        main_layout.addWidget(self._glow)
        main_layout.addWidget(self._text_label)

        # 动画
        self._size_animation = QPropertyAnimation(self, b"geometry")
        self._size_animation.setDuration(300)
        self._size_animation.setEasingCurve(QEasingCurve.OutCubic)

        # 初始尺寸 - 待机时显示旋转圆环
        self.resize(64, 64)
        self._center_on_screen()
        self._idle = True

    def _animate_to_size(self, width: int, height: int):
        """以中心为锚点平滑过渡到新尺寸"""
        current_rect = self.geometry()
        cx = current_rect.x() + current_rect.width() // 2
        cy = current_rect.y() + current_rect.height() // 2
        x = cx - width // 2
        y = cy - height // 2
        end_rect = QRect(x, y, width, height)
        self._size_animation.setStartValue(current_rect)
        self._size_animation.setEndValue(end_rect)
        self._size_animation.start()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = screen.bottom() - self.height() - 80
        self.move(x, y)

    def paintEvent(self, event):
        """待机时画彩色圆形区域，录音时画圆角矩形背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        if self._idle:
            # 深色彩色圆形背景
            cx = self.width() / 2
            cy = self.height() / 2
            r = min(self.width(), self.height()) / 2
            bg = QRadialGradient(cx, cy, r)
            bg.setColorAt(0, QColor(30, 20, 50, 220))
            bg.setColorAt(1, QColor(10, 10, 20, 240))
            painter.setBrush(QBrush(bg))
            painter.drawEllipse(QPointF(cx, cy), r, r)
        else:
            painter.setBrush(QBrush(QColor(15, 15, 15, 220)))
            painter.drawRoundedRect(self.rect(), 24, 24)

    def start_recording(self):
        """开始录音：展开浮窗，启动 Siri 光晕动画"""
        self._idle = False
        self._text_received = False
        self._text_label.hide()
        self._text_label.setText("")
        self._glow.show()
        self._glow.start()
        self._animate_to_size(240, 64)
        self.update()

    def stop_recording(self):
        """停止录音：光晕渐隐"""
        self._glow.stop()

    MAX_LABEL_WIDTH = 600

    def update_text(self, text: str):
        """实时更新文字"""
        if not text:
            return

        if not self._text_received:
            self._text_received = True
            self._glow.stop()

        self._text_label.setText(text)
        self._text_label.show()

        fm = QFontMetrics(self._text_label.font())
        text_width = min(fm.horizontalAdvance(text) + 40, self.MAX_LABEL_WIDTH)
        width = max(240, text_width + 32)

        if text_width >= self.MAX_LABEL_WIDTH:
            self._text_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._text_label.setMaximumWidth(self.MAX_LABEL_WIDTH)
        else:
            self._text_label.setAlignment(Qt.AlignCenter)
            self._text_label.setMaximumWidth(self.MAX_LABEL_WIDTH)

        self._animate_to_size(width, 80)

    def set_text(self, text: str):
        """设置最终文字"""
        if not text:
            return
        self._glow.hide_animation()
        self._text_label.setText(text)
        self._text_label.show()

        fm = QFontMetrics(self._text_label.font())
        text_width = min(fm.horizontalAdvance(text) + 40, self.MAX_LABEL_WIDTH)
        width = max(240, text_width + 32)
        self._animate_to_size(width, 80)

    def reset(self):
        """重置到待机状态：旋转圆环"""
        self._idle = True
        self._glow.stop()  # 切回 idle 模式（旋转）
        self._glow.show()
        self._text_label.hide()
        self._text_label.setText("")
        self._animate_to_size(64, 64)
        self.update()

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
