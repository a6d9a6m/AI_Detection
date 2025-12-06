// Dashboard JavaScript

// 当前用户信息
let currentUser = null;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadStats();
    setupEventListeners();
});

// 加载当前用户信息
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            currentUser = await response.json();
            document.getElementById('username').textContent = currentUser.username;
            document.getElementById('user-avatar').textContent = currentUser.username[0].toUpperCase();
        } else {
            // 未登录，跳转到登录页
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Failed to load user:', error);
    }
}

// 加载统计数据
async function loadStats() {
    try {
        // 加载声纹数据数量
        const voiceprintsResp = await fetch('/api/voiceprints?limit=1');
        if (voiceprintsResp.ok) {
            const data = await voiceprintsResp.json();
            document.getElementById('stat-voiceprints').textContent = data.count || 0;
        }

        // 加载模型数量
        const modelsResp = await fetch('/api/models');
        if (modelsResp.ok) {
            const data = await modelsResp.json();
            document.getElementById('stat-models').textContent = data.count || 0;
        }

        // 加载报告数量
        const reportsResp = await fetch('/api/reports');
        if (reportsResp.ok) {
            const data = await reportsResp.json();
            document.getElementById('stat-reports').textContent = data.count || 0;
        }

        // API调用数（mock）
        document.getElementById('stat-api-calls').textContent = Math.floor(Math.random() * 1000);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 文件上传
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }

    // 拖拽上传
    const uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileUpload();
            }
        });
    }

    // 搜索
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }

    // 表单提交
    const trainingForm = document.getElementById('training-form');
    if (trainingForm) {
        trainingForm.addEventListener('submit', handleTrainingSubmit);
    }

    const reportForm = document.getElementById('report-form');
    if (reportForm) {
        reportForm.addEventListener('submit', handleReportSubmit);
    }

    const apiKeyForm = document.getElementById('api-key-form');
    if (apiKeyForm) {
        apiKeyForm.addEventListener('submit', handleApiKeySubmit);
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 显示页面
function showPage(pageName) {
    // 隐藏所有页面
    const pages = document.querySelectorAll('.page-content');
    pages.forEach(page => page.style.display = 'none');

    // 移除所有导航链接的active类
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => link.classList.remove('active'));

    // 显示选中的页面
    const targetPage = document.getElementById(`${pageName}-page`);
    if (targetPage) {
        targetPage.style.display = 'block';
    }

    // 添加active类到对应的导航链接
    const targetLink = document.querySelector(`[onclick="showPage('${pageName}')"]`);
    if (targetLink) {
        targetLink.classList.add('active');
    }

    // 更新页面标题
    const titles = {
        'overview': '概览',
        'data': '声纹数据管理',
        'training': '模型训练',
        'models': '模型管理',
        'reports': '报告管理',
        'api': 'API管理',
        'system': '系统监控'
    };
    document.getElementById('page-title').textContent = titles[pageName] || '概览';

    // 加载页面数据
    switch (pageName) {
        case 'data':
            loadVoiceprints();
            break;
        case 'training':
            loadTrainingTasks();
            break;
        case 'models':
            loadModels();
            break;
        case 'reports':
            loadReports();
            break;
        case 'system':
            loadSystemStatus();
            break;
    }
}

