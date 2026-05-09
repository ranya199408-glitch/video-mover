/**
 * Video-Mover Web UI JavaScript
 */

// State
const state = {
    currentTab: 'download',
    ws: null,
    tasks: {}
};

// 字段中文标签映射
const FIELD_LABELS = {
    // 字幕
    include_subtitles: '启用字幕',
    subtitles_opacity: '字幕透明度',
    use_whisper: '使用Whisper AI',
    whisper_model_name: 'Whisper模型',
    subtitles_color: '字幕颜色',
    subtitles_duration: '字幕时长阈值',
    // 标题
    include_titles: '启用标题',
    titles_opacity: '标题透明度',
    top_title: '顶部标题',
    top_title_margin: '顶部标题边距',
    bottom_title: '底部标题',
    bottom_title_margin: '底部标题边距',
    // 水印
    include_watermark: '启用水印',
    watermark_type: '水印类型',
    watermark_text: '水印文字',
    watermark_opacity: '水印透明度',
    watermark_direction: '水印方向',
    watermark_color: '水印颜色',
    // 音频
    enable_silence_check: '静音检测',
    silence_threshold: '静音阈值',
    silence_retention_ratio: '静音保留比例',
    silent_duration: '静音持续时间',
    include_background_music: '背景音乐',
    background_music_volume: '背景音乐音量',
    // 视频变换
    flip_horizontal: '水平镜像',
    rotation_angle: '旋转角度',
    crop_percentage: '裁剪比例',
    fade_in_frames: '淡入帧数',
    fade_out_frames: '淡出帧数',
    // 画中画
    include_hzh: '启用画中画',
    hzh_opacity: '画中画透明度',
    hzh_scale: '画中画大小',
    // 颜色
    enable_sbc: '颜色调整',
    saturation: '饱和度',
    brightness: '亮度',
    contrast: '对比度',
    // 模糊
    blur_background_enabled: '背景模糊',
    top_blur_percentage: '顶部模糊',
    bottom_blur_percentage: '底部模糊',
    side_blur_percentage: '侧边模糊',
    gaussian_blur_interval: '高斯模糊间隔',
    gaussian_blur_kernel_size: '高斯模糊核',
    gaussian_blur_area_percentage: '高斯模糊区域',
    // 特效
    enable_frame_swap: '帧交换',
    frame_swap_interval: '帧交换间隔',
    enable_color_shift: '颜色偏移',
    color_shift_range: '颜色偏移范围',
    // 高级
    scramble_frequency: '频域扰乱',
    enable_texture_noise: '纹理噪声',
    texture_noise_strength: '噪声强度',
    enable_blur_edge: '边缘模糊',
    // 字体
    custom_font_enabled: '自定义字体',
    font_file: '字体文件',
    text_border_size: '文字描边'
};

// DOM Elements
const elements = {
    navBtns: document.querySelectorAll('.nav-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    logContent: document.getElementById('log-content'),
    downloadUrl: document.getElementById('download-url'),
    downloadTimeRange: document.getElementById('download-time-range'),
    downloadStartBtn: document.getElementById('download-start-btn'),
    downloadStatus: document.getElementById('download-status'),
    dedupInput: document.getElementById('dedup-input'),
    dedupOutput: document.getElementById('dedup-output'),
    dedupBrowseBtn: document.getElementById('dedup-browse-btn'),
    dedupStartBtn: document.getElementById('dedup-start-btn'),
    dedupStatus: document.getElementById('dedup-status'),
    dedupSettings: document.getElementById('dedup-settings'),
    configContent: document.getElementById('config-content'),
    configSaveBtn: document.getElementById('config-save-btn'),
    configMessage: document.getElementById('config-message')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initWebSocket();
    initDownload();
    initDedup();
    initConfig();
    loadConfigGroups();
});

// Tab Navigation
function initTabs() {
    elements.navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
}

