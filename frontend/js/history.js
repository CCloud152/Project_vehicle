// 背景图片轮播功能
function initBackgroundSlider() {
    const slides = document.querySelectorAll('.bg-slide');
    let currentSlide = 0;
    const slideInterval = 5000; // 5秒切换一次

    function nextSlide() {
        slides[currentSlide].classList.remove('active');
        currentSlide = (currentSlide + 1) % slides.length;
        slides[currentSlide].classList.add('active');
    }

    setInterval(nextSlide, slideInterval);
}

// 初始化背景轮播
initBackgroundSlider();

document.addEventListener('DOMContentLoaded', () => {
    console.log('历史记录页面加载完成，初始化脚本...');

    // 元素引用
    const historyContainer = document.getElementById('history-container');
    const historyCount = document.getElementById('history-count');
    const statusBar = document.getElementById('status-bar').querySelector('span');

    // 加载历史记录
    loadHistory();

    // ---------------------- 加载历史记录 ----------------------
    async function loadHistory() {
        console.log('开始加载历史记录');
        statusBar.textContent = '加载历史记录中...';
        historyContainer.innerHTML = '<div class="loading">加载历史记录中...</div>';

        try {
            // 获取token（与asyncRecognition.js保持一致）
            const token = localStorage.getItem('car_recognition_token');
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch('/api/history', {
                headers: headers
            });
            const data = await response.json();
            console.log('历史记录响应:', data);

            if (data.status === 'success') {
                const records = data.data.records;
                historyCount.textContent = `共 ${records.length} 条记录`;
                renderHistoryRecords(records);
                statusBar.textContent = '加载完成';
            } else {
                historyContainer.innerHTML = `<div class="error">加载失败：${data.message}</div>`;
                statusBar.textContent = `加载失败：${data.message}`;
            }
        } catch (error) {
            console.error('加载历史记录失败:', error);
            historyContainer.innerHTML = `<div class="error">加载失败：${error.message}</div>`;
            statusBar.textContent = `加载失败：${error.message}`;
        }
    }

    // ---------------------- 渲染历史记录 ----------------------
    function renderHistoryRecords(records) {
        if (!records || records.length === 0) {
            historyContainer.innerHTML = '<div class="empty-state">暂无历史记录</div>';
            return;
        }

        historyContainer.innerHTML = '';

        records.forEach(record => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.innerHTML = `
                <img src="/api/uploads/${record.image_filename}" alt="${record.brand} ${record.model}" class="history-image">
                <div class="history-info">
                    <h3>${record.brand} ${record.model}</h3>
                    <div class="history-meta">颜色：${record.color}</div>
                    <div class="history-meta">置信度：${parseFloat(record.confidence).toFixed(2)}</div>
                    <div class="history-meta">识别时间：${formatDate(record.create_time)}</div>
                </div>
                <div class="history-actions">
                    <button class="btn btn-view" data-id="${record.id}">查看</button>
                    <button class="btn btn-delete" data-id="${record.id}">删除</button>
                </div>
            `;
            historyContainer.appendChild(historyItem);
        });

        // 绑定事件
        bindHistoryEvents();
    }

    // ---------------------- 绑定历史记录事件 ----------------------
    function bindHistoryEvents() {
        // 查看按钮事件
        document.querySelectorAll('.btn-view').forEach(button => {
            button.addEventListener('click', async (e) => {
                const recordId = e.target.dataset.id;
                console.log('查看历史记录:', recordId);
                
                // 跳转到首页并传递记录ID
                window.location.href = `/index?id=${recordId}`;
            });
        });

        // 删除按钮事件
        document.querySelectorAll('.btn-delete').forEach(button => {
            button.addEventListener('click', async (e) => {
                const recordId = e.target.dataset.id;
                console.log('删除历史记录:', recordId);

                if (confirm('确定要删除这条记录吗？')) {
                    try {
                        const response = await fetch(`/api/history/${recordId}`, {
                            method: 'DELETE'
                        });
                        const data = await response.json();
                        console.log('删除响应:', data);

                        if (data.status === 'success') {
                            statusBar.textContent = '删除成功';
                            // 重新加载历史记录
                            loadHistory();
                        } else {
                            statusBar.textContent = `删除失败：${data.message}`;
                        }
                    } catch (error) {
                        console.error('删除失败:', error);
                        statusBar.textContent = `删除失败：${error.message}`;
                    }
                }
            });
        });
    }

    // ---------------------- 格式化日期 ----------------------
    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    // 初始状态
    console.log('历史记录脚本初始化完成');
});