// 加载声纹数据列表
async function loadVoiceprints() {
    const tbody = document.getElementById('voiceprints-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;"><div class="loading"></div> 加载中...</td></tr>';

    try {
        const response = await fetch('/api/voiceprints?limit=100');
        const data = await response.json();

        if (data.data && data.data.length > 0) {
            tbody.innerHTML = data.data.map(item => `
                <tr>
                    <td>${item.filename}</td>
                    <td><span class="badge badge-primary">${item.machine_type || 'N/A'}</span></td>
                    <td>${item.section || 'N/A'}</td>
                    <td>${formatFileSize(item.file_size)}</td>
                    <td>${formatDate(item.uploaded_at)}</td>
                    <td>
                        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="downloadVoiceprint(${item.id})">下载</button>
                        <button class="btn btn-danger" style="padding: 4px 8px; font-size: 12px;" onclick="deleteVoiceprint(${item.id})">删除</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-icon">📭</div><div class="empty-title">暂无数据</div></td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger-color);">加载失败: ${error.message}</td></tr>`;
    }
}

// 文件上传处理
async function handleFileUpload() {
    const fileInput = document.getElementById('file-input');
    const files = fileInput.files;

    if (files.length === 0) return;

    const machineType = document.getElementById('upload-machine-type').value;
    const section = document.getElementById('upload-section').value;

    for (let file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('machine_type', machineType);
        formData.append('section', section);

        try {
            const response = await fetch('/api/voiceprints', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                showNotification('上传成功: ' + file.name, 'success');
            } else {
                const error = await response.json();
                showNotification('上传失败: ' + error.error, 'error');
            }
        } catch (error) {
            showNotification('上传失败: ' + error.message, 'error');
        }
    }

    // 刷新列表
    loadVoiceprints();
    fileInput.value = '';
}

// 搜索处理
async function handleSearch() {
    const query = document.getElementById('search-input').value;
    if (!query) {
        loadVoiceprints();
        return;
    }

    const tbody = document.getElementById('voiceprints-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;"><div class="loading"></div> 搜索中...</td></tr>';

    try {
        const response = await fetch(`/api/voiceprints/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.results && data.results.length > 0) {
            tbody.innerHTML = data.results.map(item => `
                <tr>
                    <td>${item.filename}</td>
                    <td><span class="badge badge-primary">${item.machine_type || 'N/A'}</span></td>
                    <td>${item.section || 'N/A'}</td>
                    <td>${formatFileSize(item.file_size)}</td>
                    <td>${formatDate(item.uploaded_at)}</td>
                    <td>
                        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="downloadVoiceprint(${item.id})">下载</button>
                        <button class="btn btn-danger" style="padding: 4px 8px; font-size: 12px;" onclick="deleteVoiceprint(${item.id})">删除</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-title">未找到匹配的数据</div></td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger-color);">搜索失败: ${error.message}</td></tr>`;
    }
}

// 下载声纹数据
function downloadVoiceprint(id) {
    window.open(`/api/voiceprints/${id}/download`, '_blank');
}

// 删除声纹数据
async function deleteVoiceprint(id) {
    if (!confirm('确定要删除这条数据吗？')) return;

    try {
        const response = await fetch(`/api/voiceprints/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('删除成功', 'success');
            loadVoiceprints();
        } else {
            const error = await response.json();
            showNotification('删除失败: ' + error.error, 'error');
        }
    } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
    }
}

// 加载训练任务列表
async function loadTrainingTasks() {
    const tbody = document.getElementById('training-tasks-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;"><div class="loading"></div> 加载中...</td></tr>';

    try {
        const response = await fetch('/api/training/tasks');
        const data = await response.json();

        if (data.tasks && data.tasks.length > 0) {
            tbody.innerHTML = data.tasks.map(task => {
                const statusBadge = getStatusBadge(task.status);
                return `
                    <tr>
                        <td>${task.id}</td>
                        <td>${task.machine_type}</td>
                        <td>${statusBadge}</td>
                        <td>${task.progress}%</td>
                        <td>${formatDate(task.created_at)}</td>
                        <td>
                            <button class="btn btn-outline" style="padding: 4px 8px; font-size: 12px;" onclick="viewTask(${task.id})">查看</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-icon">📭</div><div class="empty-title">暂无训练任务</div></td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger-color);">加载失败: ${error.message}</td></tr>`;
    }
}

// 提交训练任务
async function handleTrainingSubmit(e) {
    e.preventDefault();

    const config = {
        machine_type: document.getElementById('train-machine-type').value,
        model_type: document.getElementById('train-model-type').value,
        train_dir: document.getElementById('train-dir').value,
        epochs: parseInt(document.getElementById('train-epochs').value),
        batch_size: parseInt(document.getElementById('train-batch-size').value),
        learning_rate: parseFloat(document.getElementById('train-lr').value),
        model_name: `model_${document.getElementById('train-machine-type').value}`,
        version: '1.0'
    };

    try {
        const response = await fetch('/api/training/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('训练任务已启动！', 'success');
            loadTrainingTasks();
        } else {
            showNotification('启动失败: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('启动失败: ' + error.message, 'error');
    }
}

// 加载模型列表
async function loadModels() {
    const tbody = document.getElementById('models-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;"><div class="loading"></div> 加载中...</td></tr>';

    try {
        const response = await fetch('/api/models');
        const data = await response.json();

        if (data.models && data.models.length > 0) {
            tbody.innerHTML = data.models.map(model => `
                <tr>
                    <td>${model.name}</td>
                    <td><span class="badge badge-info">${model.version}</span></td>
                    <td>${model.machine_type}</td>
                    <td>${model.model_type}</td>
                    <td>${formatDate(model.created_at)}</td>
                    <td>
                        <button class="btn btn-outline" style="padding: 4px 8px; font-size: 12px;" onclick="viewModel(${model.id})">详情</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-icon">📭</div><div class="empty-title">暂无模型</div></td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger-color);">加载失败: ${error.message}</td></tr>`;
    }
}

// 加载报告列表
async function loadReports() {
    const tbody = document.getElementById('reports-tbody');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;"><div class="loading"></div> 加载中...</td></tr>';

    try {
        const response = await fetch('/api/reports');
        const data = await response.json();

        if (data.reports && data.reports.length > 0) {
            tbody.innerHTML = data.reports.map(report => `
                <tr>
                    <td>${report.title}</td>
                    <td><span class="badge badge-success">${report.report_type}</span></td>
                    <td>${formatDate(report.created_at)}</td>
                    <td>
                        <button class="btn btn-primary" style="padding: 4px 8px; font-size: 12px;" onclick="downloadReport(${report.id})">下载</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><div class="empty-icon">📭</div><div class="empty-title">暂无报告</div></td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--danger-color);">加载失败: ${error.message}</td></tr>`;
    }
}

// 生成报告
async function handleReportSubmit(e) {
    e.preventDefault();

    const config = {
        title: document.getElementById('report-title').value,
        report_type: 'anomaly_detection',
        format: document.getElementById('report-format').value,
        content: {
            generated_by: currentUser ? currentUser.username : 'Unknown'
        }
    };

    try {
        const response = await fetch('/api/reports/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('报告生成成功！', 'success');
            loadReports();
        } else {
            showNotification('生成失败: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('生成失败: ' + error.message, 'error');
    }
}

// 下载报告
function downloadReport(id) {
    window.open(`/api/reports/${id}/download`, '_blank');
}

// 创建API密钥
async function handleApiKeySubmit(e) {
    e.preventDefault();

    const name = document.getElementById('api-key-name').value;

    try {
        const response = await fetch('/api/keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, permissions: ['read', 'write'] })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('new-api-key').textContent = data.api_key;
            document.getElementById('new-key-card').style.display = 'block';
            document.getElementById('api-key-form').reset();
            showNotification('API密钥创建成功！', 'success');
        } else {
            showNotification('创建失败: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('创建失败: ' + error.message, 'error');
    }
}

// 加载系统状态
async function loadSystemStatus() {
    const content = document.getElementById('system-status-content');
    content.innerHTML = '<div class="loading"></div> 加载中...';

    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        content.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon green">✅</div>
                    <div class="stat-value">${data.status}</div>
                    <div class="stat-label">系统状态</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon blue">💾</div>
                    <div class="stat-value">${data.metrics.cpu_usage}%</div>
                    <div class="stat-label">CPU使用率</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon orange">🧠</div>
                    <div class="stat-value">${data.metrics.memory_usage}%</div>
                    <div class="stat-label">内存使用率</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon red">💿</div>
                    <div class="stat-value">${data.metrics.disk_usage}%</div>
                    <div class="stat-label">磁盘使用率</div>
                </div>
            </div>
            <h4 style="margin: 20px 0;">服务状态</h4>
            <div style="display: grid; gap: 12px;">
                ${Object.entries(data.services).map(([key, value]) => `
                    <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(30, 136, 229, 0.05); border-radius: 8px;">
                        <span>${key}</span>
                        <span class="badge badge-success">${value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        content.innerHTML = `<div style="color: var(--danger-color);">加载失败: ${error.message}</div>`;
    }
}

// 退出登录
async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/';
    } catch (error) {
        console.error('Logout failed:', error);
        window.location.href = '/';
    }
}

// 工具函数
function formatFileSize(bytes) {
    if (!bytes) return 'N/A';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge badge-warning">等待中</span>',
        'running': '<span class="badge badge-info">运行中</span>',
        'completed': '<span class="badge badge-success">已完成</span>',
        'failed': '<span class="badge badge-danger">失败</span>'
    };
    return badges[status] || '<span class="badge">' + status + '</span>';
}

function showNotification(message, type = 'info') {
    // 简单的通知实现
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function viewTask(id) {
    alert('查看任务详情: ' + id);
}

function viewModel(id) {
    alert('查看模型详情: ' + id);
}