function switchTab(tab) {
    // Update nav buttons
    elements.navBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // Update tab content
    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tab}-tab`);
    });

    state.currentTab = tab;
}

// WebSocket for Logs
function initWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/logs`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
        addLog('System', 'WebSocket connected');
    };

    state.ws.onmessage = (event) => {
        addLog('INFO', event.data);
    };

    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        addLog('System', 'WebSocket disconnected');
        // Reconnect after 3 seconds
        setTimeout(initWebSocket, 3000);
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function addLog(source, message) {
    const logContent = elements.logContent;
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = `[${new Date().toLocaleTimeString()}] [${source}] ${message}`;
    logContent.appendChild(line);
    logContent.scrollTop = logContent.scrollHeight;
}

// Download Functions
function initDownload() {
    elements.downloadStartBtn.addEventListener('click', startDownload);
}

async function startDownload() {
    const url = elements.downloadUrl.value.trim();
    const timeRange = elements.downloadTimeRange.value.trim();

    if (!url) {
        showStatus(elements.downloadStatus, 'error', '请输入TikTok URL');
        return;
    }

    elements.downloadStartBtn.disabled = true;
    showStatus(elements.downloadStatus, 'info', '正在启动下载...');

    try {
        const response = await fetch('/api/download/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, time_range: timeRange })
        });

        const data = await response.json();
        state.tasks[data.task_id] = data;

        showStatus(elements.downloadStatus, 'info', `任务已创建: ${data.task_id}`);

        // Poll for status
        pollTaskStatus(data.task_id, elements.downloadStatus);

    } catch (error) {
        showStatus(elements.downloadStatus, 'error', `错误: ${error.message}`);
        elements.downloadStartBtn.disabled = false;
    }
}

async function pollTaskStatus(taskId, statusElement) {
    const poll = async () => {
        try {
            const response = await fetch(`/api/download/status/${taskId}`);
            const data = await response.json();

            if (data.status === 'running') {
                showStatus(statusElement, 'info', `进度: ${data.progress}%`);
            } else if (data.status === 'completed') {
                showStatus(statusElement, 'success', `完成! 结果: ${JSON.stringify(data.result)}`);
                elements.downloadStartBtn.disabled = false;
                return;
            } else if (data.status === 'failed') {
                showStatus(statusElement, 'error', `失败: ${data.error}`);
                elements.downloadStartBtn.disabled = false;
                return;
            }

            // Continue polling
            setTimeout(poll, 2000);

        } catch (error) {
            console.error('Poll error:', error);
        }
    };

    poll();
}

// Dedup Functions
async function loadConfigGroups() {
    try {
        const response = await fetch('/api/dedup/config/groups');
        const groups = await response.json();

        // Get default config
        const defaultResponse = await fetch('/api/config/video-defaults');
        const defaults = await defaultResponse.json();

        // Render settings grid
        let html = '';
        for (const [groupKey, group] of Object.entries(groups)) {
            html += `<div class="settings-group"><h4>${group.label}</h4><div class="settings-grid">`;

            for (const field of group.fields) {
                const value = defaults[field];
                const label = FIELD_LABELS[field] || field;
                const type = typeof value === 'boolean' ? 'checkbox' : typeof value === 'number' ? 'number' : 'text';

                if (type === 'checkbox') {
                    html += `
                        <div class="setting-item">
                            <label>
                                <input type="checkbox" id="dedup-${field}" ${value ? 'checked' : ''}>
                                ${label}
                            </label>
                        </div>
                    `;
                } else if (type === 'number') {
                    const max = field.includes('percentage') || field.includes('margin') || field.includes('ratio') ? 100 : field.includes('opacity') || field.includes('volume') || field.includes('strength') ? 1 : 10;
                    const step = field.includes('percentage') || field.includes('margin') ? 1 : 0.1;
                    html += `
                        <div class="setting-item">
                            <label>${label}</label>
                            <input type="range" id="dedup-${field}" min="0" max="${max}" step="${step}" value="${value}">
                            <span class="value-display">${value}</span>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="setting-item">
                            <label>${label}</label>
                            <input type="text" id="dedup-${field}" value="${value}">
                        </div>
                    `;
                }
            }

            html += '</div></div>';
        }

        elements.dedupSettings.innerHTML = html;

        // Add range slider listeners
        elements.dedupSettings.querySelectorAll('input[type="range"]').forEach(input => {
            input.addEventListener('input', (e) => {
                const display = e.target.parentElement.querySelector('.value-display');
                if (display) display.textContent = e.target.value;
            });
        });

    } catch (error) {
        console.error('Failed to load config groups:', error);
    }
}

