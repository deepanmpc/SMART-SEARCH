const { ipcRenderer } = require('electron');

const searchInput = document.getElementById('searchInput');
const indexFolderBtn = document.getElementById('indexFolderBtn');
const clearIndexBtn = document.getElementById('clearIndexBtn');
const resultsContainer = document.getElementById('resultsContainer');
const resultsList = document.getElementById('resultsList');
const resultPreview = document.getElementById('resultPreview');
const loadingIndicator = document.getElementById('loadingIndicator');
const planText = document.getElementById('planText');
const progressBar = document.getElementById('progressBar');
const usageText = document.getElementById('usageText');
const filterChips = document.querySelectorAll('.filter-chip');

// Indexing progress elements
const indexingOverlay = document.getElementById('indexingOverlay');
const indexingFile = document.getElementById('indexingFile');
const indexingETA = document.getElementById('indexingETA');
const indexingProgressBar = document.getElementById('indexingProgressBar');
const indexingCount = document.getElementById('indexingCount');
const indexingPercent = document.getElementById('indexingPercent');

const API_URL = 'http://localhost:8000';
let debounceTimer;
let progressPollingInterval;
let activeFilter = 'all';
let currentResults = [];
let selectedIndex = -1;

const PLACEHOLDERS = {
    all: 'Applications',
    text: 'Search docs',
    image: 'Search pics',
    video: 'Search video',
    audio: 'Search audio'
};

// Fetch stats on load
async function fetchStats() {
    try {
        const res = await fetch(`${API_URL}/stats`);
        const data = await res.json();
        planText.textContent = `Memory Usage`;
        progressBar.style.width = `${Math.min(data.usage_percent, 100)}%`;
        if (data.usage_percent > 90) progressBar.style.background = 'linear-gradient(90deg, #ff416c, #ff4b2b)';
        usageText.textContent = `${data.usage_percent}%`;
    } catch (e) {
        console.error('Failed to fetch stats', e);
    }
}

fetchStats();

// Window management
function updateWindowSize() {
    const isIndexing = !indexingOverlay.classList.contains('hidden');
    const hasResults = !resultsContainer.classList.contains('hidden');
    
    let height = 180; 
    if (isIndexing && hasResults) height = 520;
    else if (isIndexing) height = 280;
    else if (hasResults) height = 460;
    
    ipcRenderer.send('resize-window', 720, height);
}

function showLoading() {
    document.querySelector('.search-bar').classList.add('searching');
}

function hideLoading() {
    document.querySelector('.search-bar').classList.remove('searching');
}

function getFileIcon(fileType) {
    const icons = { image: '🖼️', video: '🎬', audio: '🎵', pdf: '📕', docx: '📝', text: '📄' };
    return icons[fileType] || '📄';
}

function displayResults(results) {
    currentResults = results;
    resultsList.innerHTML = '';
    resultPreview.innerHTML = '';
    
    if (results.length === 0) {
        resultsList.innerHTML = '<div class="info-box">No results found.</div>';
        selectedIndex = -1;
    } else {
        results.forEach((res, i) => {
            const div = document.createElement('div');
            div.className = 'result-item';
            div.id = `result-item-${i}`;
            const icon = getFileIcon(res.file_type);
            const score = (res.score * 100).toFixed(0);
            
            let snippet = res.chunk_text || '';
            if (res.content_type === 'image') {
                snippet = `<img src="file://${res.file_path}" class="result-thumb" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2224%22 height=%2224%22><rect width=%2224%22 height=%2224%22 fill=%22%23333%22/><text x=%2250%%22 y=%2250%%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23fff%22 font-size=%2210%22>🖼️</text></svg>'">`;
            } else if (!snippet && res.file_type) {
                if (res.file_type === 'image') snippet = '🖼️ Image file — press Enter to preview';
                else if (res.file_type === 'video') snippet = '🎬 Video file — press Enter to preview';
                else if (res.file_type === 'audio') snippet = '🎵 Audio file — press Enter to preview';
            }
            
            div.innerHTML = `
                <div class="result-title">
                    <span><span class="res-icon-bg">${icon}</span> ${res.document_name}</span>
                    <span class="result-score">${score}%</span>
                </div>
                <div class="result-snippet ${res.content_type === 'image' ? 'has-thumb' : ''}">${snippet}</div>
            `;
            div.onclick = () => {
                selectResult(i);
                if (res.file_path) {
                    ipcRenderer.send('open-file', res.file_path);
                }
            };
            resultsList.appendChild(div);
        });
        selectResult(0);
    }
    resultsContainer.classList.remove('hidden');
    updateWindowSize();
}

