// Main JavaScript file for Task Management System

// Constants
const API_BASE_URL = 'http://localhost:8000/api';

// Get stored user data
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function getAuthToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function setAuthData(accessToken, refreshToken, user) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('user', JSON.stringify(user));
}

function clearAuthData() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
}

function isAuthenticated() {
    return !!getAuthToken();
}

// Redirect if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        // Clear any existing auth data
        clearAuthData();
        
        // Add cache-busting parameter
        const loginUrl = '/login?t=' + new Date().getTime();
        
        // Use replace to prevent back button from going back to protected page
        window.location.replace(loginUrl);
        return false;
    }
    
    // Add cache control headers for protected pages
    if (window.performance) {
        if (performance.navigation.type === 2) {
            // Page was reached via back/forward button - force reload
            window.location.reload(true);
        }
    }
    
    return true;
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'No date set';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return 'Invalid date';
        }
        
        // Format with both date and time
        return date.toLocaleString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (error) {
        console.error('Date formatting error:', error);
        return 'Invalid date';
    }
}

// Format date for datetime-local input
function formatDateForInput(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return '';
        }
        
        // Get local timezone offset and adjust
        const localDate = new Date(date.getTime() - (date.getTimezoneOffset() * 60000));
        return localDate.toISOString().slice(0, 16);
    } catch (error) {
        console.error('Date input formatting error:', error);
        return '';
    }
}

// Format date for display with relative time
function formatDateWithRelative(dateString) {
    if (!dateString) return 'No date set';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = date.getTime() - now.getTime();
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
        
        let relativeText = '';
        if (diffDays === 0) {
            relativeText = ' (Today)';
        } else if (diffDays === 1) {
            relativeText = ' (Tomorrow)';
        } else if (diffDays === -1) {
            relativeText = ' (Yesterday)';
        } else if (diffDays > 1) {
            relativeText = ` (In ${diffDays} days)`;
        } else if (diffDays < -1) {
            relativeText = ` (${Math.abs(diffDays)} days ago)`;
        }
        
        return formatDate(dateString) + relativeText;
    } catch (error) {
        return formatDate(dateString);
    }
}

// Calculate duration between two dates
function calculateDuration(startDateString, endDateString) {
    if (!startDateString || !endDateString) return 'Unknown';
    
    try {
        const startDate = new Date(startDateString);
        const endDate = new Date(endDateString);
        
        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
            return 'Invalid dates';
        }
        
        const diffMs = endDate.getTime() - startDate.getTime();
        
        if (diffMs < 0) {
            return 'Invalid duration';
        }
        
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays > 0) {
            const remainingHours = diffHours % 24;
            if (remainingHours > 0) {
                return `${diffDays} day${diffDays > 1 ? 's' : ''}, ${remainingHours} hour${remainingHours > 1 ? 's' : ''}`;
            }
            return `${diffDays} day${diffDays > 1 ? 's' : ''}`;
        } else if (diffHours > 0) {
            const remainingMinutes = diffMinutes % 60;
            if (remainingMinutes > 0) {
                return `${diffHours} hour${diffHours > 1 ? 's' : ''}, ${remainingMinutes} minute${remainingMinutes > 1 ? 's' : ''}`;
            }
            return `${diffHours} hour${diffHours > 1 ? 's' : ''}`;
        } else if (diffMinutes > 0) {
            return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''}`;
        } else {
            return 'Less than a minute';
        }
    } catch (error) {
        console.error('Duration calculation error:', error);
        return 'Unknown';
    }
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
        
        // Handle 401 - try to refresh token
        if (response.status === 401) {
            try {
                await refreshAccessToken();
                // Retry request with new token
                headers['Authorization'] = `Bearer ${getAuthToken()}`;
                const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
                    ...options,
                    headers
                });
                
                if (!retryResponse.ok) {
                    const error = await retryResponse.json();
                    throw new Error(error.detail || 'An error occurred');
                }
                
                return await retryResponse.json();
            } catch (refreshError) {
                clearAuthData();
                window.location.href = '/login';
                throw refreshError;
            }
        }
        
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

// Token refresh function
async function refreshAccessToken() {
    try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }
        
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (!response.ok) {
            throw new Error('Failed to refresh token');
        }
        
        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        
        return data.access_token;
    } catch (error) {
        console.error('Token refresh error:', error);
        clearAuthData();
        window.location.href = '/login';
        throw error;
    }
}

// Auth Functions
async function register(userData, otp = null) {
    try {
        const payload = otp ? { user_data: userData, otp } : { user_data: userData };
        
        const response = await fetch(`${API_BASE_URL}/auth/register-with-otp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // Handle validation errors with detailed messages
            let errorMessage = 'Registration failed';
            if (data.detail) {
                if (typeof data.detail === 'string') {
                    errorMessage = data.detail;
                } else if (data.detail.errors && Array.isArray(data.detail.errors)) {
                    errorMessage = data.detail.errors.join('. ');
                } else if (data.detail.message) {
                    errorMessage = data.detail.message;
                }
            }
            throw new Error(errorMessage);
        }
        
        return data;
    } catch (error) {
        console.error('Registration error:', error);
        throw error;
    }
}

