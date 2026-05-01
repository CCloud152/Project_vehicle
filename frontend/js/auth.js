/**
 * 用户认证模块
 * 处理登录、注册、Token管理等
 */

class AuthManager {
    constructor() {
        this.tokenKey = 'car_recognition_token';
        this.userKey = 'car_recognition_user';
        this.apiBaseUrl = '/api';
    }

    /**
     * 获取存储的Token
     */
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    /**
     * 获取存储的用户信息
     */
    getUser() {
        const userStr = localStorage.getItem(this.userKey);
        return userStr ? JSON.parse(userStr) : null;
    }

    /**
     * 检查是否已登录
     */
    isLoggedIn() {
        return !!this.getToken();
    }

    /**
     * 保存登录信息
     */
    saveAuth(tokenData, userData) {
        localStorage.setItem(this.tokenKey, tokenData.access_token);
        localStorage.setItem(this.userKey, JSON.stringify(userData));
    }

    /**
     * 清除登录信息
     */
    clearAuth() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
    }

    /**
     * 获取请求头（包含认证信息）
     */
    getAuthHeaders() {
        const token = this.getToken();
        return token ? {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        } : {
            'Content-Type': 'application/json'
        };
    }

    /**
     * 用户注册
     */
    async register(username, password, email = '') {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    password,
                    email: email || undefined
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                // 自动登录
                this.saveAuth(data.data.token, data.data.user);
                return { success: true, data: data.data };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('注册失败:', error);
            return { success: false, message: '网络错误，请稍后重试' };
        }
    }

    /**
     * 用户登录
     */
    async login(username, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    password
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.saveAuth(data.data.token, data.data.user);
                return { success: true, data: data.data };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('登录失败:', error);
            return { success: false, message: '网络错误，请稍后重试' };
        }
    }

    /**
     * 用户登出
     */
    async logout() {
        try {
            const token = this.getToken();
            if (token) {
                // 通知服务器登出
                await fetch(`${this.apiBaseUrl}/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            }
        } catch (error) {
            console.error('登出请求失败:', error);
        } finally {
            // 清除本地存储
            this.clearAuth();
            // 跳转到首页
            window.location.href = '/';
        }
    }

    /**
     * 获取用户信息
     */
    async getProfile() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/profile`, {
                method: 'GET',
                headers: this.getAuthHeaders()
            });

            const data = await response.json();

            if (data.status === 'success') {
                // 更新本地存储的用户信息
                localStorage.setItem(this.userKey, JSON.stringify(data.data.user));
                return { success: true, data: data.data };
            } else {
                // Token可能过期，清除登录状态
                if (response.status === 401) {
                    this.clearAuth();
                }
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('获取用户信息失败:', error);
            return { success: false, message: '网络错误' };
        }
    }

    /**
     * 更新用户信息
     */
    async updateProfile(userData) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/profile`, {
                method: 'PUT',
                headers: this.getAuthHeaders(),
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (data.status === 'success') {
                // 刷新用户信息
                await this.getProfile();
                return { success: true, message: data.message };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('更新用户信息失败:', error);
            return { success: false, message: '网络错误' };
        }
    }

    /**
     * 修改密码
     */
    async changePassword(oldPassword, newPassword) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/change-password`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({
                    old_password: oldPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                return { success: true, message: data.message };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('修改密码失败:', error);
            return { success: false, message: '网络错误' };
        }
    }

    /**
     * 刷新Token
     */
    async refreshToken() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/refresh`, {
                method: 'POST',
                headers: this.getAuthHeaders()
            });

            const data = await response.json();

            if (data.status === 'success') {
                // 更新Token
                const user = this.getUser();
                this.saveAuth(data.data.token, user);
                return { success: true };
            } else {
                // 刷新失败，清除登录状态
                this.clearAuth();
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('刷新Token失败:', error);
            return { success: false, message: '网络错误' };
        }
    }

    /**
     * 初始化页面（检查登录状态并更新UI）
     */
    async initPage() {
        const user = this.getUser();
        const token = this.getToken();

        if (user && token) {
            // 更新UI显示登录状态
            this.updateAuthUI(user);
            
            // 验证Token是否有效
            const result = await this.getProfile();
            if (!result.success) {
                this.updateAuthUI(null);
            }
        } else {
            this.updateAuthUI(null);
        }
    }

    /**
     * 更新页面上的认证相关UI
     */
    updateAuthUI(user) {
        // 查找所有需要显示用户名的元素
        const usernameElements = document.querySelectorAll('.username-display');
        usernameElements.forEach(el => {
            el.textContent = user ? user.username : '未登录';
        });

        // 查找登录/登出按钮
        const loginBtn = document.getElementById('login-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const userInfo = document.getElementById('user-info');

        if (user) {
            // 已登录状态
            if (loginBtn) loginBtn.style.display = 'none';
            if (logoutBtn) logoutBtn.style.display = 'inline-block';
            if (userInfo) {
                userInfo.style.display = 'inline-block';
                userInfo.textContent = user.username;
            }
        } else {
            // 未登录状态
            if (loginBtn) loginBtn.style.display = 'inline-block';
            if (logoutBtn) logoutBtn.style.display = 'none';
            if (userInfo) {
                userInfo.style.display = 'none';
            }
        }
    }

    /**
     * 需要登录才能访问
     */
    requireAuth() {
        if (!this.isLoggedIn()) {
            // 保存当前URL，登录后返回
            sessionStorage.setItem('redirect_after_login', window.location.href);
            window.location.href = '/login.html';
            return false;
        }
        return true;
    }

    /**
     * 检查登录后是否需要跳转
     */
    checkRedirectAfterLogin() {
        const redirectUrl = sessionStorage.getItem('redirect_after_login');
        if (redirectUrl) {
            sessionStorage.removeItem('redirect_after_login');
            window.location.href = redirectUrl;
            return true;
        }
        return false;
    }
}

// 创建全局实例
const auth = new AuthManager();

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    auth.initPage();
});