function initDedup() {
    elements.dedupStartBtn.addEventListener('click', startDedup);

    // File input element
    const fileInput = document.getElementById('dedup-file-btn');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // Get the full path using webkitRelativePath or path property
                const path = file.webkitRelativePath || file.path || file.name;
                elements.dedupInput.value = path;
            }
        });
    }

    // Folder input element
    const folderInput = document.getElementById('dedup-folder-btn');
    if (folderInput) {
        folderInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                // Get the folder path from the first file
                const firstFile = files[0];
                const folderPath = firstFile.webkitRelativePath.split('/')[0];
                elements.dedupInput.value = folderPath + '/';

                // Store files for batch processing
                state.dedupFolderFiles = Array.from(files).filter(f => f.type.startsWith('video/') || /\.(mp4|avi|mov|mkv|flv|wmv)$/i.test(f.name));
            }
        });
    }
}

async function startDedup() {
    const inputFile = elements.dedupInput.value.trim();
    const outputFile = elements.dedupOutput.value.trim();

    if (!inputFile) {
        showStatus(elements.dedupStatus, 'error', '请输入视频文件路径');
        return;
    }

    // Collect config values
    const config = {};
    elements.dedupSettings.querySelectorAll('input').forEach(input => {
        const field = input.id.replace('dedup-', '');
        if (input.type === 'checkbox') {
            config[field] = input.checked;
        } else if (input.type === 'range') {
            config[field] = parseFloat(input.value);
        } else {
            config[field] = isNaN(parseFloat(input.value)) ? input.value : parseFloat(input.value);
        }
    });

    elements.dedupStartBtn.disabled = true;
    showStatus(elements.dedupStatus, 'info', '正在启动去重处理...');

    try {
        const response = await fetch('/api/dedup/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input_file: inputFile, output_file: outputFile || null, config })
        });

        const data = await response.json();
        state.tasks[data.task_id] = data;

        showStatus(elements.dedupStatus, 'info', `任务已创建: ${data.task_id}`);
        pollTaskStatus(data.task_id, elements.dedupStatus);

    } catch (error) {
        showStatus(elements.dedupStatus, 'error', `错误: ${error.message}`);
        elements.dedupStartBtn.disabled = false;
    }
}

// Config Functions
async function initConfig() {
    // Load config on tab switch
    elements.configContent.addEventListener('focus', loadConfig);

    elements.configSaveBtn.addEventListener('click', saveConfig);
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config/yaml');
        const config = await response.json();
        elements.configContent.value = JSON.stringify(config, null, 2);
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

async function saveConfig() {
    try {
        const content = JSON.parse(elements.configContent.value);
        const response = await fetch('/api/config/yaml', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            showMessage(elements.configMessage, 'success', '配置已保存');
        } else {
            throw new Error('Failed to save');
        }
    } catch (error) {
        showMessage(elements.configMessage, 'error', `保存失败: ${error.message}`);
    }
}

// Utility Functions
function showStatus(element, type, message) {
    element.className = `status-box show ${type}`;
    element.textContent = message;
}

function showMessage(element, type, message) {
    element.className = `message-box show ${type}`;
    element.textContent = message;
    setTimeout(() => {
        element.className = 'message-box';
    }, 3000);
}
