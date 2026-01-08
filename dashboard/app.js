// API Base URL
const API_BASE_URL = 'http://localhost:8000';

// State Management
let currentTab = 'generate';
let generationProgress = {
    research: { status: 'pending', message: '' },
    write: { status: 'pending', message: '' },
    images: { status: 'pending', message: '' },
    seo: { status: 'pending', message: '' },
    review: { status: 'pending', message: '' }
};

// API Call Functions
async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');
        const data = await response.json();
        updateStatsDisplay(data);
    } catch (error) {
        console.error('Error fetching stats:', error);
        showNotification('統計情報の取得に失敗しました', 'error');
    }
}

async function fetchPosts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/posts`);
        if (!response.ok) throw new Error('Failed to fetch posts');
        const data = await response.json();
        updatePostsTable(data);
    } catch (error) {
        console.error('Error fetching posts:', error);
        showNotification('記事一覧の取得に失敗しました', 'error');
    }
}

async function generateResearch(topic) {
    try {
        updateStepStatus('research', 'processing', 'リサーチ中...');
        const response = await fetch(`${API_BASE_URL}/api/generate/research`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });

        if (!response.ok) throw new Error('Research generation failed');
        const data = await response.json();
        updateStepStatus('research', 'completed', 'リサーチ完了');
        return data;
    } catch (error) {
        console.error('Error in research generation:', error);
        updateStepStatus('research', 'error', 'リサーチに失敗しました');
        throw error;
    }
}

async function generateWrite(researchData) {
    try {
        updateStepStatus('write', 'processing', '執筆中...');
        const response = await fetch(`${API_BASE_URL}/api/generate/write`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ research_data: researchData })
        });

        if (!response.ok) throw new Error('Writing generation failed');
        const data = await response.json();
        updateStepStatus('write', 'completed', '執筆完了');
        return data;
    } catch (error) {
        console.error('Error in writing generation:', error);
        updateStepStatus('write', 'error', '執筆に失敗しました');
        throw error;
    }
}

async function generateImages(articleData) {
    try {
        updateStepStatus('images', 'processing', '画像生成中...');
        const response = await fetch(`${API_BASE_URL}/api/generate/images`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_data: articleData })
        });

        if (!response.ok) throw new Error('Image generation failed');
        const data = await response.json();
        updateStepStatus('images', 'completed', '画像生成完了');
        return data;
    } catch (error) {
        console.error('Error in image generation:', error);
        updateStepStatus('images', 'error', '画像生成に失敗しました');
        throw error;
    }
}

async function generateSEO(articleData) {
    try {
        updateStepStatus('seo', 'processing', 'SEO最適化中...');
        const response = await fetch(`${API_BASE_URL}/api/generate/seo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_data: articleData })
        });

        if (!response.ok) throw new Error('SEO generation failed');
        const data = await response.json();
        updateStepStatus('seo', 'completed', 'SEO最適化完了');
        return data;
    } catch (error) {
        console.error('Error in SEO generation:', error);
        updateStepStatus('seo', 'error', 'SEO最適化に失敗しました');
        throw error;
    }
}

