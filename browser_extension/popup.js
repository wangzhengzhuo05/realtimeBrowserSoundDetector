/**
 * 课堂音频监听助手 - Popup 控制界面
 */

// DOM 元素
const serverDot = document.getElementById('serverDot');
const serverStatus = document.getElementById('serverStatus');
const captureDot = document.getElementById('captureDot');
const captureStatus = document.getElementById('captureStatus');
const volumeBar = document.getElementById('volumeBar');
const serverUrlInput = document.getElementById('serverUrl');
const enablePlaybackCheckbox = document.getElementById('enablePlayback');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');

// 从 storage 加载保存的设置
chrome.storage.local.get(['serverUrl', 'enablePlayback'], (result) => {
    if (result.serverUrl) {
        serverUrlInput.value = result.serverUrl;
    }
    // 默认开启外放
    enablePlaybackCheckbox.checked = result.enablePlayback !== false;
});

// 保存服务器地址
serverUrlInput.addEventListener('change', () => {
    chrome.storage.local.set({ serverUrl: serverUrlInput.value });
});

// 保存外放设置
enablePlaybackCheckbox.addEventListener('change', () => {
    chrome.storage.local.set({ enablePlayback: enablePlaybackCheckbox.checked });
});

// 更新状态显示
function updateStatus(state) {
    // 服务器状态
    if (state.wsConnected) {
        serverDot.classList.add('connected');
        serverStatus.textContent = '已连接';
    } else {
        serverDot.classList.remove('connected');
        serverStatus.textContent = '未连接';
    }

    // 捕获状态
    if (state.isCapturing) {
        captureDot.classList.add('connected', 'capturing');
        captureStatus.textContent = '捕获中...';
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        captureDot.classList.remove('connected', 'capturing');
        captureStatus.textContent = '未开始';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }

    // 音量显示
    if (state.volume !== undefined) {
        volumeBar.style.width = `${Math.min(state.volume * 100, 100)}%`;
    }
}

// 获取当前状态
function refreshStatus() {
    chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
        if (response) {
            updateStatus(response);
        }
    });
}

// 开始捕获
startBtn.addEventListener('click', async () => {
    const serverUrl = serverUrlInput.value.trim();
    if (!serverUrl) {
        alert('请输入服务器地址');
        return;
    }

    // 保存服务器地址
    chrome.storage.local.set({ serverUrl });

    // 发送开始命令
    chrome.runtime.sendMessage({
        type: 'START_CAPTURE',
        serverUrl: serverUrl,
        enablePlayback: enablePlaybackCheckbox.checked
    }, (response) => {
        if (response && response.success) {
            refreshStatus();
        } else {
            alert(response?.error || '启动失败');
        }
    });
});

// 停止捕获
stopBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'STOP_CAPTURE' }, () => {
        refreshStatus();
    });
});

// 定时刷新状态
refreshStatus();
setInterval(refreshStatus, 500);