let otpEmail = '';
let otpResendTimeout = null;

// Function to show OTP section and start resend timer
function showOtpSection(email) {
    otpEmail = email;
    document.getElementById('otpSection').classList.remove('d-none');
    document.getElementById('submitBtn').innerHTML = '<i class="bi bi-check-circle"></i> Verify & Create Account';
    document.getElementById('backToFormBtn').classList.remove('d-none');
    startResendTimer();
}

// Function to go back to the form
function backToForm() {
    document.getElementById('otpSection').classList.add('d-none');
    document.getElementById('submitBtn').innerHTML = '<i class="bi bi-person-plus"></i> Create Account';
    document.getElementById('backToFormBtn').classList.add('d-none');
    document.getElementById('otp').value = '';
    document.getElementById('otpFeedback').textContent = '';
    document.getElementById('otpFeedback').className = 'form-text';
    
    // Clear any existing timer
    if (otpResendTimeout) {
        clearTimeout(otpResendTimeout);
        otpResendTimeout = null;
    }
    document.getElementById('resendOtpBtn').disabled = false;
    document.getElementById('resendTimer').textContent = '';
}

// Function to start the OTP resend timer
function startResendTimer(duration = 30) {
    const resendBtn = document.getElementById('resendOtpBtn');
    const timerElement = document.getElementById('resendTimer');
    
    resendBtn.disabled = true;
    let timeLeft = duration;
    
    const updateTimer = () => {
        if (timeLeft <= 0) {
            resendBtn.disabled = false;
            timerElement.textContent = '';
            clearTimeout(otpResendTimeout);
            otpResendTimeout = null;
            return;
        }
        
        timerElement.textContent = `(${timeLeft}s)`;
        timeLeft--;
        otpResendTimeout = setTimeout(updateTimer, 1000);
    };
    
    updateTimer();
}

// Function to resend OTP
async function resendOtp() {
    const email = document.getElementById('email').value.trim();
    if (!email) {
        showError('Please enter your email address first');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/send-otp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to send OTP');
        }
        
        showToast('OTP has been resent to your email', 'success');
        startResendTimer();
    } catch (error) {
        showError(error.message || 'Failed to resend OTP. Please try again.');
    }
}

// Function to verify OTP
async function verifyOtp(email, otp) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/verify-otp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `email=${encodeURIComponent(email)}&otp=${encodeURIComponent(otp)}`
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'OTP verification failed');
        }
        
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Function to send OTP for registration
async function sendOtpForRegistration(email) {
    try {
        console.log('Sending OTP request for email:', email);
        const requestBody = `email=${encodeURIComponent(email)}`;
        console.log('Request body:', requestBody);
        
        const response = await fetch(`${API_BASE_URL}/auth/send-otp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: requestBody
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to send OTP');
        }
        
        return { success: true };
    } catch (error) {
        console.error('Send OTP error:', error);
        return { success: false, error: error.message };
    }
}

// Function to check if email exists
async function checkEmailExists(email) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/check-email?email=${encodeURIComponent(email)}`);
        const data = await response.json();
        return data.exists;
    } catch (error) {
        console.error('Error checking email:', error);
        return false;
    }
}


