// Audio Anomaly Detection System - Frontend JavaScript

// Global variables
let socket = null;
let currentTab = 'train';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize Socket.IO
    socket = io();

    // Load configuration
    loadConfig();

    // Setup event listeners
    setupEventListeners();

    // Setup socket listeners
    setupSocketListeners();
}

function loadConfig() {
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            // Populate checkpoint dropdowns
            const trainCheckpoint = document.getElementById('test-checkpoint');
            const realtimeCheckpoint = document.getElementById('realtime-checkpoint');

            data.checkpoints.forEach(checkpoint => {
                const option1 = new Option(checkpoint, 'checkpoints/' + checkpoint);
                const option2 = new Option(checkpoint, 'checkpoints/' + checkpoint);
                trainCheckpoint.add(option1);
                realtimeCheckpoint.add(option2);
            });
        })
        .catch(error => {
            console.error('Failed to load config:', error);
        });
}

function refreshCheckpoints() {
    loadConfig();
    alert('检查点列表已刷新！');
}

// Tab switching
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    event.target.classList.add('active');

    currentTab = tabName;
}

// Event listeners setup
function setupEventListeners() {
    // Train form
    document.getElementById('train-form').addEventListener('submit', handleTrainSubmit);

    // Test form
    document.getElementById('test-form').addEventListener('submit', handleTestSubmit);

    // Realtime form
    document.getElementById('realtime-form').addEventListener('submit', handleRealtimeSubmit);
}

// Socket.IO event listeners
function setupSocketListeners() {
    // Training events
    socket.on('training_log', function(data) {
        appendToOutput('train-output', data.message, 'log-normal');
    });

    socket.on('training_complete', function(data) {
        const statusBox = document.getElementById('train-status');
        statusBox.textContent = data.message;
        statusBox.className = 'status-box ' + (data.returncode === 0 ? 'completed' : 'stopped');
    });

    // Testing events
    socket.on('testing_log', function(data) {
        appendToOutput('test-output', data.message, 'log-normal');
    });

    socket.on('testing_complete', function(data) {
        const statusBox = document.getElementById('test-status');
        statusBox.textContent = data.message;
        statusBox.className = 'status-box ' + (data.returncode === 0 ? 'completed' : 'stopped');

        // Display results
        if (data.results && Object.keys(data.results).length > 0) {
            displayTestResults(data.results);
        }
    });

    // Real-time detection events
    socket.on('realtime_status', function(data) {
        const statusIndicator = document.getElementById('detection-status');
        statusIndicator.textContent = data.message || data.status;
        statusIndicator.className = 'status-indicator ' + data.status;
    });

    socket.on('realtime_data', function(data) {
        updateRealtimeDisplay(data);
    });

    socket.on('realtime_log', function(data) {
        appendToOutput('realtime-output', data.message, 'log-info');
    });

    socket.on('realtime_stopped', function(data) {
        const statusIndicator = document.getElementById('detection-status');
        statusIndicator.textContent = '已停止';
        statusIndicator.className = 'status-indicator stopped';
        appendToOutput('realtime-output', '检测已停止: ' + data.message, 'log-info');
    });
}

