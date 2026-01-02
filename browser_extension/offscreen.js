/**
 * Offscreen Document - 负责实际的音频捕获和处理
 * 在 Manifest V3 中，tabCapture 需要在 offscreen document 中使用
 */

// 音频配置
const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

let ws = null;
let mediaStream = null;
let audioContext = null;
let processor = null;
let isCapturing = false;

/**
 * 开始音频捕获
 */
async function startCapture(streamId, serverUrl) {
    try {
        console.log('[Offscreen] 开始捕获，streamId:', streamId);

        // 连接 WebSocket
        ws = new WebSocket(serverUrl);

        await new Promise((resolve, reject) => {
            ws.onopen = () => {
                console.log('[Offscreen] WebSocket 已连接');
                resolve();
            };
            ws.onerror = (e) => {
                console.error('[Offscreen] WebSocket 错误:', e);
                reject(new Error('WebSocket 连接失败'));
            };
            // 设置超时
            setTimeout(() => reject(new Error('WebSocket 连接超时')), 5000);
        });

        ws.onclose = () => {
            console.log('[Offscreen] WebSocket 已关闭');
            stopCapture();
        };

        // 使用 streamId 获取媒体流
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                mandatory: {
                    chromeMediaSource: 'tab',
                    chromeMediaSourceId: streamId
                }
            },
            video: false
        });

        console.log('[Offscreen] 获取媒体流成功');

        // 创建音频处理上下文
        audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
        const source = audioContext.createMediaStreamSource(mediaStream);

        // 创建 ScriptProcessor
        processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);

        processor.onaudioprocess = (event) => {
            if (!isCapturing || !ws || ws.readyState !== WebSocket.OPEN) {
                return;
            }

            const inputData = event.inputBuffer.getChannelData(0);

            // 计算音量并发送到 background
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i];
            }
            const volume = Math.sqrt(sum / inputData.length);

            // 发送音量更新
            chrome.runtime.sendMessage({
                type: 'VOLUME_UPDATE',
                volume: volume
            });

            // 转换为 16-bit PCM
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            // 发送到服务器
            ws.send(pcmData.buffer);
        };

        // 连接音频节点
        source.connect(processor);
        processor.connect(audioContext.destination);

        isCapturing = true;
        console.log('[Offscreen] 音频捕获已启动');

        return { success: true };

    } catch (error) {
        console.error('[Offscreen] 启动失败:', error);
        stopCapture();
        return { success: false, error: error.message };
    }
}

/**
 * 停止音频捕获
 */
function stopCapture() {
    isCapturing = false;

    if (ws) {
        ws.close();
        ws = null;
    }

    if (processor) {
        processor.disconnect();
        processor = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }

    console.log('[Offscreen] 已停止捕获');
}

// 监听来自 background 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('[Offscreen] 收到消息:', message.type);

    if (message.type === 'START_CAPTURE_OFFSCREEN') {
        startCapture(message.streamId, message.serverUrl)
            .then(result => sendResponse(result));
        return true; // 异步响应
    }

    if (message.type === 'STOP_CAPTURE_OFFSCREEN') {
        stopCapture();
        sendResponse({ success: true });
    }

    if (message.type === 'GET_CAPTURE_STATUS') {
        sendResponse({ isCapturing });
    }
});

console.log('[Offscreen] Document 已加载');
