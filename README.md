# 🎓 课堂监听报警系统 (Classroom Audio Monitor)

实时监听网课音频，自动识别关键词并触发报警提醒，再也不用担心错过老师的点名签到！

## ✨ 功能特点

- 🌐 **浏览器音频捕获** - 通过 Chrome 扩展直接捕获浏览器标签页音频
- 🎙️ **实时语音识别** - 支持阿里云 DashScope API 和本地 FunASR 两种模式
- 🔔 **关键词报警** - 检测到指定关键词时自动播放报警声
- 🎵 **自定义报警音** - 支持 wav/mp3/ogg/m4a/flac 等多种音频格式
- 🖥️ **Web 控制面板** - 在浏览器中可视化配置和管理
- 🔄 **自动重连** - ASR 连接断开时自动重连，稳定可靠
- 📦 **模块化设计** - 代码结构清晰，易于扩展和维护

## 📁 项目结构

```
realtimeBrowserSoundDetector/
├── main.py                 # 程序入口
├── monitor.py              # 主控制器 (基础版)
├── monitor_web.py          # 主控制器 (Web 增强版)
├── config.py               # 配置文件 (旧版)
├── config_manager.py       # 动态配置管理器
├── config.json             # 配置数据 (自动生成)
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
├── web/                    # Web 控制面板
│   ├── __init__.py
│   ├── server.py           # HTTP/WebSocket 服务器
│   └── static/             # 前端静态文件
│       ├── index.html
│       ├── style.css
│       └── app.js
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
git clone https://github.com/wangzhengzhuo05/realtimeBrowserSoundDetector.git
cd realtimeBrowserSoundDetector

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动程序

```bash
python main.py
```

### 3. 配置系统

打开浏览器访问 **http://localhost:8080** ，在 Web 控制面板中：

1. 通过环境变量 `DASHSCOPE_API_KEY` 设置 DashScope API Key（推荐，避免写入仓库），或在 Web 控制面板中填写后保存
     - 也可以在项目根目录创建 `.secrets.json`（不会被 git 追踪），内容示例：
         ```json
         { "api_key": "your-api-key" }
         ```
2. 设置需要监控的关键词
3. 点击「保存配置」
4. 点击「重启服务」使配置生效

> 💡 **获取 API Key**: 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)，注册并开通服务（有免费额度）

### 4. 安装浏览器扩展

1. 打开 Chrome 浏览器，访问 `chrome://extensions/`
2. 开启右上角的 **"开发者模式"**
3. 点击 **"加载已解压的扩展程序"**
4. 选择项目中的 `browser_extension` 文件夹
5. 扩展安装完成！

### 5. 开始监听

1. 打开网课页面（如腾讯会议、钉钉直播、学习通等）
2. 点击浏览器工具栏中的扩展图标
3. 点击 **"开始捕获音频"** 按钮
4. 系统开始实时识别语音，检测到关键词自动报警！

## ⚙️ 配置说明

通过 Web 控制面板 (http://localhost:8080) 可以配置以下参数：

| 参数       | 说明                                         |
| ---------- | -------------------------------------------- |
| ASR 模式   | 云端 API 或本地模型                          |
| API Key    | DashScope API 密钥                           |
| 监控关键词 | 触发报警的关键词列表                         |
| 冷却时间   | 报警间隔时间（秒）                           |
| 自定义音频 | 支持 wav/mp3/ogg/m4a/flac 等格式（相对路径） |

配置会自动保存到 `config.json` 文件。

## 🔊 自定义报警音

### 方式一：通过 Web 控制面板（推荐）

1. 将音频文件放入 `assets/custom_sounds/` 目录
2. 打开 Web 控制面板 (http://localhost:8080)
3. 在配置区域点击文件夹图标选择音源
4. 系统自动保存并生效（无需重启）

### 方式二：手动配置

在 `config.json` 中设置相对路径：
```json
{
  "custom_sound": "assets/custom_sounds/alarm.mp3"
}
```

### 支持的音频格式

- **.wav** - Windows 原生支持，无需额外依赖
- **.mp3/.ogg/.m4a/.flac** - 需要安装 `playsound==1.2.2`（已包含在 requirements.txt）

> 💡 **提示**: 使用相对路径确保跨电脑兼容性

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

## � TODO / 已知问题

- [ ] **自定义音频跨电脑兼容性问题** - 部分用户反馈在新电脑上即使已安装 playsound 且音频文件存在，仍然无法播放自定义音频（一直使用默认蜂鸣声）。路径解析和热更新逻辑已实现，但在某些环境下可能存在兼容性问题。临时解决方案：使用 .wav 格式音频，或检查 playsound 库在特定环境下的兼容性。

## �📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**⭐ 如果觉得有用，请给个 Star 支持一下！**
