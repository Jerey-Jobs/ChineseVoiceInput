"""录音 + ASR 控制器"""

import queue
import threading

import pyaudio
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QMetaObject, Q_ARG

SAMPLE_RATE = 16000
CHUNK_SIZE = 3200  # 200ms


class Recorder(QObject):
    """录音 + ASR 控制器，在主线程中用信号通信"""

    text_update = pyqtSignal(str)
    recording_done = pyqtSignal(str)

    def __init__(self, engine, app_obj=None):
        super().__init__()
        self._engine = engine
        self._recording = False
        self._audio_queue = None
        self._p = None
        self._app_obj = app_obj  # VoiceTypingApp 对象引用

    def start(self):
        self._recording = True
        self._audio_queue = queue.Queue()

        # 启动引擎建连（异步，不阻塞）
        if not self._engine.is_available():
            self._engine.initialize()
        self._engine.start()
        if hasattr(self._engine, "set_text_callback"):
            self._engine.set_text_callback(lambda t: self.text_update.emit(t))

        # 立刻初始化 PyAudio 并开始录音（不等连接就绪）
        self._p = pyaudio.PyAudio()

        # 录音线程
        threading.Thread(target=self._record_audio, daemon=True).start()
        # 音频推流线程
        threading.Thread(target=self._feed_engine, daemon=True).start()

    def stop(self):
        self._recording = False

    def _record_audio(self):
        import time as _t
        import os
        _t0 = _t.time()
        try:
            stream = self._p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
        except Exception:
            self.recording_done.emit("")
            return
        print(f"[录音] 麦克风打开耗时: {_t.time() - _t0:.3f}s")

        # 调试用：把本次录音的原始 PCM 落盘，方便确认是否丢音频
        debug_dir = os.path.expanduser("~/.cache/voice_typing_debug")
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"rec_{int(_t.time())}.pcm")
        debug_file = open(debug_path, "wb")
        print(f"[录音] PCM 调试文件: {debug_path}")

        frame_idx = 0
        clip_streak = 0  # 连续削波帧计数（用于识别启动瞬态）
        while self._recording:
            try:
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if frame_idx < 3:
                    print(f"[录音] 采集第 {frame_idx} 帧, t=+{_t.time()-_t0:.3f}s, bytes={len(data)}")

                # 检测麦克风启动瞬态削波噪声（前几帧常见的满幅爆音）
                # 只在录音刚开始的前 10 帧内检测，避免误杀正常大音量说话
                if frame_idx < 10:
                    import array
                    samples = array.array('h')
                    samples.frombytes(data)
                    clipped = sum(1 for s in samples if abs(s) >= 32750)
                    clip_ratio = clipped / max(len(samples), 1)
                    if clip_ratio > 0.95:
                        clip_streak += 1
                        print(f"[录音] 帧 {frame_idx} 检测到削波噪声 ({clip_ratio*100:.0f}%)，替换为静音")
                        data = b'\x00' * len(data)
                    else:
                        clip_streak = 0

                frame_idx += 1
                debug_file.write(data)
                self._audio_queue.put(data)
            except Exception:
                break

        debug_file.close()
        print(f"[录音] 共采集 {frame_idx} 帧，PCM 已保存: {debug_path}")
        stream.stop_stream()
        stream.close()
        self._p.terminate()

    def _feed_engine(self):
        import time as _t
        _t0 = _t.time()
        try:
            self._engine.set_text_callback(lambda t: self.text_update.emit(t))
        except Exception:
            pass

        # 等引擎连接就绪再开始推音频（录音线程此时已在积累数据）
        if hasattr(self._engine, '_ws_ready'):
            self._engine._ws_ready.wait(timeout=3.0)
            print(f"[录音] 引擎就绪 +{_t.time()-_t0:.3f}s，开始推送音频 (积压: {self._audio_queue.qsize()} 帧)")

        sent_idx = 0
        while self._recording or (self._audio_queue and not self._audio_queue.empty()):
            try:
                data = self._audio_queue.get(timeout=0.3)
                if sent_idx < 5:
                    print(f"[录音] 推送第 {sent_idx} 帧给引擎, t=+{_t.time()-_t0:.3f}s")
                sent_idx += 1
                self._engine.send_audio(data)
            except queue.Empty:
                continue
        print(f"[录音] 共推送 {sent_idx} 帧给引擎")

        final_text = self._engine.stop()

        if self._app_obj:
            QMetaObject.invokeMethod(
                self._app_obj,
                "_on_recording_done",
                Qt.QueuedConnection,
                Q_ARG(str, final_text)
            )
