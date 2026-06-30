# ChineseVoiceInput · AI 中文语音输入工具

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#许可)
[![Platform](https://img.shields.io/badge/platform-Ubuntu%20%2F%20X11-orange)](#系统要求)

> Ubuntu 桌面下的实时 AI 语音转文字工具。快捷键触发说话，识别 + 润色后自动粘贴到光标处。

## ✨ 功能特性

- 🎤 **实时语音转写** —— Siri 风格彩色动画浮窗，录音时展开波浪，待机时旋转圆环
- ⌨️ **自动粘贴** —— 识别完成后文字直接落到当前光标位置
- 🔥 **双触发模式** —— 「按住说话」或「双击触发 + 任意键停止」
- ☁️ **双云端 ASR 引擎** —— 阿里云 Paraformer / 火山引擎 BigModel（支持 Seed-ASR 2.0）
- 🪄 **独立润色引擎** —— 可选 阿里 Qwen / 豆包 / DeepSeek，也可关闭润色
- 📝 **多模式风格提示词** —— 日常 / 专业 / 自定义，每个模式独立提示词
- 📒 **自定义热词** —— 一键同步到云端，提升专业术语识别率
- 🛡️ **单实例锁** —— 防止重复启动
- ⏱️ **录音保护** —— 最长 20 秒自动停止，避免过度消耗
- 🎨 **暗黑极简界面** —— 主页面集成所有设置，侧边栏一键退出

## 系统要求

- **操作系统**：Ubuntu / 其他 Linux 桌面，**X11 会话**（Wayland 下全局快捷键与粘贴可能失效）
- **Python**：3.8+
- **云端账号**：阿里云 DashScope 或火山引擎二选一

## 📦 安装

```bash
# 系统依赖
sudo apt install xclip xdotool portaudio19-dev

# 拉取代码并安装 Python 依赖
git clone https://github.com/Jerey-Jobs/ChineseVoiceInput.git
cd ChineseVoiceInput
pip install -r requirements.txt

# 启动
python3 main.py
```

## 🚀 使用

首次运行会打开设置窗口（主页面已集成所有设置）：

1. **选择 ASR 引擎** —— 阿里云 Paraformer 或 火山引擎 BigModel
2. **配置凭证**
   - 阿里云：填入 [DashScope API Key](https://dashscope.console.aliyun.com/)
   - 火山引擎（旧版）：App ID + Access Token
   - 火山引擎（新版）：API Key + Resource ID（支持 `volc.seedasr.sauc.duration`）
3. **选择润色模型** —— 关闭 / 阿里 Qwen / 豆包 / DeepSeek
4. **润色强度** —— 轻度 / 中度 / 重度
5. **设置快捷键** —— 支持「按住说话」和「双击触发」两种模式
6. **自定义风格** —— 多模式切换（日常/专业/自定义），每个模式独立提示词
7. *(可选)* **自定义词库** —— 添加专业术语，一键同步热词到云端

**语音输入流程**：

- **按住模式**：按住快捷键说话 → 松开 → 润色 → 粘贴
- **双击模式**：双击触发键开始录音 → 说完按任意键停止 → 润色 → 粘贴

## 🔧 故障排查

| 现象 | 排查方向 |
|------|----------|
| 快捷键无响应 | 是否与系统快捷键冲突；尝试更换组合键；确认 X11 会话 |
| 录音无声音 | 检查麦克风权限；`arecord -l` 确认设备 |
| 粘贴失败 | 确认已安装 `xclip` + `xdotool`；确认 X11 |
| ASR 报错 401 | 检查 API Key 是否正确、是否过期 |
| 润色无效果 | 确认润色模型未设为"关闭"；检查对应 LLM 的 Key |
| ALSA/Jack 警告 | 无害日志，不影响功能 |

## ⚙️ 配置文件

```
~/.config/voice_typing/config.json
```

包含：引擎选择、API 凭证、润色模型、润色强度、快捷键、触发模式、自定义词库、风格模式等。

## 📄 许可

[MIT License](LICENSE)

## 🔗 相关链接

- 阿里云 DashScope 控制台：<https://dashscope.console.aliyun.com/>
- 火山引擎语音控制台：<https://console.volcengine.com/speech/new/experience/asr>
- 火山引擎 ARK 控制台：<https://console.volcengine.com/ark/>
- DeepSeek 开放平台：<https://platform.deepseek.com/>
