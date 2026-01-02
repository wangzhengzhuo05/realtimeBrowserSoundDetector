/**
 * 课堂音频监听助手 - Background Service Worker
 * 使用 Offscreen Document 进行音频捕获
 */

// 状态管理
let state = {
    isCapturing: false,
    wsConnected: false,
    volume: 0
};

let offscreenCreated = false;

/**
 * 创建 Offscreen Document
 */
async function setupOffscreenDocument() {
    // 检查是否已存在
    const existingContexts = await chrome.runtime.getContexts({
        contextTypes: ['OFFSCREEN_DOCUMENT']
    });

    if (existingContexts.length > 0) {
        offscreenCreated = true;
        return;
    }

    // 创建 offscreen document
    await chrome.offscreen.createDocument({
        url: 'offscreen.html',
        reasons: ['USER_MEDIA'],
        justification: '需要捕获标签页音频进行语音识别'
    });

    offscreenCreated = true;
    console.log('[Background] Offscreen document 已创建');
}

/**
 * 关闭 Offscreen Document
 */
async function closeOffscreenDocument() {
    if (!offscreenCreated) return;

    try {
        await chrome.offscreen.closeDocument();
        offscreenCreated = false;
        console.log('[Background] Offscreen document 已关闭');
    } catch (e) {
        console.log('[Background] 关闭 offscreen 时出错:', e);
    }
}

/**
 * 开始捕获音频
 */
async function startCapture(serverUrl) {
    try {
        // 获取当前标签页
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) {
            throw new Error('未找到活动标签页');
        }

        console.log('[Background] 当前标签页:', tab.id, tab.url);

        // 获取媒体流 ID
        const streamId = await chrome.tabCapture.getMediaStreamId({
            targetTabId: tab.id
        });

        console.log('[Background] 获取到 streamId:', streamId);

        // 创建 offscreen document
        await setupOffscreenDocument();

        // 等待一下确保 offscreen 准备好
        await new Promise(resolve => setTimeout(resolve, 100));

        // 发送消息给 offscreen document 开始捕获
        const response = await chrome.runtime.sendMessage({
            type: 'START_CAPTURE_OFFSCREEN',
            streamId: streamId,
            serverUrl: serverUrl
        });

        if (response && response.success) {
            state.isCapturing = true;
            state.wsConnected = true;
            console.log('[Background] 音频捕获已启动');
            return { success: true };
        } else {
            throw new Error(response?.error || '启动失败');
        }

    } catch (error) {
        console.error('[Background] 启动失败:', error);
        state.isCapturing = false;
        state.wsConnected = false;
        return { success: false, error: error.message };
    }
}

/**
 * 停止捕获
 */
async function stopCapture() {
    try {
        // 发送停止消息
        await chrome.runtime.sendMessage({ type: 'STOP_CAPTURE_OFFSCREEN' });
    } catch (e) {
        console.log('[Background] 停止消息发送失败:', e);
    }

    state.isCapturing = false;
    state.wsConnected = false;
    state.volume = 0;

    // 关闭 offscreen document
    await closeOffscreenDocument();

    console.log('[Background] 已停止捕获');
}

// 监听来自 popup 和 offscreen 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('[Background] 收到消息:', message.type);

    switch (message.type) {
        case 'GET_STATUS':
            sendResponse(state);
            break;

        case 'START_CAPTURE':
            startCapture(message.serverUrl).then(sendResponse);
            return true; // 异步响应

        case 'STOP_CAPTURE':
            stopCapture().then(() => sendResponse({ success: true }));
            return true;

        case 'VOLUME_UPDATE':
            // 来自 offscreen 的音量更新
            state.volume = message.volume;
            break;
    }
});

console.log('[Background] Service Worker 已启动');
