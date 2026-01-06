// API 基础地址
const API_BASE = '';

// 自动保存防抖计时器
let autoSaveTimer = null;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    connectStatusWebSocket();

    // 表单提交
    document.getElementById('configForm').addEventListener('submit', saveConfig);

    // 检测模式切换
    document.getElementById('detectMode').addEventListener('change', function () {
        const isQwen2 = this.value === 'qwen2-audio';
        document.getElementById('asrModeGroup').style.display = isQwen2 ? 'none' : 'block';
        document.getElementById('semanticOptions').style.display =
            (!isQwen2 && document.getElementById('enableSemantic').checked) ? 'grid' : 'none';
        triggerAutoSave();
    });

    // 语义匹配开关
    document.getElementById('enableSemantic').addEventListener('change', function () {
        const isQwen2 = document.getElementById('detectMode').value === 'qwen2-audio';
        document.getElementById('semanticOptions').style.display =
            (!isQwen2 && this.checked) ? 'grid' : 'none';
        triggerAutoSave();
    });

    // Debug 模式切换视图
    document.getElementById('debugMode').addEventListener('change', function () {
        switchRecognitionView(this.checked);
        triggerAutoSave();
    });

    // 阈值滑块
    document.getElementById('semanticThreshold').addEventListener('input', function () {
        document.getElementById('thresholdValue').textContent = this.value;
        triggerAutoSave();
    });

    // 为其他表单元素添加自动保存
    setupAutoSave();
});

// 设置自动保存监听
function setupAutoSave() {
    const fields = [
        'useCloudApi', 'apiKey', 'wsHost', 'wsPort',
        'keywords', 'cooldown', 'customSound', 'semanticModel', 'alertMode'
    ];

    fields.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            const eventType = (element.tagName === 'SELECT' || element.type === 'checkbox') ? 'change' : 'input';
            element.addEventListener(eventType, triggerAutoSave);
        }
    });
}

// 触发自动保存（防抖）
function triggerAutoSave() {
    // 清除之前的计时器
    if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
    }

    // 1秒后自动保存
    autoSaveTimer = setTimeout(async () => {
        await saveConfigAuto();
    }, 1000);
}

