"""火山引擎 BigModel 流式语音识别引擎"""

import asyncio
import gzip
import json
import queue
import struct
import threading
import uuid

import websockets

from voice_typing.engine.base import BaseEngine

WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
RESOURCE_ID = "volc.bigasr.sauc.duration"

HDR_CONFIG = bytes([0x11, 0x10, 0x11, 0x00])
HDR_AUDIO = bytes([0x11, 0x20, 0x01, 0x00])
HDR_AUDIO_LAST = bytes([0x11, 0x22, 0x01, 0x00])


def _build_frame(header: bytes, payload: bytes) -> bytes:
    compressed = gzip.compress(payload)
    return header + struct.pack(">I", len(compressed)) + compressed


def _parse_response(msg: bytes):
    """解析二进制响应帧，返回 (text, is_final)

    BigModel 2.0 帧布局: [4字节header][4字节序列号][4字节payload长度][payload]
    payload 是否 gzip 由 header 字节 2 的低 4 位决定（0=无压缩，1=gzip）。
    """
    if len(msg) < 12:
        return "", False
    compression = msg[2] & 0x0F
    payload_len = struct.unpack(">I", msg[8:12])[0]
    payload = msg[12:12 + payload_len]
    if compression == 1:
        payload = gzip.decompress(payload)
    data = json.loads(payload)
    if "code" in data and data["code"] != 20000000:
        return "", False
    results = data.get("result", {})
    if isinstance(results, list):
        if not results:
            return "", False
        results = results[0]
    text = results.get("text", "")
    # BigModel 2.0 的 definite 在 utterances[0] 里；服务端最后帧会带 NEG_SEQUENCE flag
    utterances = results.get("utterances") or []
    is_final = (utterances and utterances[0].get("definite", False)) or (msg[1] & 0x02) != 0
    return text, is_final