// Handle train form submission
function handleTrainSubmit(event) {
    event.preventDefault();

    const data = {
        // 基本配置
        train_dir: document.getElementById('train-dir').value,
        machine_type: document.getElementById('train-machine-type').value,
        output_dir: document.getElementById('train-output-dir').value,

        // 训练参数
        epochs: parseInt(document.getElementById('train-epochs').value),
        batch_size: parseInt(document.getElementById('train-batch').value),
        lr: parseFloat(document.getElementById('train-lr').value),
        weight_decay: parseFloat(document.getElementById('train-weight-decay').value),
        optimizer: document.getElementById('train-optimizer').value,
        scheduler: document.getElementById('train-scheduler').value,
        warmup_epochs: parseInt(document.getElementById('train-warmup').value),
        num_workers: parseInt(document.getElementById('train-workers').value),
        save_interval: parseInt(document.getElementById('train-save-interval').value),
        seed: parseInt(document.getElementById('train-seed').value),

        // 特征提取参数
        sr: parseInt(document.getElementById('train-sr').value),
        n_mels: parseInt(document.getElementById('train-n-mels').value),
        n_fft: parseInt(document.getElementById('train-n-fft').value),
        hop_length: parseInt(document.getElementById('train-hop-length').value),
        fmin: parseInt(document.getElementById('train-fmin').value),
        fmax: parseInt(document.getElementById('train-fmax').value),
        patch_frames: parseInt(document.getElementById('train-patch-frames').value),

        // 模型参数
        width_mult: parseFloat(document.getElementById('train-width-mult').value),
        dropout_rate: parseFloat(document.getElementById('train-dropout').value),

        // 数据增强
        augmentation: document.getElementById('train-augmentation').checked,
        aug_volume_min: parseFloat(document.getElementById('train-aug-vol-min').value),
        aug_volume_max: parseFloat(document.getElementById('train-aug-vol-max').value),
        aug_time_shift: parseInt(document.getElementById('train-aug-time-shift').value),
        aug_freq_mask: parseInt(document.getElementById('train-aug-freq-mask').value),
        aug_time_mask: parseInt(document.getElementById('train-aug-time-mask').value)
    };

    // Clear previous output
    document.getElementById('train-output').innerHTML = '';
    document.getElementById('train-status').textContent = '正在启动训练...';
    document.getElementById('train-status').className = 'status-box running';

    fetch('/api/train', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'error') {
            alert('错误: ' + result.message);
            document.getElementById('train-status').textContent = '错误: ' + result.message;
            document.getElementById('train-status').className = 'status-box stopped';
        }
    })
    .catch(error => {
        alert('启动训练失败: ' + error);
        document.getElementById('train-status').textContent = '启动失败';
        document.getElementById('train-status').className = 'status-box stopped';
    });
}

// Handle test form submission
function handleTestSubmit(event) {
    event.preventDefault();

    const data = {
        checkpoint: document.getElementById('test-checkpoint').value,
        machine_type: document.getElementById('test-machine-type').value,
        train_dir: document.getElementById('test-train-dir').value,
        test_dir: document.getElementById('test-test-dir').value,
        patch_frames: parseInt(document.getElementById('test-patch-frames').value),
        hop_frames: parseInt(document.getElementById('test-hop-frames').value)
    };

    if (!data.checkpoint) {
        alert('请选择一个checkpoint');
        return;
    }

    // Clear previous output
    document.getElementById('test-output').innerHTML = '';
    document.getElementById('test-results').innerHTML = '';
    document.getElementById('test-status').textContent = '正在启动测试...';
    document.getElementById('test-status').className = 'status-box running';

    fetch('/api/test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'error') {
            alert('错误: ' + result.message);
            document.getElementById('test-status').textContent = '错误: ' + result.message;
            document.getElementById('test-status').className = 'status-box stopped';
        }
    })
    .catch(error => {
        alert('启动测试失败: ' + error);
        document.getElementById('test-status').textContent = '启动失败';
        document.getElementById('test-status').className = 'status-box stopped';
    });
}

// Handle realtime form submission
function handleRealtimeSubmit(event) {
    event.preventDefault();

    const source = document.getElementById('realtime-source').value;
    const data = {
        checkpoint: document.getElementById('realtime-checkpoint').value,
        source: source,
        device: document.getElementById('realtime-device').value,
        threshold: parseFloat(document.getElementById('realtime-threshold').value),
        patch_frames: parseInt(document.getElementById('realtime-patch-frames').value),
        buffer_duration: parseFloat(document.getElementById('realtime-buffer-duration').value),
        hop_duration: parseFloat(document.getElementById('realtime-hop-duration').value),
        enable_playback: document.getElementById('enable-playback').checked
    };

    if (!data.checkpoint) {
        alert('请选择一个checkpoint');
        return;
    }

    if (source === 'file') {
        data.audio_file = document.getElementById('realtime-audio-file').value;
        if (!data.audio_file) {
            alert('请输入音频文件路径');
            return;
        }
        // 添加实时模式参数
        data.realtime = document.getElementById('realtime-mode').checked;
    } else {
        const deviceId = document.getElementById('realtime-device-id').value;
        if (deviceId) {
            data.device_id = parseInt(deviceId);
        }
    }

    // Clear previous output
    document.getElementById('realtime-output').innerHTML = '';
    resetRealtimeStats();

    // Emit socket event to start real-time detection
    socket.emit('start_realtime', data);
}