// 自动保存配置（静默保存，无toast提示）
async function saveConfigAuto() {
    const keywordsText = document.getElementById('keywords').value;
    const keywords = keywordsText
        .split(/[,\n，]/)
        .map(k => k.trim())
        .filter(k => k.length > 0);

    const detectMode = document.getElementById('detectMode').value;
    const debugMode = document.getElementById('debugMode').checked;
    const config = {
        detect_mode: detectMode,
        debug_mode: debugMode,
        use_cloud_api: document.getElementById('useCloudApi').value === 'true',
        api_key: document.getElementById('apiKey').value,
        ws_host: document.getElementById('wsHost').value,
        ws_port: parseInt(document.getElementById('wsPort').value),
        keywords: keywords,
        cooldown: parseInt(document.getElementById('cooldown').value),
        custom_sound: document.getElementById('customSound').value || null,
        alert_mode: document.getElementById('alertMode').value || 'sound',
        enable_semantic: document.getElementById('enableSemantic').checked,
        semantic_threshold: parseFloat(document.getElementById('semanticThreshold').value),
        semantic_model: document.getElementById('semanticModel').value || 'text-embedding-v3'
    };

    try {
        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('自动保存失败');

        // 静默保存，只在控制台显示
        console.log('[自动保存] 配置已保存');

        // 更新状态显示
        document.getElementById('wsStatus').textContent = `ws://${config.ws_host}:${config.ws_port}`;
        const isQwen2 = detectMode === 'qwen2-audio';
        const modeText = debugMode ? 'DEBUG' : (isQwen2 ? 'Qwen2-Audio' : (config.use_cloud_api ? 'DashScope API' : '本地 FunASR'));
        document.getElementById('asrMode').textContent = modeText;
        updateCurrentSoundDisplay(config.custom_sound);

    } catch (error) {
        console.error('[自动保存] 保存失败:', error);
    }
}

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        if (!response.ok) throw new Error('加载配置失败');

        const config = await response.json();

        // 检测模式
        const detectMode = config.detect_mode || 'asr';
        document.getElementById('detectMode').value = detectMode;
        const isQwen2 = detectMode === 'qwen2-audio';
        document.getElementById('asrModeGroup').style.display = isQwen2 ? 'none' : 'block';

        // Debug 模式
        document.getElementById('debugMode').checked = config.debug_mode || false;

        // 根据 Debug 模式切换视图
        switchRecognitionView(config.debug_mode || false);

        // 填充表单
        document.getElementById('useCloudApi').value = config.use_cloud_api.toString();
        document.getElementById('apiKey').value = config.api_key || '';
        document.getElementById('wsHost').value = config.ws_host || 'localhost';
        document.getElementById('wsPort').value = config.ws_port || 8765;
        document.getElementById('keywords').value = (config.keywords || []).join('\n');
        document.getElementById('cooldown').value = config.cooldown || 5;
        document.getElementById('alertMode').value = config.alert_mode || 'sound';
        const customSoundValue = config.custom_sound === null ? '' : (config.custom_sound || '');
        document.getElementById('customSound').value = customSoundValue;

        // 语义匹配配置
        document.getElementById('enableSemantic').checked = config.enable_semantic || false;
        document.getElementById('semanticThreshold').value = config.semantic_threshold || 0.65;
        document.getElementById('thresholdValue').textContent = config.semantic_threshold || 0.65;
        document.getElementById('semanticOptions').style.display =
            (!isQwen2 && config.enable_semantic) ? 'grid' : 'none';
        document.getElementById('semanticModel').value = config.semantic_model || 'text-embedding-v3';

        // 更新状态显示
        document.getElementById('wsStatus').textContent = `ws://${config.ws_host}:${config.ws_port}`;
        const modeText = config.debug_mode ? 'DEBUG' : (isQwen2 ? 'Qwen2-Audio' : (config.use_cloud_api ? 'DashScope API' : '本地 FunASR'));
        document.getElementById('asrMode').textContent = modeText;

        // 更新当前音源显示
        updateCurrentSoundDisplay(config.custom_sound);

        showToast('配置已加载', 'success');
    } catch (error) {
        console.error('加载配置失败:', error);
        showToast('加载配置失败: ' + error.message, 'error');
    }
}

// 保存配置
async function saveConfig(e) {
    e.preventDefault();

    const keywordsText = document.getElementById('keywords').value;
    const keywords = keywordsText
        .split(/[,\n，]/)
        .map(k => k.trim())
        .filter(k => k.length > 0);

    const detectMode = document.getElementById('detectMode').value;
    const debugMode = document.getElementById('debugMode').checked;
    const config = {
        detect_mode: detectMode,
        debug_mode: debugMode,
        use_cloud_api: document.getElementById('useCloudApi').value === 'true',
        api_key: document.getElementById('apiKey').value,
        ws_host: document.getElementById('wsHost').value,
        ws_port: parseInt(document.getElementById('wsPort').value),
        keywords: keywords,
        cooldown: parseInt(document.getElementById('cooldown').value),
        custom_sound: document.getElementById('customSound').value || null,
        alert_mode: document.getElementById('alertMode').value || 'sound',
        enable_semantic: document.getElementById('enableSemantic').checked,
        semantic_threshold: parseFloat(document.getElementById('semanticThreshold').value),
        semantic_model: document.getElementById('semanticModel').value || 'text-embedding-v3'
    };

    try {
        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('保存配置失败');

        const result = await response.json();
        showToast('✓ 配置已保存', 'success');

        // 更新状态显示
        document.getElementById('wsStatus').textContent = `ws://${config.ws_host}:${config.ws_port}`;
        const isQwen2 = detectMode === 'qwen2-audio';
        const modeText = debugMode ? 'DEBUG' : (isQwen2 ? 'Qwen2-Audio' : (config.use_cloud_api ? 'DashScope API' : '本地 FunASR'));
        document.getElementById('asrMode').textContent = modeText;

        // 更新当前音源显示
        updateCurrentSoundDisplay(config.custom_sound);

        // 保存成功后重新加载配置，确保前端和服务器状态同步
        await loadConfig();

    } catch (error) {
        console.error('保存配置失败:', error);
        showToast('保存配置失败: ' + error.message, 'error');
    }
}