async function generateReview(articleData) {
    try {
        updateStepStatus('review', 'processing', 'レビュー中...');
        const response = await fetch(`${API_BASE_URL}/api/generate/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_data: articleData })
        });

        if (!response.ok) throw new Error('Review generation failed');
        const data = await response.json();
        updateStepStatus('review', 'completed', 'レビュー完了');
        return data;
    } catch (error) {
        console.error('Error in review generation:', error);
        updateStepStatus('review', 'error', 'レビューに失敗しました');
        throw error;
    }
}

async function publishPost(postId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/posts/publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ post_id: postId })
        });

        if (!response.ok) throw new Error('Publishing failed');
        const data = await response.json();
        showNotification('記事を公開しました', 'success');
        await fetchPosts();
        await fetchStats();
        return data;
    } catch (error) {
        console.error('Error publishing post:', error);
        showNotification('記事の公開に失敗しました', 'error');
        throw error;
    }
}

// Tab Switching
function switchTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data for specific tabs
    if (tabName === 'posts') {
        fetchPosts();
    } else if (tabName === 'analytics') {
        initializeCharts();
    }
}

// Generation Form Processing
async function handleGenerate(event) {
    event.preventDefault();

    const form = event.target;
    const topic = form.querySelector('#topic').value;
    const targetKeywords = form.querySelector('#target-keywords').value;
    const contentType = form.querySelector('#content-type').value;

    if (!topic) {
        showNotification('トピックを入力してください', 'error');
        return;
    }

    // Reset progress
    resetProgress();

    // Show progress section
    document.getElementById('generation-progress').style.display = 'block';

    // Disable form
    form.querySelector('button[type="submit"]').disabled = true;

    try {
        // Step 1: Research
        const researchData = await generateResearch(topic);

        // Step 2: Write
        const articleData = await generateWrite(researchData);

        // Step 3: Images
        const imageData = await generateImages(articleData);

        // Step 4: SEO
        const seoData = await generateSEO({ ...articleData, ...imageData });

        // Step 5: Review
        const reviewData = await generateReview({ ...articleData, ...imageData, ...seoData });

        showNotification('記事生成が完了しました!', 'success');

        // Switch to posts tab
        setTimeout(() => {
            switchTab('posts');
        }, 1500);

    } catch (error) {
        console.error('Generation process failed:', error);
        showNotification('記事生成中にエラーが発生しました', 'error');
    } finally {
        // Re-enable form
        form.querySelector('button[type="submit"]').disabled = false;
    }
}

// Progress Display Update
function updateStepStatus(step, status, message) {
    generationProgress[step] = { status, message };

    const stepElement = document.querySelector(`[data-step="${step}"]`);
    if (!stepElement) return;

    // Remove all status classes
    stepElement.classList.remove('pending', 'processing', 'completed', 'error');

    // Add current status class
    stepElement.classList.add(status);

    // Update message
    const messageElement = stepElement.querySelector('.step-message');
    if (messageElement) {
        messageElement.textContent = message;
    }

    // Update icon
    const iconElement = stepElement.querySelector('.step-icon');
    if (iconElement) {
        switch(status) {
            case 'pending':
                iconElement.innerHTML = '<i class="fas fa-clock"></i>';
                break;
            case 'processing':
                iconElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                break;
            case 'completed':
                iconElement.innerHTML = '<i class="fas fa-check-circle"></i>';
                break;
            case 'error':
                iconElement.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
                break;
        }
    }
}

function resetProgress() {
    const steps = ['research', 'write', 'images', 'seo', 'review'];
    steps.forEach(step => {
        updateStepStatus(step, 'pending', '待機中');
    });
}

// Stats Display Update
function updateStatsDisplay(stats) {
    document.getElementById('total-posts').textContent = stats.total_posts || 0;
    document.getElementById('published-posts').textContent = stats.published_posts || 0;
    document.getElementById('draft-posts').textContent = stats.draft_posts || 0;
    document.getElementById('total-views').textContent = formatNumber(stats.total_views || 0);
}

// Posts Table Update
function updatePostsTable(posts) {
    const tbody = document.querySelector('#posts-table tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!posts || posts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">記事がありません</td></tr>';
        return;
    }

    posts.forEach(post => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(post.title || '')}</td>
            <td><span class="badge badge-${getStatusBadgeClass(post.status)}">${getStatusText(post.status)}</span></td>
            <td>${formatDate(post.created_at)}</td>
            <td>${formatDate(post.published_at)}</td>
            <td>${formatNumber(post.views || 0)}</td>
            <td>
                <div class="action-buttons">
                    ${post.status === 'draft' ? `
                        <button class="btn btn-sm btn-primary" onclick="publishPost('${post.id}')">
                            <i class="fas fa-paper-plane"></i> 公開
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-secondary" onclick="editPost('${post.id}')">
                        <i class="fas fa-edit"></i> 編集
                    </button>
                    <button class="btn btn-sm btn-info" onclick="downloadPost('${post.id}')">
                        <i class="fas fa-download"></i> DL
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Chart Initialization
let postsChart = null;
let viewsChart = null;

function initializeCharts() {
    // Posts Over Time Chart
    const postsCtx = document.getElementById('posts-chart');
    if (postsCtx) {
        if (postsChart) {
            postsChart.destroy();
        }

        postsChart = new Chart(postsCtx, {
            type: 'line',
            data: {
                labels: ['1月', '2月', '3月', '4月', '5月', '6月'],
                datasets: [{
                    label: '投稿数',
                    data: [12, 19, 15, 25, 22, 30],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Views Chart
    const viewsCtx = document.getElementById('views-chart');
    if (viewsCtx) {
        if (viewsChart) {
            viewsChart.destroy();
        }

        viewsChart = new Chart(viewsCtx, {
            type: 'bar',
            data: {
                labels: ['1月', '2月', '3月', '4月', '5月', '6月'],
                datasets: [{
                    label: '閲覧数',
                    data: [1200, 1900, 1500, 2500, 2200, 3000],
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

// Post Actions
function editPost(postId) {
    // TODO: Implement edit functionality
    showNotification('編集機能は準備中です', 'info');
}

function downloadPost(postId) {
    window.location.href = `${API_BASE_URL}/api/posts/${postId}/download`;
}

// Utility Functions
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function getStatusBadgeClass(status) {
    const classes = {
        'draft': 'warning',
        'published': 'success',
        'archived': 'secondary'
    };
    return classes[status] || 'secondary';
}

function getStatusText(status) {
    const texts = {
        'draft': '下書き',
        'published': '公開中',
        'archived': 'アーカイブ'
    };
    return texts[status] || status;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${escapeHtml(message)}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    // Add to container
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }

    container.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Set up tab listeners
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Set up generation form
    const generateForm = document.getElementById('generate-form');
    if (generateForm) {
        generateForm.addEventListener('submit', handleGenerate);
    }

    // Load initial data
    fetchStats();

    // Refresh stats every 30 seconds
    setInterval(fetchStats, 30000);
});
