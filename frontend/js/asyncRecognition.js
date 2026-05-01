/**
 * 异步识别模块
 * 处理异步任务提交、进度查询、结果展示
 */

class AsyncRecognition {
    constructor() {
        this.currentTaskId = null;
        this.pollingInterval = null;
        this.isRecognizing = false;
        this.apiBaseUrl = '/api';
    }

    /**
     * 提交异步识别任务
     */
    async submitTask(filename) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/async/recognize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders()
                },
                body: JSON.stringify({ filename })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.currentTaskId = data.data.task_id;
                return {
                    success: true,
                    taskId: data.data.task_id,
                    message: data.data.message
                };
            } else {
                return {
                    success: false,
                    message: data.message
                };
            }
        } catch (error) {
            console.error('提交任务失败:', error);
            return {
                success: false,
                message: '网络错误，请稍后重试'
            };
        }
    }

    /**
     * 查询任务状态
     */
    async queryTaskStatus(taskId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/async/tasks/${taskId}`, {
                method: 'GET',
                headers: this.getAuthHeaders()
            });

            const data = await response.json();

            if (data.status === 'success') {
                return {
                    success: true,
                    state: data.data.state,
                    progress: data.data.progress || 0,
                    message: data.data.message || '',
                    result: data.data.result,
                    error: data.data.error
                };
            } else {
                return {
                    success: false,
                    message: data.message
                };
            }
        } catch (error) {
            console.error('查询任务状态失败:', error);
            return {
                success: false,
                message: '查询失败'
            };
        }
    }

    /**
     * 取消任务
     */
    async cancelTask(taskId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/async/tasks/${taskId}/cancel`, {
                method: 'POST',
                headers: this.getAuthHeaders()
            });

            const data = await response.json();

            if (data.status === 'success') {
                return { success: true, message: '任务已取消' };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('取消任务失败:', error);
            return { success: false, message: '取消失败' };
        }
    }

    /**
     * 开始轮询任务进度
     */
    startPolling(taskId, onProgress, onComplete, onError) {
        this.stopPolling(); // 先停止之前的轮询
        
        this.isRecognizing = true;
        let pollCount = 0;
        const maxPolls = 120; // 最多轮询120次（2分钟）

        this.pollingInterval = setInterval(async () => {
            pollCount++;
            
            if (pollCount > maxPolls) {
                this.stopPolling();
                onError && onError('识别超时，请稍后查询结果');
                return;
            }

            const status = await this.queryTaskStatus(taskId);

            if (!status.success) {
                // 查询失败，继续尝试
                console.warn('查询失败，继续轮询:', status.message);
                return;
            }

            // 更新进度
            onProgress && onProgress({
                state: status.state,
                progress: status.progress,
                message: status.message
            });

            // 检查任务状态
            if (status.state === 'SUCCESS') {
                this.stopPolling();
                this.isRecognizing = false;
                
                if (status.result && status.result.success) {
                    onComplete && onComplete(status.result);
                } else {
                    onError && onError(status.result?.message || '识别失败');
                }
            } else if (status.state === 'FAILURE') {
                this.stopPolling();
                this.isRecognizing = false;
                onError && onError(status.error || '任务执行失败');
            }
            // PENDING 或 STARTED 状态继续轮询

        }, 1000); // 每秒查询一次
    }

    /**
     * 停止轮询
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        this.isRecognizing = false;
    }

    /**
     * 取消当前识别
     */
    async cancel() {
        if (this.currentTaskId && this.isRecognizing) {
            await this.cancelTask(this.currentTaskId);
            this.stopPolling();
            this.currentTaskId = null;
        }
    }

    /**
     * 获取认证头
     */
    getAuthHeaders() {
        const token = localStorage.getItem('car_recognition_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    /**
     * 获取状态文字
     */
    getStatusText(state, message) {
        const statusMap = {
            'PENDING': '排队中...',
            'STARTED': message || '识别中...',
            'SUCCESS': '识别完成',
            'FAILURE': '识别失败',
            'REVOKED': '已取消'
        };
        return statusMap[state] || message || '处理中...';
    }
}

// 创建全局实例
const asyncRecognition = new AsyncRecognition();