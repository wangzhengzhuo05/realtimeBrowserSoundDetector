# 🎓 课堂监听报警系统 (Classroom Audio Monitor)

实时监听网课音频，自动识别关键词并触发报警提醒，再也不用担心错过老师的点名签到！

## ✨ 功能特点

- 🌐 **浏览器音频捕获** - 通过 Chrome 扩展直接捕获浏览器标签页音频
- 🎙️ **实时语音识别** - 支持阿里云 DashScope API 和本地 FunASR 两种模式
- 🔔 **关键词报警** - 检测到指定关键词时自动播放报警声
- 🎵 **自定义报警音** - 支持自定义 .wav 格式报警音频
- 🔄 **自动重连** - ASR 连接断开时自动重连，稳定可靠
- 📦 **模块化设计** - 代码结构清晰，易于扩展和维护

## 📁 项目结构

```
realtimeBrowserSoundDetector/
├── main.py                 # 程序入口
├── monitor.py              # 主控制器
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── asr/                    # 语音识别模块
│   ├── __init__.py
│   ├── base.py             # ASR 基类
│   ├── dashscope_asr.py    # 阿里云 DashScope ASR
│   └── funasr_engine.py    # 本地 FunASR
├── audio/                  # 音频处理模块
│   ├── __init__.py
│   └── server.py           # WebSocket 服务器
├── alert/                  # 报警模块
│   ├── __init__.py
│   └── keyword_alert.py    # 关键词检测与报警
└── browser_extension/      # Chrome 浏览器扩展
    ├── manifest.json
    ├── background.js
    ├── popup.html
    ├── popup.js
    ├── offscreen.html
    └── offscreen.js
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/yourusername/realtimeBrowserSoundDetector.git
cd realtimeBrowserSoundDetector

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `config.py` 文件，填入你的阿里云 DashScope API Key：

```python
DASHSCOPE_API_KEY = "your-api-key-here"
```

> 💡 **获取 API Key**: 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)，注册并开通服务（有免费额度）

### 3. 安装浏览器扩展

1. 打开 Chrome 浏览器，访问 `chrome://extensions/`
2. 开启右上角的 **"开发者模式"**
3. 点击 **"加载已解压的扩展程序"**
4. 选择项目中的 `browser_extension` 文件夹
5. 扩展安装完成！

### 4. 启动程序

```bash
python main.py
```

### 5. 开始监听

1. 打开网课页面（如腾讯会议、钉钉直播、学习通等）
2. 点击浏览器工具栏中的扩展图标
3. 点击 **"开始捕获音频"** 按钮
4. 系统开始实时识别语音，检测到关键词自动报警！

## ⚙️ 配置说明

编辑 `config.py` 自定义配置：

```python
# ASR 模式: True = 云端 API, False = 本地模型
USE_CLOUD_API = True

# 监控关键词列表
ALERT_KEYWORDS = ["签到", "点名", "打开手机", "扫码", "考勤", "输入码", "钉钉", "上课"]

# 报警冷却时间（秒）
ALERT_COOLDOWN = 5

# 自定义报警音频 (可选，支持 .wav 格式)
CUSTOM_ALERT_SOUND = None  # 或 "D:/sounds/alert.wav"
```

## 🔊 自定义报警音

1. 准备一个 `.wav` 格式的音频文件
2. 在 `config.py` 中设置路径：
   ```python
   CUSTOM_ALERT_SOUND = "D:/sounds/你的报警音.wav"
   ```
3. 重启程序即可生效

## 📋 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.8+
- **浏览器**: Chrome / Edge (Chromium 内核)
- **网络**: 使用云端 API 需要联网

## 🛠️ 技术栈

- **后端**: Python 3, asyncio, websockets
- **语音识别**: 阿里云 DashScope (paraformer-realtime-v2) / FunASR
- **浏览器扩展**: Chrome Extension Manifest V3
- **音频格式**: 16kHz PCM 16-bit Mono

## 📝 常见问题

### Q: 提示 "DashScope 连接失败"？
A: 请检查 API Key 是否正确，以及网络是否正常。

### Q: 浏览器扩展无法捕获音频？
A: 确保已授予扩展 "标签页音频捕获" 权限，并且目标页面正在播放音频。

### Q: 识别不准确？
A: 云端 API 识别效果更好，确保 `USE_CLOUD_API = True`。

### Q: 没有声音报警？
A: 检查系统音量设置，确保扬声器正常工作。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**⭐ 如果觉得有用，请给个 Star 支持一下！**
