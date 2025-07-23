// ========== GLOBAL VARIABLES ==========
let toastCount = 0;

// ========== DOCUMENT READY ==========
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    handleAuthentication();
});

function initializeApp() {
    console.log('BlogGen Pro - Initializing...');
}

function handleAuthentication() {
    const token = localStorage.getItem('access_token');
    if (token) {
        setAuthorizationHeader(token);
    }
}

function setAuthorizationHeader(token) {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        if (args[1]) {
            args[1].headers = {
                ...args[1].headers,
                'Authorization': `Bearer ${token}`
            };
        } else {
            args[1] = {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            };
        }
        return originalFetch.apply(this, args);
    };
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('access_token');
        
        fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(() => {
            window.location.href = '/';
        })
        .catch(error => {
            console.error('Logout error:', error);
            window.location.href = '/';
        });
    }
}

// ========== TOAST NOTIFICATIONS ==========
function showToast(message, type = 'info', duration = 5000) {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    const toastId = 'toast-' + Date.now();
    toast.id = toastId;
    
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-primary';
    toast.className = `toast show align-items-center text-white ${bgClass} border-0`;
    toast.setAttribute('role', 'alert');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="closeToast('${toastId}')"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        closeToast(toastId);
    }, duration);
}

function closeToast(toastId) {
    const toast = document.getElementById(toastId);
    if (toast) {
        toast.style.opacity = '0';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }
}

// ========== DASHBOARD FUNCTIONS ==========
function deletePost(postId) {
    if (confirm('Are you sure you want to delete this blog post?')) {
        const token = localStorage.getItem('access_token');
        
        fetch(`/delete-post/${postId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const postElement = document.querySelector(`[data-post-id="${postId}"]`);
                if (postElement) {
                    postElement.remove();
                }
                showToast('Blog post deleted successfully', 'success');
            } else {
                showToast('Failed to delete blog post', 'error');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            showToast('Error deleting blog post', 'error');
        });
    }
}

function viewPost(postId) {
    showToast('View post feature coming soon!', 'info');
}

function downloadPost(postId) {
    showToast('Individual post download coming soon!', 'info');
}

function refreshPosts() {
    location.reload();
}

function showComingSoon() {
    showToast('This feature is coming soon!', 'info');
}

// ========== GENERATE PAGE FUNCTIONS ==========
function copyBlogContent() {
    if (generatedBlogData && generatedBlogData.content) {
        const textContent = generatedBlogData.content;
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(textContent).then(function() {
                showToast('Blog content copied to clipboard!', 'success');
            });
        } else {
            const textArea = document.createElement('textarea');
            textArea.value = textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('Blog content copied to clipboard!', 'success');
        }
    } else {
        showToast('No content to copy', 'error');
    }
}

// ========== GLOBAL FUNCTIONS ==========
window.showToast = showToast;
window.logout = logout;
window.deletePost = deletePost;
window.viewPost = viewPost;
window.downloadPost = downloadPost;
window.refreshPosts = refreshPosts;
window.showComingSoon = showComingSoon;
window.copyBlogContent = copyBlogContent;