function selectResult(index) {
    if (index < 0 || index >= currentResults.length) return;
    
    if (selectedIndex >= 0) {
        const oldEl = document.getElementById(`result-item-${selectedIndex}`);
        if (oldEl) oldEl.classList.remove('selected');
    }
    
    selectedIndex = index;
    const newEl = document.getElementById(`result-item-${selectedIndex}`);
    if (newEl) {
        newEl.classList.add('selected');
        newEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    const res = currentResults[index];
    const icon = getFileIcon(res.file_type);
    
    let mediaHtml = `<div class="preview-icon-large">${icon}</div>`;
    if (res.file_type === 'image') {
        mediaHtml = `<img src="file://${res.file_path}" class="preview-media-img" onerror="this.outerHTML='<div class=\\'preview-icon-large\\'>${icon}</div>'">`;
    } else if (res.file_type === 'video') {
        mediaHtml = `<video src="file://${res.file_path}" class="preview-media-video" controls autoplay muted loop></video>`;
    } else if (res.file_type === 'audio') {
        mediaHtml = `<audio src="file://${res.file_path}" controls style="width:100%; margin-bottom: 16px;" autoplay></audio>`;
    }
    
    resultPreview.innerHTML = `
        ${mediaHtml}
        <div class="preview-title">${res.document_name}</div>
        <div class="preview-meta">${(res.score * 100).toFixed(0)}% Match • ${res.file_type.toUpperCase()}</div>
        ${res.chunk_text ? `<div class="preview-snippet">${res.chunk_text}</div>` : ''}
    `;
}

function displayAnswer(answer) {
    currentResults = [];
    resultsList.innerHTML = `<div class="answer-box">🤖 ${answer}</div>`;
    resultPreview.innerHTML = '';
    resultsContainer.classList.remove('hidden');
    updateWindowSize();
}

function displayInfo(message) {
    currentResults = [];
    resultsList.innerHTML = `<div class="info-box">${message}</div>`;
    resultPreview.innerHTML = '';
    resultsContainer.classList.remove('hidden');
    updateWindowSize();
}

// Indexing Progress Polling
function startPollingProgress() {
    if (progressPollingInterval) clearInterval(progressPollingInterval);
    
    indexingOverlay.classList.remove('hidden');
    updateWindowSize();
    
    progressPollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/index/status`);
            const data = await res.json();
            
            if (!data.is_indexing && data.percentage >= 100) {
                // Done
                clearInterval(progressPollingInterval);
                indexingFile.textContent = "✅ Indexing Complete";
                indexingETA.textContent = "";
                indexingProgressBar.style.width = "100%";
                indexingCount.textContent = `${data.total_files} / ${data.total_files}`;
                indexingPercent.textContent = "100%";
                
                fetchStats();
                setTimeout(() => {
                    indexingOverlay.classList.add('hidden');
                    updateWindowSize();
                }, 3000);
                return;
            }
            
            if (!data.is_indexing && data.total_files === 0) {
                clearInterval(progressPollingInterval);
                indexingOverlay.classList.add('hidden');
                updateWindowSize();
                return;
            }

            // Update UI
            indexingFile.textContent = `Indexing: ${data.current_file || 'Preparing...'}`;
            indexingProgressBar.style.width = `${data.percentage}%`;
            indexingCount.textContent = `${data.processed_files} / ${data.total_files}`;
            indexingPercent.textContent = `${data.percentage}%`;
            
            if (data.eta_seconds > 0) {
                const mins = Math.floor(data.eta_seconds / 60);
                const secs = Math.floor(data.eta_seconds % 60);
                indexingETA.textContent = `ETA: ${mins}m ${secs}s`;
            } else {
                indexingETA.textContent = "ETA: --";
            }

        } catch (e) {
            console.error("Polling error", e);
        }
    }, 1000);
}

async function handleCommand(val) {
    if (!val) {
        currentResults = [];
        resultsList.innerHTML = '';
        resultPreview.innerHTML = '';
        resultsContainer.classList.add('hidden');
        updateWindowSize();
        return;
    }

    if (val === 'status') {
        startPollingProgress();
        searchInput.value = '';
        return;
    }

    if (val.startsWith('index ')) {
        const folder = val.replace('index ', '');
        startIndexing(folder);
        return;
    }

    if (val.startsWith('ask ')) {
        const query = val.replace('ask ', '');
        showLoading();
        displayInfo(`Thinking about "${query}"...`);
        try {
            const res = await fetch(`${API_URL}/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: query, top_k: 5, file_type: activeFilter })
            });
            const data = await res.json();
            hideLoading();
            displayAnswer(data.answer);
        } catch (e) {
            hideLoading();
            displayInfo('❌ Ask API error.');
        }
        return;
    }
    
    // Default: search
    let query = val;
    if (val.startsWith('search ')) query = val.replace('search ', '');
    
    showLoading();
    try {
        const res = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, top_k: 8, file_type: activeFilter })
        });
        if (res.status === 429) {
            hideLoading();
            const data = await res.json();
            displayInfo(`⚠️ Quota Exceeded: ${data.detail || 'The 1000-request Gemini free limit has been reached.'}`);
            return;
        }
        const data = await res.json();
        hideLoading();
        displayResults(data.results);
    } catch (e) {
        hideLoading();
        displayInfo('❌ Search API error. Check if backend is running.');
    }
}

