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
    console.log('页面加载完成，初始化脚本...');

    // 元素引用
    const fileUpload = document.getElementById('file-upload');
    const previewImage = document.getElementById('preview-image');
    const imagePlaceholder = document.getElementById('image-placeholder');
    const startRecognize = document.getElementById('start-recognize');
    const clearAll = document.getElementById('clear-all');
    const statusBar = document.getElementById('status-bar').querySelector('span');
    const zoomIn = document.getElementById('zoom-in');
    const zoomOut = document.getElementById('zoom-out');
    const zoomReset = document.getElementById('zoom-reset');

    // 状态变量
    let currentFilename = null;
    let zoomFactor = 1.0;
    let currentVehicleIndex = 0;
    let allVehicles = [];

    // 检查URL参数，加载历史记录
    checkUrlParams();

    // ---------------------- 检查URL参数 ----------------------
    function checkUrlParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const recordId = urlParams.get('id');
        if (recordId) {
            console.log('加载历史记录:', recordId);
            loadHistoryRecord(recordId);
        }
    }

    // ---------------------- 加载历史记录详情 ----------------------
    async function loadHistoryRecord(recordId) {
        statusBar.textContent = '加载历史记录中...';
        const cardContainer = document.getElementById('vehicle-cards-container');
        cardContainer.innerHTML = '<div class="loading">加载历史记录中...</div>';

        try {
            console.log('请求历史记录详情:', recordId);
            // 获取token并添加到请求头
            const token = localStorage.getItem('car_recognition_token');
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            
            const response = await fetch(`/api/history/${recordId}`, {
                headers: headers
            });
            const data = await response.json();
            console.log('历史记录响应:', data);

            if (data.status === 'success') {
                const record = data.data.record;
                const purchaseAdvice = data.data.purchase_advice;
                currentFilename = record.image_filename;
                
                // 显示图片
                previewImage.src = `/api/uploads/${record.image_filename}`;
                previewImage.style.display = 'block';
                imagePlaceholder.style.display = 'none';
                zoomFactor = 1.0;
                updateImageZoom();

                // 构建车辆数据
                const vehicle = {
                    basic: {
                        brand: record.brand,
                        model: record.model,
                        color: record.color,
                        confidence: parseFloat(record.confidence)
                    },
                    purchase_advice: purchaseAdvice,
                    bbox: record.bbox ? JSON.parse(record.bbox) : {}
                };

                // 渲染车辆信息
                renderVehicles([vehicle]);
                statusBar.textContent = '历史记录加载完成';
            } else {
                cardContainer.innerHTML = `<div class="error">加载失败：${data.message}</div>`;
                statusBar.textContent = `加载失败：${data.message}`;
            }
        } catch (error) {
            console.error('加载历史记录失败:', error);
            cardContainer.innerHTML = `<div class="error">加载失败：${error.message}</div>`;
            statusBar.textContent = `加载失败：${error.message}`;
        }
    }

    // ---------------------- 本地上传图片 ----------------------
    fileUpload.addEventListener('change', async (e) => {
        console.log('文件选择变化');
        const file = e.target.files[0];
        if (!file) return;

        // 前端验证文件大小
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            statusBar.textContent = `文件过大，最大支持${maxSize/(1024*1024)}MB`;
            return;
        }

        // 本地预览
        const reader = new FileReader();
        reader.onload = (event) => {
            console.log('本地预览加载完成');
            // 清除之前的识别框
            clearBoundingBoxes();
            previewImage.src = event.target.result;
            previewImage.style.display = 'block';
            imagePlaceholder.style.display = 'none';
            zoomFactor = 1.0;
            updateImageZoom();
        };
        reader.readAsDataURL(file);

        // 上传到服务器
        const formData = new FormData();
        formData.append('file', file);

        statusBar.textContent = '上传中...';

        try {
            console.log('开始上传到服务器...');
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            console.log('上传响应状态:', response.status);
            const data = await response.json();
            console.log('上传响应数据:', data);

            if (data.status === 'success') {
                currentFilename = data.data.filename;
                statusBar.textContent = `已上传图片: ${data.data.filename}`;

                // 更新为服务器上的图片
                previewImage.src = `/api/uploads/${data.data.filename}`;
            } else {
                statusBar.textContent = `上传失败: ${data.message}`;
                console.error('上传失败:', data.message);
            }
        } catch (error) {
            console.error('上传出错:', error);
            statusBar.textContent = `上传出错: ${error.message}`;
        }
    });

    // 进度条相关元素
    const progressSection = document.getElementById('recognition-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressPercentage = document.getElementById('progress-percentage');
    const cancelBtn = document.getElementById('cancel-recognition');

    // ---------------------- 开始识别（异步） ----------------------
    startRecognize.addEventListener('click', async () => {
        console.log('开始识别按钮点击');
        if (!currentFilename) {
            statusBar.textContent = '请先上传图片';
            return;
        }

        // 显示进度区域
        progressSection.style.display = 'block';
        progressBar.style.width = '0%';
        progressStatus.textContent = '提交任务...';
        progressPercentage.textContent = '0%';
        cancelBtn.style.display = 'inline-block';
        
        // 清空之前的结果
        const cardContainer = document.getElementById('vehicle-cards-container');
        cardContainer.innerHTML = '';
        const indicatorsContainer = document.getElementById('vehicle-indicators');
        indicatorsContainer.innerHTML = '';
        clearBoundingBoxes();

        statusBar.textContent = '正在提交识别任务...';

        try {
            // 提交异步任务
            const submitResult = await asyncRecognition.submitTask(currentFilename);
            
            if (!submitResult.success) {
                statusBar.textContent = `提交失败：${submitResult.message}`;
                progressStatus.textContent = '提交失败';
                cancelBtn.style.display = 'none';
                return;
            }

            const taskId = submitResult.taskId;
            statusBar.textContent = `任务已提交：${taskId}`;
            console.log('异步任务已提交:', taskId);

            // 开始轮询进度
            asyncRecognition.startPolling(
                taskId,
                // 进度回调
                (progress) => {
                    const percent = progress.progress;
                    progressBar.style.width = `${percent}%`;
                    progressPercentage.textContent = `${percent}%`;
                    
                    // 根据状态显示不同文字
                    let statusText = asyncRecognition.getStatusText(progress.state, progress.message);
                    progressStatus.textContent = statusText;
                    
                    // 更新状态栏
                    statusBar.textContent = `识别中：${statusText}`;
                    
                    // 设置进度条颜色
                    progressBar.setAttribute('data-state', progress.state);
                },
                // 完成回调
                (result) => {
                    // 隐藏进度区域
                    progressSection.style.display = 'none';
                    cancelBtn.style.display = 'none';
                    
                    // 显示结果
                    if (result.vehicles && result.vehicles.length > 0) {
                        renderVehicles(result.vehicles);
                        statusBar.textContent = `识别完成，共${result.count}辆车`;
                    } else {
                        cardContainer.innerHTML = '<div class="empty-state">未识别到车辆</div>';
                        statusBar.textContent = '未识别到车辆';
                    }
                },
                // 错误回调
                (error) => {
                    progressSection.style.display = 'none';
                    cancelBtn.style.display = 'none';
                    cardContainer.innerHTML = `<div class="error">识别失败：${error}</div>`;
                    statusBar.textContent = `识别失败：${error}`;
                }
            );

        } catch (error) {
            console.error("提交任务错误：", error);
            progressSection.style.display = 'none';
            cancelBtn.style.display = 'none';
            cardContainer.innerHTML = `<div class="error">提交失败：${error.message}</div>`;
            statusBar.textContent = `提交失败：${error.message}`;
        }
    });

    // 取消识别
    cancelBtn.addEventListener('click', async () => {
        if (asyncRecognition.isRecognizing) {
            await asyncRecognition.cancel();
            progressSection.style.display = 'none';
            cancelBtn.style.display = 'none';
            statusBar.textContent = '识别已取消';
            
            const cardContainer = document.getElementById('vehicle-cards-container');
            cardContainer.innerHTML = '<div class="empty-state">识别已取消</div>';
        }
    });

    // ---------------------- 清除所有内容 ----------------------
    clearAll.addEventListener('click', () => {
        console.log('清除按钮点击');
        previewImage.src = '';
        previewImage.style.display = 'none';
        imagePlaceholder.style.display = 'block';

        const cardContainer = document.getElementById('vehicle-cards-container');
        cardContainer.innerHTML = '<div class="empty-state">请点击"开始识别"获取结果</div>';

        const indicatorsContainer = document.getElementById('vehicle-indicators');
        indicatorsContainer.innerHTML = '';

        clearBoundingBoxes();

        currentFilename = null;
        zoomFactor = 1.0;
        updateImageZoom();
        statusBar.textContent = '就绪';
        fileUpload.value = '';
    });

    // ---------------------- 图片缩放 ----------------------
    zoomIn.addEventListener('click', () => {
        zoomFactor *= 1.1;
        updateImageZoom();
    });

    zoomOut.addEventListener('click', () => {
        zoomFactor *= 0.9;
        updateImageZoom();
    });

    zoomReset.addEventListener('click', () => {
        zoomFactor = 1.0;
        updateImageZoom();
    });

    function updateImageZoom() {
        if (previewImage.style.display === 'block') {
            previewImage.style.transform = `scale(${zoomFactor})`;
        }
    }

    // ---------------------- 渲染车辆 ----------------------
    function renderVehicles(vehicles) {
        console.log("渲染车辆数据:", vehicles);

        if (!vehicles || !Array.isArray(vehicles) || vehicles.length === 0) {
            const container = document.getElementById('vehicle-cards-container');
            container.innerHTML = '<div class="empty-state">未识别到有效车辆数据</div>';
            return;
        }

        allVehicles = vehicles;
        currentVehicleIndex = 0;

        const container = document.getElementById('vehicle-cards-container');
        const indicatorsContainer = document.getElementById('vehicle-indicators');
        container.innerHTML = '';
        indicatorsContainer.innerHTML = '';

        clearBoundingBoxes();

        vehicles.forEach((vehicle, index) => {
            // 支持两种数据结构：vehicle.brand 或 vehicle.basic.brand
            const basic = {
                brand: vehicle.brand || (vehicle.basic && vehicle.basic.brand) || '未知',
                model: vehicle.model || (vehicle.basic && vehicle.basic.model) || '未知',
                confidence: vehicle.confidence || (vehicle.basic && vehicle.basic.confidence) || 0,
                color: vehicle.color || (vehicle.basic && vehicle.basic.color) || '未知'
            };
            const purchaseAdvice = vehicle.purchase_advice || vehicle.purchaseAdvice || {};
            const bbox = vehicle.bbox || {};

            // 创建车辆卡片
            const card = document.createElement('div');
            card.className = `vehicle-card ${index === 0 ? 'active' : ''}`;
            card.innerHTML = `
                <div class="vehicle-header">
                    <span class="vehicle-number">车辆 ${index + 1}</span>
                    <h3>${basic.brand} ${basic.model}</h3>
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${(parseFloat(basic.confidence) || 0) * 100}%"></div>
                </div>
                <div class="confidence-text">置信度: ${(parseFloat(basic.confidence) || 0).toFixed(2)}</div>
                <div class="confidence-text">颜色: ${basic.color}</div>

                <div class="purchase-advice-section">
                    <h4>购买建议</h4>
                    <div class="advice-content">
                        <div class="advice-item">指导价：${purchaseAdvice.price || '暂无'}</div>
                        <div class="advice-item">用户体验：${purchaseAdvice.experience || '暂无'}</div>
                        <div class="advice-item">优缺点：${purchaseAdvice.pros_cons || '暂无'}</div>
                        <div class="advice-item">购买指数：${purchaseAdvice.rating || '★☆☆☆☆'}</div>
                        ${purchaseAdvice.official_url ? `
                            <div class="advice-item" style="grid-column: 1 / -1;">
                                官网链接：<a href="${purchaseAdvice.official_url}" target="_blank" class="official-link">${purchaseAdvice.official_url}</a>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            container.appendChild(card);

            // 创建指示器圆点
            const dot = document.createElement('div');
            dot.className = `indicator-dot ${index === 0 ? 'active' : ''}`;
            dot.addEventListener('click', () => switchToVehicle(index));
            indicatorsContainer.appendChild(dot);

            // 创建位置框
            createBoundingBox(bbox, index + 1);
        });

        // 绑定交互事件
        bindVehicleCardEvents(vehicles.length);
        document.getElementById('nav-prev').onclick = showPrevVehicle;
        document.getElementById('nav-next').onclick = showNextVehicle;

        console.log('车辆渲染完成');
    }

    // ---------------------- 车辆切换函数 ----------------------
    function switchToVehicle(index) {
        const cards = document.querySelectorAll('.vehicle-card');
        const dots = document.querySelectorAll('.indicator-dot');

        if (index < 0 || index >= cards.length) return;

        cards.forEach(card => card.classList.remove('active'));
        dots.forEach(dot => dot.classList.remove('active'));

        cards[index].classList.add('active');
        dots[index].classList.add('active');

        currentVehicleIndex = index;
    }

    function showPrevVehicle() {
        if (allVehicles.length === 0) return;
        currentVehicleIndex = (currentVehicleIndex - 1 + allVehicles.length) % allVehicles.length;
        switchToVehicle(currentVehicleIndex);
    }

    function showNextVehicle() {
        if (allVehicles.length === 0) return;
        currentVehicleIndex = (currentVehicleIndex + 1) % allVehicles.length;
        switchToVehicle(currentVehicleIndex);
    }

    // ---------------------- 位置框相关函数 ----------------------
    function createBoundingBox(bbox, vehicleNumber) {
        const container = document.getElementById('detection-overlay');
        const bboxElement = document.createElement('div');
        bboxElement.className = 'vehicle-bbox';
        bboxElement.dataset.vehicleNumber = vehicleNumber;

        if (bbox && bbox.x1 && bbox.y1 && bbox.x2 && bbox.y2) {
            bboxElement.style.left = `${parseFloat(bbox.x1) * 100}%`;
            bboxElement.style.top = `${parseFloat(bbox.y1) * 100}%`;
            bboxElement.style.width = `${(parseFloat(bbox.x2) - parseFloat(bbox.x1)) * 100}%`;
            bboxElement.style.height = `${(parseFloat(bbox.y2) - parseFloat(bbox.y1)) * 100}%`;

            const label = document.createElement('div');
            label.className = 'bbox-label';
            label.textContent = `车辆 ${vehicleNumber}`;
            bboxElement.appendChild(label);

            container.appendChild(bboxElement);
        }
    }

    function clearBoundingBoxes() {
        const existingBoxes = document.querySelectorAll('.vehicle-bbox');
        existingBoxes.forEach(box => box.remove());
    }

    function bindVehicleCardEvents(vehicleCount) {
        const cards = document.querySelectorAll('.vehicle-card');
        const boxes = document.querySelectorAll('.vehicle-bbox');

        cards.forEach((card, index) => {
            card.addEventListener('mouseenter', () => {
                if (boxes[index]) {
                    boxes[index].classList.add('highlight');
                }
            });

            card.addEventListener('mouseleave', () => {
                if (boxes[index]) {
                    boxes[index].classList.remove('highlight');
                }
            });
        });
    }

    // 初始状态
    console.log('脚本初始化完成');
});