class VolcengineEngine(BaseEngine):
    """火山引擎流式语音识别（BigModel ASR v2）"""

    name = "火山引擎 BigModel ASR"

    def __init__(self, app_id: str = "", access_token: str = "", hotwords: list = None, resource_id: str = "", api_key: str = "", hotword_id: str = "", replace_word_id: str = ""):
        self._app_id = app_id
        self._access_token = access_token
        self._api_key = api_key  # 新版认证（单 key）
        self._hotwords = hotwords or []
        self._hotword_id = hotword_id  # 云端热词表 ID
        self._replace_word_id = replace_word_id  # 云端替换词表 ID
        self._resource_id = resource_id or RESOURCE_ID
        self._running = False
        self._audio_queue = None
        self._text_callback = None
        self._final_text = ""
        self._ws_done = None

    def initialize(self) -> bool:
        return bool(self._api_key or (self._app_id and self._access_token))

    def is_available(self) -> bool:
        return bool(self._api_key or (self._app_id and self._access_token))

    def set_text_callback(self, cb):
        self._text_callback = cb

    def start(self):
        self._running = True
        self._audio_queue = queue.Queue()
        self._final_text = ""
        self._ws_done = threading.Event()
        self._ws_ready = threading.Event()  # WebSocket 连接就绪
        threading.Thread(target=self._run_ws, daemon=True).start()

    def _run_ws(self):
        asyncio.run(self._ws_session())

    async def _ws_session(self):
        # 新版认证（单 X-Api-Key）vs 旧版（App-Key + Access-Key）
        if self._api_key:
            headers = {
                "X-Api-Key": self._api_key,
                "X-Api-Resource-Id": self._resource_id,
                "X-Api-Request-Id": str(uuid.uuid4()),
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }
            print(f"[ASR] 引擎: 火山引擎 Seed-ASR (新版认证)")
            print(f"[ASR] API: {WS_URL}")
            print(f"[ASR] X-Api-Key: {self._api_key[:8]}...({len(self._api_key)})")
        else:
            headers = {
                "X-Api-App-Key": self._app_id,
                "X-Api-Access-Key": self._access_token,
                "X-Api-Resource-Id": self._resource_id,
                "X-Api-Request-Id": str(uuid.uuid4()),
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }
            print(f"[ASR] 引擎: 火山引擎 BigModel (旧版认证)")
            print(f"[ASR] API: {WS_URL}")
            print(f"[ASR] X-Api-App-Key: {self._app_id}")
            print(f"[ASR] X-Api-Access-Key: {self._access_token[:8]}...({len(self._access_token)})")
        print(f"[ASR] X-Api-Resource-Id: {self._resource_id}")
        if self._hotwords:
            print(f"[ASR] 热词: {len(self._hotwords)} 个")
        try:
            async with websockets.connect(
                WS_URL,
                extra_headers=headers,
                max_size=10_000_000,
                ping_interval=20,
            ) as ws:
                config = {
                    "user": {"uid": "voice-typing"},
                    "audio": {
                        "format": "pcm", "codec": "raw",
                        "rate": 16000, "bits": 16, "channel": 1,
                    },
                    "request": {
                        "model_name": "bigmodel",
                        "enable_itn": True,
                        "enable_punc": True,
                        "result_type": "single",
                        "language": "zh-CN",
                    },
                }
                if self._hotwords:
                    config["request"]["hotwords"] = self._hotwords
                if self._hotword_id:
                    config["request"]["boosting_table_id"] = self._hotword_id
                    print(f"[ASR] 云端热词ID(boosting_table_id): {self._hotword_id}")
                if self._replace_word_id:
                    config["request"]["correct_table_id"] = self._replace_word_id
                    print(f"[ASR] 云端替换词ID(correct_table_id): {self._replace_word_id}")
                payload = json.dumps(config).encode()
                await ws.send(_build_frame(HDR_CONFIG, payload))
                import time as _t
                _conn_time = _t.time()
                print(f"[ASR] WebSocket 已连接，config 已发送")
                self._ws_ready.set()  # 通知：可以开始发音频了

                async def send_loop():
                    loop = asyncio.get_event_loop()
                    _first_sent = [False]
                    while self._running:
                        try:
                            data = await loop.run_in_executor(
                                None, lambda: self._audio_queue.get(timeout=0.3)
                            )
                        except queue.Empty:
                            continue
                        if not _first_sent[0]:
                            print(f"[ASR] 首帧音频发出，距连接: {_t.time() - _conn_time:.3f}s")
                            _first_sent[0] = True
                        await ws.send(_build_frame(HDR_AUDIO, data))
                    # drain remaining audio
                    while True:
                        try:
                            data = self._audio_queue.get_nowait()
                            await ws.send(_build_frame(HDR_AUDIO, data))
                        except queue.Empty:
                            break
                    await ws.send(_build_frame(HDR_AUDIO_LAST, b""))

                async def recv_loop():
                    final_parts = []
                    async for msg in ws:
                        text, is_final = _parse_response(msg)
                        if not text:
                            continue
                        print(f"[ASR] 收到帧: is_final={is_final}, text={text!r}")
                        if is_final:
                            # 去重：避免两遍识别返回相同句子
                            if text not in final_parts:
                                final_parts.append(text)
                            else:
                                print(f"[ASR] 检测到重复句子，已跳过: {text!r}")
                            self._final_text = "".join(final_parts)
                            preview = self._final_text
                            print(f"[ASR] final_parts={final_parts!r}")
                        else:
                            preview = "".join(final_parts) + text
                        if self._text_callback:
                            self._text_callback(preview)

                await asyncio.gather(send_loop(), recv_loop())
        except Exception as e:
            print(f"[Volcengine] WS 连接异常: {e}")
        finally:
            self._ws_done.set()

    def send_audio(self, pcm_bytes: bytes):
        if self._running and self._audio_queue is not None:
            self._audio_queue.put(pcm_bytes)

    def stop(self) -> str:
        self._running = False
        self._ws_done.wait(timeout=10)
        return self._final_text.strip()
