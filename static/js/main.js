// Main JavaScript file for Task Management System

// Constants
const API_BASE_URL = 'http://localhost:8000/api';

// Get stored user data
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function getAuthToken() {
    return localStorage.getItem('token');
}

function setAuthData(token, user) {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
}

function clearAuthData() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

function isAuthenticated() {
    return !!getAuthToken();
}

// Redirect if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'No date set';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format date for input
function formatDateForInput(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().slice(0, 16);
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// Show loading spinner
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="spinner-container">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
}

// API Helper Functions
async function apiRequest(endpoint, options = {}) {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'An error occurred');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Auth Functions
async function register(userData) {
    return await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData)
    });
}

async function login(email, password) {
    const response = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    
    setAuthData(response.access_token, response.user);
    return response;
}

function logout() {
    clearAuthData();
    window.location.href = '/login';
}

// Task Functions
async function createTask(taskData) {
    const user = getCurrentUser();
    return await apiRequest(`/tasks?user_id=${user.id}`, {
        method: 'POST',
        body: JSON.stringify(taskData)
    });
}

async function getTasks(status = null) {
    const user = getCurrentUser();
    let endpoint = `/tasks?user_id=${user.id}`;
    if (status) {
        endpoint += `&status=${status}`;
    }
    return await apiRequest(endpoint);
}

async function getTask(taskId) {
    return await apiRequest(`/tasks/${taskId}`);
}

async function updateTask(taskId, taskData) {
    return await apiRequest(`/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify(taskData)
    });
}

async function deleteTask(taskId) {
    return await apiRequest(`/tasks/${taskId}`, {
        method: 'DELETE'
    });
}

// User Functions
async function getUser(userId) {
    return await apiRequest(`/users/${userId}`);
}

async function updateUser(userId, userData) {
    return await apiRequest(`/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(userData)
    });
}

// Task Card HTML
function createTaskCard(task) {
    const priorityClass = `priority-${task.priority}`;
    const priorityBadge = `badge-${task.priority}`;
    
    return `
        <div class="card task-card ${priorityClass}" onclick="viewTask('${task.id}')">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="card-title mb-0">${task.title}</h5>
                    <span class="badge badge-priority ${priorityBadge}">${task.priority.toUpperCase()}</span>
                </div>
                <p class="card-text text-muted small">${task.description.substring(0, 100)}${task.description.length > 100 ? '...' : ''}</p>
                ${task.tags && task.tags.length > 0 ? `
                    <div class="task-tags">
                        ${task.tags.map(tag => `<span class="task-tag">${tag}</span>`).join('')}
                    </div>
                ` : ''}
                ${task.due_date ? `
                    <div class="mt-2">
                        <small class="text-muted">
                            <i class="bi bi-calendar"></i> Due: ${formatDate(task.due_date)}
                        </small>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function viewTask(taskId) {
    window.location.href = `/task/${taskId}`;
}

// Update navbar with user info
function updateNavbar() {
    const user = getCurrentUser();
    const navbarUser = document.getElementById('navbarUser');
    
    if (user && navbarUser) {
        navbarUser.innerHTML = `
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-dropdown="dropdown">
                    ${user.first_name} ${user.last_name}
                </a>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item" href="/profile">Profile</a></li>
                    <li><a class="dropdown-item" href="/dashboard">Dashboard</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="#" onclick="logout()">Logout</a></li>
                </ul>
            </li>
        `;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateNavbar();
});

