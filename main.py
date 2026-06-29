#!/usr/bin/env python3
"""兼容旧版入口，调用新的包结构"""
import sys, fcntl, os

# 单实例锁，防止重复启动
_lock_file = os.path.expanduser("~/.cache/voice_typing.lock")
os.makedirs(os.path.dirname(_lock_file), exist_ok=True)
_fp = open(_lock_file, 'w')
try:
    fcntl.flock(_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("VoiceType 已在运行中")
    sys.exit(0)

from voice_typing.app import main

if __name__ == "__main__":
    main()