// 更新当前音源显示
function updateCurrentSoundDisplay(customSound) {
    const soundDisplayEl = document.getElementById('currentSound');

    if (!customSound || customSound === null || customSound === '') {
        soundDisplayEl.textContent = '🔔 默认蜂鸣声';
        soundDisplayEl.title = '使用系统内置蜂鸣声';
    } else {
        // 提取文件名
        const fileName = customSound.split(/[/\\]/).pop();
        soundDisplayEl.textContent = `🔊 ${fileName}`;
        soundDisplayEl.title = customSound;
    }
}

// 验证自定义音频路径
async function validateSound() {
    const pathInput = document.getElementById('customSound');
    const resultEl = document.getElementById('soundValidationResult');

    if (!pathInput || !resultEl) {
        console.error('找不到输入框或结果元素');
        alert('验证功能初始化失败，请刷新页面');
        return;
    }

    const path = pathInput.value.trim();

    if (!path) {
        resultEl.textContent = '将使用默认蜂鸣声';
        resultEl.style.color = '';
        return;
    }

    resultEl.textContent = '验证中...';
    resultEl.style.color = '#6b7280';

    try {
        const res = await fetch(`${API_BASE}/api/validate-sound`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();

        if (data.valid) {
            resultEl.textContent = '✅ ' + data.message;
            resultEl.style.color = '#10b981';
        } else {
            resultEl.textContent = '❌ ' + data.message;
            resultEl.style.color = '#ef4444';
        }
    } catch (e) {
        console.error('验证失败:', e);
        resultEl.textContent = '❌ 验证失败: ' + e.message;
        resultEl.style.color = '#ef4444';
    }
}

// 显示音源选择器
async function showSoundPicker() {
    const picker = document.getElementById('soundPicker');
    const listEl = document.getElementById('soundList');

    picker.style.display = 'block';
    listEl.innerHTML = '<p class="placeholder">加载中...</p>';

    try {
        const res = await fetch(`${API_BASE}/api/list-sounds`);
        if (!res.ok) throw new Error('加载音源列表失败');

        const data = await res.json();

        listEl.innerHTML = '';

        // 添加默认音源选项
        const defaultItem = document.createElement('div');
        defaultItem.className = 'sound-item default-sound';
        defaultItem.innerHTML = `
            <div class="sound-info">
                <strong>🔔 默认蜂鸣声</strong>
                <small>系统内置音源</small>
            </div>
            <button type="button" class="btn-small" onclick='selectSound("")'>选择</button>
        `;
        listEl.appendChild(defaultItem);

        if (data.sounds && data.sounds.length > 0) {
            data.sounds.forEach(sound => {
                const item = document.createElement('div');
                item.className = 'sound-item';
                item.innerHTML = `
                    <div class="sound-info">
                        <strong>🔊 ${sound.name}</strong>
                        <small>${sound.format} · ${sound.size}</small>
                    </div>
                    <button type="button" class="btn-small" onclick='selectSound(${JSON.stringify(sound.path)})'>选择</button>
                `;
                listEl.appendChild(item);
            });
        } else {
            const emptyHint = document.createElement('p');
            emptyHint.className = 'placeholder';
            emptyHint.innerHTML = '暂无自定义音源<br><small>请将音频文件放入 assets/custom_sounds/ 目录</small>';
            listEl.appendChild(emptyHint);
        }
    } catch (e) {
        console.error('加载音源列表失败:', e);
        listEl.innerHTML = '<p class="placeholder" style="color: #ef4444;">❌ ' + e.message + '</p>';
    }
}

// 隐藏音源选择器
function hideSoundPicker() {
    document.getElementById('soundPicker').style.display = 'none';
}

// 选择音源
function selectSound(path) {
    const pathInput = document.getElementById('customSound');
    const resultEl = document.getElementById('soundValidationResult');

    pathInput.value = path;
    hideSoundPicker();

    // 立即更新前端音源显示（预览）
    updateCurrentSoundDisplay(path);

    // 触发自动保存
    triggerAutoSave();

    if (!path) {
        resultEl.textContent = '✅ 已选择默认蜂鸣声';
        resultEl.style.color = '#10b981';
    } else {
        validateSound();
    }
}

// 重启服务
async function restartService() {
    if (!confirm('确定要重启服务吗？这将断开所有连接。')) return;

    try {
        const response = await fetch(`${API_BASE}/api/restart`, { method: 'POST' });
        if (!response.ok) throw new Error('重启服务失败');

        showToast('🔄 服务正在重启...', 'warning');

        // 更新状态
        updateStatus('offline', '重启中...');

        // 3秒后重新连接
        setTimeout(() => {
            connectStatusWebSocket();
        }, 3000);

    } catch (error) {
        console.error('重启服务失败:', error);
        showToast('重启服务失败: ' + error.message, 'error');
    }
}

// 切换 API Key 可见性
function toggleApiKeyVisibility() {
    const input = document.getElementById('apiKey');
    input.type = input.type === 'password' ? 'text' : 'password';
}

// 状态 WebSocket 连接
let statusWs = null;
let reconnectTimer = null;

function connectStatusWebSocket() {
    if (statusWs) {
        statusWs.close();
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/status`;

    console.log('[WebSocket] 尝试连接:', wsUrl);

    try {
        statusWs = new WebSocket(wsUrl);

        statusWs.onopen = () => {
            console.log('[WebSocket] 状态 WebSocket 已连接');
            updateStatus('online', '运行中');
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        statusWs.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('[WebSocket] 收到消息:', data);
                handleStatusMessage(data);
            } catch (e) {
                console.error('[WebSocket] 解析状态消息失败:', e);
            }
        };

        statusWs.onclose = (event) => {
            console.log('[WebSocket] 状态 WebSocket 已断开, code:', event.code, 'reason:', event.reason);
            updateStatus('offline', '已断开');
            // 自动重连
            if (!reconnectTimer) {
                reconnectTimer = setTimeout(connectStatusWebSocket, 5000);
            }
        };

        statusWs.onerror = (error) => {
            console.error('[WebSocket] 状态 WebSocket 错误:', error);
            updateStatus('error', '连接错误');
        };

    } catch (e) {
        console.error('[WebSocket] 创建 WebSocket 失败:', e);
        updateStatus('error', '连接失败');
    }
}

// 处理状态消息
function handleStatusMessage(data) {
    switch (data.type) {
        case 'recognition':
            updateRecognition(data.text, data.source);
            break;
        case 'alert':
            addAlertRecord(data.keywords, data.text, data.source);
            break;
        case 'status':
            updateStatus(data.status, data.message);
            break;
        case 'llm_status':
            updateLLMStatus(data.detected, data.reason);
            break;
        case 'code_detected':
            addCodeRecord(data.code, data.timestamp);
            break;
    }
}

// 更新状态显示
function updateStatus(status, text) {
    const statusDot = document.querySelector('#systemStatus .status-dot');
    const statusText = document.getElementById('statusText');

    statusDot.className = 'status-dot ' + status;
    statusText.textContent = text;
}

// 切换识别视图（Debug 双栏/普通单栏）
function switchRecognitionView(isDebugMode) {
    const singleView = document.getElementById('singleRecognitionView');
    const debugView = document.getElementById('debugRecognitionView');

    if (isDebugMode) {
        singleView.style.display = 'none';
        debugView.style.display = 'grid';
    } else {
        singleView.style.display = 'block';
        debugView.style.display = 'none';
    }
}

// 更新识别结果
function updateRecognition(text, source) {
    const isDebugMode = document.getElementById('debugMode').checked;
    let box;

    if (isDebugMode) {
        // Debug 模式：根据来源选择不同的框
        switchRecognitionView(true);
        if (source === 'qwen2-audio') {
            box = document.getElementById('qwen2RecognitionBox');
        } else {
            // ASR 或默认
            box = document.getElementById('asrRecognitionBox');
        }
    } else {
        // 普通模式：使用单栏
        switchRecognitionView(false);
        box = document.getElementById('recognitionBox');
    }

    const placeholder = box.querySelector('.placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    // 追加文本或更新最后一行
    const lines = box.querySelectorAll('p:not(.placeholder)');
    if (lines.length > 0) {
        const lastLine = lines[lines.length - 1];
        lastLine.textContent = text;
    } else {
        const p = document.createElement('p');
        p.textContent = text;
        box.appendChild(p);
    }

    // 限制行数
    while (box.children.length > 20) {
        box.removeChild(box.firstChild);
    }

    // 滚动到底部
    box.scrollTop = box.scrollHeight;
}

// 添加报警记录
function addAlertRecord(keywords, text, source) {
    const list = document.getElementById('alertList');
    const placeholder = list.querySelector('.placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const item = document.createElement('div');
    item.className = 'alert-item';

    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN');

    // Debug 模式下显示来源
    const isDebugMode = document.getElementById('debugMode').checked;
    const sourceTag = isDebugMode && source ? `<span class="source-tag ${source}">${source === 'qwen2-audio' ? '🤖' : '🎤'}</span>` : '';

    item.innerHTML = `
        <span class="time">[${timeStr}]</span>
        ${sourceTag}
        <span class="keyword">${keywords.join(', ')}</span>
        <span class="text">${text.substring(0, 50)}${text.length > 50 ? '...' : ''}</span>
    `;

    list.insertBefore(item, list.firstChild);

    // 限制记录数
    while (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }

    // 播放提示音
    playAlertSound();
}

// 添加签到码记录
function addCodeRecord(code, timestamp) {
    const list = document.getElementById('codeList');
    const placeholder = list.querySelector('.placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const item = document.createElement('div');
    item.className = 'code-item';

    item.innerHTML = `
        <span class="code-number">📋 ${code}</span>
        <span class="code-time">${timestamp}</span>
        <button class="copy-btn" onclick="copyCode('${code}')" title="复制">📋</button>
    `;

    list.insertBefore(item, list.firstChild);

    // 限制记录数
    while (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }

    // 显示提示
    showToast(`检测到签到码: ${code}`, 'info');
}

// 复制签到码到剪贴板
function copyCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        showToast(`已复制: ${code}`, 'success');
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

// 播放提示音（网页端）
function playAlertSound() {
    try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleRIvlNfl1pVmEQdSrufp0IFSAAhdr/Dm0IZdBxdc');
        audio.play().catch(e => console.log('播放提示音失败'));
    } catch (e) {
        console.log('创建音频失败');
    }
}

// 更新 LLM 检测状态
function updateLLMStatus(detected, reason) {
    const statusEl = document.getElementById('llmStatus');
    if (!statusEl) return;

    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN');

    if (detected) {
        statusEl.className = 'llm-status detected';
        statusEl.innerHTML = `<span class="time">[${timeStr}]</span> ✅ 检测到签到意图`;
    } else {
        statusEl.className = 'llm-status not-detected';
        statusEl.innerHTML = `<span class="time">[${timeStr}]</span> ❌ 未检测到签到意图${reason ? ': ' + reason : ''}`;
    }
}

// 显示 Toast 消息
function showToast(message, type = 'success') {
    // 移除现有的 toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // 触发动画
    setTimeout(() => toast.classList.add('show'), 10);

    // 3秒后移除
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