async function login(email, password) {
    const response = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    
    // Store both access and refresh tokens
    setAuthData(response.access_token, response.refresh_token, response.user);
    return response;
}

async function logout() {
    try {
        // Clear local storage
        clearAuthData();
        
        // Clear session storage
        sessionStorage.clear();
        
        // Clear any cookies
        document.cookie.split(";").forEach(function(c) {
            document.cookie = c.trim().split("=")[0] + '=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/';
        });
        
        // Clear browser cache
        if ('caches' in window) {
            caches.keys().then(function(names) {
                for (let name of names) {
                    caches.delete(name);
                }
            });
        }
        
        // Force a hard redirect to login page with cache-busting
        const loginUrl = '/login';
        window.location.replace(loginUrl);
        
        // Force a reload to ensure no cached content is shown
        window.location.reload(true);
        
    } catch (error) {
        console.error('Error during logout:', error);
        window.location.href = '/login';
    }
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

// Profile Picture Functions
async function uploadProfilePicture(userId, file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const token = getAuthToken();
    const headers = {};
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/upload-profile-picture`, {
            method: 'POST',
            headers: headers,
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload profile picture');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Profile picture upload error:', error);
        throw error;
    }
}


async function getProfilePicture(userId) {
    return await apiRequest(`/users/${userId}/profile-picture`);
}

// Password change function
async function changePassword(userId, currentPassword, newPassword) {
    return await apiRequest(`/users/${userId}/change-password`, {
        method: 'POST',
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword
        })
    });
}

// Task statistics function
async function getTaskStatistics(userId) {
    return await apiRequest(`/tasks/${userId}/statistics`);
}

// Settings functions
async function getUserSettings(userId) {
    return await apiRequest(`/users/${userId}/settings`);
}

async function updateUserSettings(userId, settings) {
    return await apiRequest(`/users/${userId}/settings`, {
        method: 'PUT',
        body: JSON.stringify(settings)
    });
}

// Task Card HTML
function createTaskCard(task) {
    const priorityClass = `priority-${task.priority}`;
    const priorityBadge = `badge-${task.priority}`;
    
    return `
        <div class="card task-card ${priorityClass}" 
             draggable="true" 
             data-task-id="${task.id}" 
             data-task-status="${task.status}"
             onmousedown="console.log('Mouse down on task card')"
             ondragstart="console.log('Inline dragstart on task card')">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="d-flex align-items-start gap-2 flex-grow-1">
                        <div class="drag-handle" title="Drag to move task">
                            <i class="bi bi-grip-vertical text-muted"></i>
                        </div>
                        <h5 class="card-title mb-0 flex-grow-1">${task.title}</h5>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge badge-priority ${priorityBadge}">${task.priority.toUpperCase()}</span>
                        <div class="task-actions">
                            <button class="btn btn-sm btn-outline-danger task-delete-btn" 
                                    data-task-id="${task.id}" 
                                    title="Delete Task"
                                    onclick="event.stopPropagation(); deleteTaskConfirm('${task.id}', '${task.title.replace(/'/g, "\\'")}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <p class="card-text text-muted small">${task.description.substring(0, 100)}${task.description.length > 100 ? '...' : ''}</p>
                ${task.tags && task.tags.length > 0 ? `
                    <div class="task-tags">
                        ${task.tags.map(tag => `<span class="task-tag">${tag}</span>`).join('')}
                    </div>
                ` : ''}
                ${task.due_date ? `
                    <div class="mt-2">
                        <small class="text-muted ${new Date(task.due_date) < new Date() && task.status !== 'completed' ? 'text-danger' : ''}">
                            <i class="bi bi-calendar${new Date(task.due_date) < new Date() && task.status !== 'completed' ? '-x' : ''}"></i> 
                            Due: ${formatDateWithRelative(task.due_date)}
                            ${new Date(task.due_date) < new Date() && task.status !== 'completed' ? ' <i class="bi bi-exclamation-triangle"></i>' : ''}
                        </small>
                    </div>
                ` : ''}
                ${task.status === 'completed' && task.end_time ? `
                    <div class="mt-2">
                        <small class="text-success">
                            <i class="bi bi-check-circle"></i> Completed: ${formatDate(task.end_time)}
                            ${task.start_time ? `<br><i class="bi bi-clock"></i> Duration: ${calculateDuration(task.start_time, task.end_time)}` : ''}
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

// Task deletion with confirmation
async function deleteTaskConfirm(taskId, taskTitle) {
    // Create a custom confirmation modal or use browser confirm
    const confirmed = confirm(`Are you sure you want to delete the task "${taskTitle}"?\n\nThis action cannot be undone.`);
    
    if (confirmed) {
        try {
            // Show loading toast
            showToast('Deleting task...', 'info');
            
            // Delete the task
            await deleteTask(taskId);
            
            // Show success message
            showToast('Task deleted successfully!', 'success');
            
            // Reload tasks to reflect changes
            if (typeof loadTasks === 'function') {
                await loadTasks();
            } else {
                // If we're not on dashboard, reload the page
                window.location.reload();
            }
            
        } catch (error) {
            console.error('Error deleting task:', error);
            showToast('Failed to delete task: ' + error.message, 'danger');
        }
    }
}

// Update navbar with user info
function updateNavbar() {
    const user = getCurrentUser();
    const navbarUser = document.getElementById('navbarUser');
    
    console.log('[updateNavbar] User:', user);
    console.log('[updateNavbar] Navbar element:', navbarUser);
    
    if (!navbarUser) {
        console.warn('[updateNavbar] Navbar element not found');
        return;
    }
    
    if (user) {
        // User is logged in - show user menu
        console.log('[updateNavbar] Updating navbar for logged in user:', user.first_name);
        navbarUser.innerHTML = `
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                    ${user.first_name} ${user.last_name}
                </a>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="/profile"><i class="bi bi-person-circle me-2"></i>Profile</a></li>
                    <li><a class="dropdown-item" href="/dashboard"><i class="bi bi-speedometer2 me-2"></i>Dashboard</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="#" onclick="logout()"><i class="bi bi-box-arrow-right me-2"></i>Logout</a></li>
                </ul>
            </li>
        `;
    } else {
        // User is not logged in - show login/register buttons
        console.log('[updateNavbar] User not logged in, showing login/register buttons');
        navbarUser.innerHTML = `
            <li class="nav-item">
                <a class="nav-link" href="/login">Login</a>
            </li>
            <li class="nav-item">
                <a class="btn btn-primary ms-lg-2 mt-2 mt-lg-0" href="/register">Get Started</a>
            </li>
        `;
    }
}

// Drag and Drop Variables
let draggedTask = null;
let draggedElement = null;

// Drag and Drop Event Handlers
function handleDragStart(event) {
    console.log('Drag start event triggered on:', event.currentTarget);
    
    // Don't allow drag from interactive elements
    if (event.target.closest('.task-delete-btn') || 
        event.target.closest('.task-actions button')) {
        console.log('Preventing drag from interactive element');
        event.preventDefault();
        return false;
    }
    
    const taskCard = event.currentTarget; // Use currentTarget instead of closest
    console.log('Task card:', taskCard);
    
    draggedElement = taskCard;
    draggedTask = {
        id: taskCard.dataset.taskId,
        status: taskCard.dataset.taskStatus
    };
    
    taskCard.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', taskCard.dataset.taskId);
    
    console.log('Drag started for task:', draggedTask);
}

function handleDragEnd(event) {
    const taskCard = event.currentTarget;
    console.log('Drag end on:', taskCard);
    
    taskCard.classList.remove('dragging');
    taskCard.style.opacity = ''; // Reset opacity
    
    // Clean up drag over states
    document.querySelectorAll('.task-list').forEach(list => {
        list.classList.remove('drag-over');
    });
    
    console.log('Drag ended');
    draggedTask = null;
    draggedElement = null;
}

function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

function handleDragEnter(event) {
    event.preventDefault();
    const taskList = event.target.closest('.task-list');
    if (taskList) {
        taskList.classList.add('drag-over');
        console.log('Drag entered:', taskList.dataset.status);
    }
}

function handleDragLeave(event) {
    const taskList = event.target.closest('.task-list');
    if (taskList) {
        // Only remove drag-over if we're actually leaving the drop zone
        const rect = taskList.getBoundingClientRect();
        const x = event.clientX;
        const y = event.clientY;
        
        if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
            taskList.classList.remove('drag-over');
            console.log('Drag left:', taskList.dataset.status);
        }
    }
}

async function handleDrop(event) {
    event.preventDefault();
    
    console.log('Drop event triggered', event.target);
    
    const dropTarget = event.target.closest('.task-list');
    if (!draggedTask || !dropTarget) {
        console.log('Invalid drop - no dragged task or drop target');
        return;
    }
    
    const newStatus = dropTarget.dataset.status;
    const oldStatus = draggedTask.status;
    
    console.log('Dropping task from', oldStatus, 'to', newStatus);
    
    // Don't do anything if dropped in the same column
    if (newStatus === oldStatus) {
        dropTarget.classList.remove('drag-over');
        console.log('Same column drop - no action needed');
        return;
    }
    
    try {
        // Prepare update data
        const updateData = { status: newStatus };
        
        // Handle automatic time setting based on status change
        if (newStatus === 'completed') {
            // Set end time when completing task
            updateData.end_time = new Date().toISOString();
        } else if (newStatus === 'in_progress') {
            // Set start time when starting task (if not already set)
            // Note: We don't have the full task data here, so the backend should handle this
            updateData.start_time_if_empty = new Date().toISOString();
        }
        
        // Update task status via API
        console.log('Updating task status via API...');
        await updateTask(draggedTask.id, updateData);
        
        // Show success message with appropriate feedback
        let message = `Task moved to ${newStatus.replace('_', ' ')}!`;
        if (newStatus === 'completed') {
            message += ' End time recorded.';
        } else if (newStatus === 'in_progress') {
            message += ' Task started.';
        }
        
        showToast(message, 'success');
        
        // Reload tasks to reflect changes
        await loadTasks();
        
    } catch (error) {
        showToast('Failed to move task: ' + error.message, 'danger');
        console.error('Error moving task:', error);
    }
    
    dropTarget.classList.remove('drag-over');
}

// Track if drag and drop is already initialized
let dragDropInitialized = false;

// Initialize drag and drop on task lists
function initializeDragAndDrop() {
    console.log('Initializing drag and drop...');
    
    const taskLists = document.querySelectorAll('.task-list');
    console.log('Found task lists:', taskLists.length);
    
    // Add listeners to task lists
    taskLists.forEach(list => {
        // Remove existing listeners first
        list.removeEventListener('dragover', handleDragOver);
        list.removeEventListener('dragenter', handleDragEnter);
        list.removeEventListener('dragleave', handleDragLeave);
        list.removeEventListener('drop', handleDrop);
        
        // Add new listeners
        list.addEventListener('dragover', handleDragOver);
        list.addEventListener('dragenter', handleDragEnter);
        list.addEventListener('dragleave', handleDragLeave);
        list.addEventListener('drop', handleDrop);
        console.log('Added listeners to task list:', list.dataset.status);
    });
    
    // Add direct listeners to task cards
    const taskCards = document.querySelectorAll('.task-card');
    console.log('Found task cards:', taskCards.length);
    
    taskCards.forEach(card => {
        // Ensure draggable attribute is set
        card.setAttribute('draggable', 'true');
        
        // Remove existing listeners
        card.removeEventListener('dragstart', handleDragStart);
        card.removeEventListener('dragend', handleDragEnd);
        card.removeEventListener('click', handleTaskClick);
        
        // Add direct listeners
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
        card.addEventListener('click', handleTaskClick);
        
        console.log('Added direct listeners to card:', card.dataset.taskId);
    });
    
    console.log('Drag and drop initialization complete');
}

// Handle task card clicks
function handleTaskClick(event) {
    // Don't navigate if clicking on delete button or during drag
    if (event.target.closest('.task-delete-btn') || 
        event.currentTarget.classList.contains('dragging')) {
        return;
    }
    
    const taskId = event.currentTarget.dataset.taskId;
    if (taskId) {
        viewTask(taskId);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateNavbar();
    initializeDragAndDrop();
    
    // Load task detail page data if on task detail page
    if (window.location.pathname.includes('/task/')) {
        const taskId = window.location.pathname.split('/task/')[1];
        if (taskId) {
            loadTaskDetailData(taskId);
        }
    }
});

// Task Detail Page Functions
async function loadTaskDetailData(taskId) {
    try {
        await Promise.all([
            loadSubtasks(taskId),
            loadComments(taskId),
            loadHistory(taskId),
            loadAttachments(taskId)
        ]);
    } catch (error) {
        console.error('Error loading task detail data:', error);
    }
}

async function loadSubtasks(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/subtasks`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        
        if (response.ok) {
            const subtasks = await response.json();
            const container = document.getElementById('subtasksList');
            
            // Check if container exists (might not be on task detail page)
            if (!container) {
                console.log('Subtasks container not found - not on task detail page');
                return;
            }
            
            if (subtasks.length === 0) {
                container.innerHTML = '<p class="text-muted">No subtasks yet</p>';
            } else {
                container.innerHTML = subtasks.map(subtask => `
                    <div class="border-bottom pb-2 mb-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${subtask.title}</strong>
                                <br><small class="text-muted">${subtask.description}</small>
                                <br><span class="badge badge-${subtask.priority}">${subtask.priority}</span>
                            </div>
                            <div>
                                <span class="badge bg-${subtask.status === 'completed' ? 'success' : subtask.status === 'in_progress' ? 'warning' : 'secondary'}">${subtask.status}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Failed to load subtasks:', error);
    }
}

async function loadComments(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/comments`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        
        if (response.ok) {
            const comments = await response.json();
            const container = document.getElementById('commentsList');
            
            // Check if container exists (might not be on task detail page)
            if (!container) {
                console.log('Comments container not found - not on task detail page');
                return;
            }
            
            if (comments.length === 0) {
                container.innerHTML = '<p class="text-muted">No comments yet</p>';
            } else {
                container.innerHTML = comments.map(comment => `
                    <div class="border-bottom pb-3 mb-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <strong>${comment.author_username || 'User'}</strong>
                                <small class="text-muted ms-2">${new Date(comment.created_at).toLocaleString()}</small>
                                ${comment.edited ? '<small class="text-muted ms-1">(edited)</small>' : ''}
                                <p class="mt-2 mb-0">${comment.content}</p>
                            </div>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-secondary" onclick="editComment('${comment.id}')">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="deleteComment('${comment.id}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Failed to load comments:', error);
    }
}

async function loadHistory(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/history`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        
        if (response.ok) {
            const history = await response.json();
            const container = document.getElementById('historyTimeline');
            
            // Check if container exists (might not be on task detail page)
            if (!container) {
                console.log('History timeline container not found - not on task detail page');
                return;
            }
            
            // Check if history is actually an array
            if (!Array.isArray(history)) {
                console.error('History response is not an array:', history);
                container.innerHTML = '<p class="text-muted">Error loading activity history</p>';
                return;
            }
            
            if (history.length === 0) {
                container.innerHTML = '<p class="text-muted">No activity history</p>';
            } else {
                container.innerHTML = history.map(entry => `
                    <div class="border-bottom pb-3 mb-3">
                        <div class="d-flex align-items-start">
                            <div class="flex-shrink-0 me-3">
                                <i class="bi bi-circle-fill text-primary" style="font-size: 8px;"></i>
                            </div>
                            <div class="flex-grow-1">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <strong>${entry.field_name.replace('_', ' ').toUpperCase()}</strong>
                                        <br><small class="text-muted">${new Date(entry.created_at).toLocaleString()}</small>
                                        <br><small class="text-muted">by ${entry.changed_by_username || 'User'}</small>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    ${entry.old_value ? `<div class="text-danger"><small>From: ${entry.old_value}</small></div>` : ''}
                                    ${entry.new_value ? `<div class="text-success"><small>To: ${entry.new_value}</small></div>` : ''}
                                    ${entry.comment ? `<div class="text-muted"><small>Note: ${entry.comment}</small></div>` : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

async function loadAttachments(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/attachments`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        
        if (response.ok) {
            const attachments = await response.json();
            const container = document.getElementById('attachmentsList');
            
            // Check if container exists (might not be on task detail page)
            if (!container) {
                console.log('Attachments container not found - not on task detail page');
                return;
            }
            
            if (attachments.length === 0) {
                container.innerHTML = '<p class="text-muted">No attachments</p>';
            } else {
                container.innerHTML = attachments.map(attachment => `
                    <div class="border-bottom pb-2 mb-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="flex-grow-1">
                                <i class="bi bi-paperclip me-2"></i>
                                <strong>${attachment.filename}</strong>
                                <br><small class="text-muted">${(attachment.file_size / 1024).toFixed(1)} KB</small>
                                ${attachment.description ? `<br><small class="text-muted">${attachment.description}</small>` : ''}
                            </div>
                            <div>
                                <a href="/api/tasks/${taskId}/attachments/${attachment.id}/download" class="btn btn-sm btn-outline-primary">
                                    <i class="bi bi-download"></i>
                                </a>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteAttachment('${attachment.id}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Failed to load attachments:', error);
    }
}

async function submitComment() {
    const content = document.getElementById('commentInput').value.trim();
    if (!content) {
        showToast('Please enter a comment', 'warning');
        return;
    }
    
    const taskId = window.location.pathname.split('/task/')[1];
    if (!taskId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/comments`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        
        if (response.ok) {
            document.getElementById('commentInput').value = '';
            showToast('Comment added successfully!', 'success');
            await loadComments(taskId);
        } else {
            throw new Error('Failed to add comment');
        }
    } catch (error) {
        showToast('Failed to add comment: ' + error.message, 'danger');
    }
}

async function uploadAttachment() {
    const fileInput = document.getElementById('attachmentInput');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const taskId = window.location.pathname.split('/task/')[1];
    if (!taskId) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/attachments`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` },
            body: formData
        });
        
        if (response.ok) {
            fileInput.value = '';
            showToast('Attachment uploaded successfully!', 'success');
            await loadAttachments(taskId);
        } else {
            throw new Error('Failed to upload attachment');
        }
    } catch (error) {
        showToast('Failed to upload attachment: ' + error.message, 'danger');
    }
}

function openCreateSubtaskModal() {
    // This would open a modal to create a subtask
    // For now, we'll use a simple prompt
    const title = prompt('Enter subtask title:');
    if (!title) return;
    
    const description = prompt('Enter subtask description:') || '';
    
    createSubtask(title, description);
}

async function createSubtask(title, description) {
    const taskId = window.location.pathname.split('/task/')[1];
    if (!taskId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title,
                description,
                parent_task_id: taskId,
                priority: 'medium',
                status: 'todo'
            })
        });
        
        if (response.ok) {
            showToast('Subtask created successfully!', 'success');
            await loadSubtasks(taskId);
        } else {
            throw new Error('Failed to create subtask');
        }
    } catch (error) {
        showToast('Failed to create subtask: ' + error.message, 'danger');
    }
}

async function editComment(commentId) {
    const newContent = prompt('Edit comment:');
    if (!newContent) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/comments/${commentId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: newContent })
        });
        
        if (response.ok) {
            showToast('Comment updated successfully!', 'success');
            const taskId = window.location.pathname.split('/task/')[1];
            await loadComments(taskId);
        } else {
            throw new Error('Failed to update comment');
        }
    } catch (error) {
        showToast('Failed to update comment: ' + error.message, 'danger');
    }
}

async function deleteComment(commentId) {
    if (!confirm('Are you sure you want to delete this comment?')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/comments/${commentId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        
        if (response.ok) {
            showToast('Comment deleted successfully!', 'success');
            const taskId = window.location.pathname.split('/task/')[1];
            await loadComments(taskId);
        } else {
            throw new Error('Failed to delete comment');
        }
    } catch (error) {
        showToast('Failed to delete comment: ' + error.message, 'danger');
    }
}

async function deleteAttachment(attachmentId) {
    if (!confirm('Are you sure you want to delete this attachment?')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/attachments/${attachmentId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        
        if (response.ok) {
            showToast('Attachment deleted successfully!', 'success');
            const taskId = window.location.pathname.split('/task/')[1];
            await loadAttachments(taskId);
        } else {
            throw new Error('Failed to delete attachment');
        }
    } catch (error) {
        showToast('Failed to delete attachment: ' + error.message, 'danger');
    }
}