async function startIndexing(folderPath) {
    try {
        const res = await fetch(`${API_URL}/index`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_path: folderPath })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            startPollingProgress();
        } else {
            alert(`Indexing failed: ${data.message || data.detail}`);
        }
    } catch (e) {
        alert('❌ Index API error.');
    }
}

async function deleteIndex() {
    if (!confirm('Are you sure you want to PERMANENTLY delete the entire index? This cannot be undone.')) return;
    
    try {
        const res = await fetch(`${API_URL}/index`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok && data.success) {
            displayInfo('✨ Index cleared successfully.');
            fetchStats();
            setTimeout(() => {
                resultsContainer.classList.add('hidden');
                updateWindowSize();
            }, 2000);
        } else {
            alert(`Delete failed: ${data.detail}`);
        }
    } catch (e) {
        alert('❌ Delete API error.');
    }
}

// Event Listeners
indexFolderBtn.addEventListener('click', async () => {
    const folder = await ipcRenderer.invoke('select-folder');
    if (folder) {
        startIndexing(folder);
    }
});

clearIndexBtn.addEventListener('click', deleteIndex);

filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
        setActiveFilter(chip.getAttribute('data-type'));
    });
});

function setActiveFilter(type) {
    activeFilter = type;
    filterChips.forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-type') === type);
    });
    searchInput.placeholder = PLACEHOLDERS[type] || 'Applications';
    
    const val = searchInput.value.trim();
    if (val) handleCommand(val);
}

function cycleFilter(direction) {
    const types = Object.keys(PLACEHOLDERS);
    let currentIndex = types.indexOf(activeFilter);
    if (direction === 'next') {
        currentIndex = (currentIndex + 1) % types.length;
    } else {
        currentIndex = (currentIndex - 1 + types.length) % types.length;
    }
    setActiveFilter(types[currentIndex]);
}

searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const val = e.target.value.trim();
    if (!val) {
        currentResults = [];
        resultsList.innerHTML = '';
        resultPreview.innerHTML = '';
        resultsContainer.classList.add('hidden');
        updateWindowSize();
        return;
    }
    if (val.startsWith('index ') || val.startsWith('ask ') || val === 'status') return;

    debounceTimer = setTimeout(() => {
        handleCommand(val);
    }, 400);
});

searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        clearTimeout(debounceTimer);
        const val = e.target.value.trim();
        const isResultsVisible = !resultsContainer.classList.contains('hidden');
        if (isResultsVisible && currentResults.length > 0 && selectedIndex >= 0 && !val.startsWith('index ') && !val.startsWith('ask ') && val !== 'status') {
            ipcRenderer.send('open-file', currentResults[selectedIndex].file_path);
        } else {
            handleCommand(val);
        }
    } else if (e.key === 'Escape') {
        ipcRenderer.send('hide-window');
        searchInput.value = '';
        resultsContainer.classList.add('hidden');
        updateWindowSize();
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (currentResults.length > 0) selectResult(selectedIndex + 1);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (currentResults.length > 0) selectResult(selectedIndex - 1);
    } else if (e.key === 'ArrowRight' && searchInput.value === '') {
        cycleFilter('next');
    } else if (e.key === 'ArrowLeft' && searchInput.value === '') {
        cycleFilter('prev');
    }
});

window.addEventListener('focus', () => {
    searchInput.focus();
    fetchStats();
});