// Stop realtime detection
function stopRealtime() {
    socket.emit('stop_realtime');
}

// Stop a task
function stopTask(task) {
    fetch('/api/stop/' + task, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(result => {
        alert(result.message);
    })
    .catch(error => {
        alert('Failed to stop task: ' + error);
    });
}

// Toggle audio source fields
function toggleAudioSource() {
    const source = document.getElementById('realtime-source').value;
    const fileGroup = document.getElementById('audio-file-group');
    const deviceGroup = document.getElementById('device-id-group');
    const realtimeModeGroup = document.getElementById('realtime-mode-group');

    if (source === 'file') {
        fileGroup.style.display = 'block';
        deviceGroup.style.display = 'none';
        realtimeModeGroup.style.display = 'block';
    } else {
        fileGroup.style.display = 'none';
        deviceGroup.style.display = 'block';
        realtimeModeGroup.style.display = 'none';
    }
}

// Append message to output box
function appendToOutput(elementId, message, className) {
    const outputBox = document.getElementById(elementId);
    const entry = document.createElement('div');
    entry.className = 'log-entry ' + className;
    entry.textContent = message;
    outputBox.appendChild(entry);

    // Auto-scroll to bottom
    outputBox.scrollTop = outputBox.scrollHeight;
}

// Display test results
function displayTestResults(results) {
    const resultsGrid = document.getElementById('test-results');
    resultsGrid.innerHTML = '';

    const resultItems = [
        { label: 'Baseline AUC', value: results.baseline },
        { label: 'Mean Based AUC', value: results.mean_based },
        { label: 'Comprehensive AUC', value: results.comprehensive },
        { label: 'Best AUC', value: results.best_auc }
    ];

    resultItems.forEach(item => {
        if (item.value !== undefined) {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.innerHTML = `
                <div class="label">${item.label}</div>
                <div class="value">${item.value.toFixed(4)}</div>
            `;
            resultsGrid.appendChild(card);
        }
    });
}

// Update real-time detection display
function updateRealtimeDisplay(data) {
    // Update last detection
    const lastDetection = document.getElementById('last-detection');
    const isAnomaly = data.is_anomaly;

    lastDetection.className = 'detection-result ' + (isAnomaly ? 'detection-anomaly' : 'detection-normal');
    lastDetection.innerHTML = `
        <div class="detection-label">${isAnomaly ? '🚨 ANOMALY DETECTED' : '✓ Normal'}</div>
        <div class="detection-score">Score: ${data.score.toFixed(4)}</div>
        <div class="detection-class">Class: ${data.predicted_class} (${(data.class_confidence * 100).toFixed(1)}%)</div>
        <div class="detection-class">Max Prob: ${data.max_prob.toFixed(4)} | Entropy: ${data.entropy.toFixed(4)}</div>
    `;

    // Update statistics
    document.getElementById('stat-total').textContent = data.total_detections;
    document.getElementById('stat-anomalies').textContent = data.total_anomalies;
    document.getElementById('stat-rate').textContent = data.anomaly_rate.toFixed(2) + '%';

    // Update status
    const statusIndicator = document.getElementById('detection-status');
    statusIndicator.textContent = '运行中';
    statusIndicator.className = 'status-indicator running';

    // Add to output log
    const timestamp = data.timestamp || new Date().toLocaleTimeString();
    const status = isAnomaly ? '🚨 ANOMALY' : '✓ Normal';
    const logClass = isAnomaly ? 'log-anomaly' : 'log-normal';
    const message = `[${timestamp}] ${status} | Score: ${data.score.toFixed(4)} | Class: ${data.predicted_class} | MaxProb: ${data.max_prob.toFixed(4)}`;

    appendToOutput('realtime-output', message, logClass);
}

// Reset real-time statistics
function resetRealtimeStats() {
    document.getElementById('stat-total').textContent = '0';
    document.getElementById('stat-anomalies').textContent = '0';
    document.getElementById('stat-rate').textContent = '0%';

    const lastDetection = document.getElementById('last-detection');
    lastDetection.className = 'detection-result';
    lastDetection.innerHTML = '<div class="detection-label">Waiting...</div>';
}
