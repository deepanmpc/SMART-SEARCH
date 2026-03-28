const { ipcRenderer } = require('electron');

const searchInput = document.getElementById('searchInput');
const indexFolderBtn = document.getElementById('indexFolderBtn');
const clearIndexBtn = document.getElementById('clearIndexBtn');
const resultsContainer = document.getElementById('resultsContainer');
const resultsList = document.getElementById('resultsList');
const resultPreview = document.getElementById('resultPreview');
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
const stopIndexingBtn = document.getElementById('stopIndexingBtn');
const pauseIndexingBtn = document.getElementById('pauseIndexingBtn');
const setupWizard = document.getElementById('setupWizard');
const setupStartBtn = document.getElementById('setupStartBtn');

const API_URL = 'http://localhost:8000';
let debounceTimer;
let progressPollingInterval;
let activeFilter = 'all';
let currentResults = [];
let selectedIndex = -1;

const PLACEHOLDERS = {
    all: '✦ Applications',
    text: '≣ Search docs',
    image: '▣ Search pics',
    video: '🎞️ Search video',
    audio: '≋ Search audio'
};

// Fetch stats on load
async function fetchStats() {
    try {
        const res = await fetch(`${API_URL}/stats`);
        const data = await res.json();
        planText.textContent = `Memory Usage`;
        
        const usageMb = data.ram_usage_mb || 0;
        const limitMb = data.ram_limit_mb || 500;
        const percent = Math.min((usageMb / limitMb) * 100, 100);
        
        progressBar.style.width = `${percent}%`;
        if (percent > 90) progressBar.style.background = 'linear-gradient(90deg, #ff416c, #ff4b2b)';
        usageText.textContent = `${Math.round(usageMb)} MB / ${limitMb} MB`;
    } catch (e) {
        console.error('Failed to fetch stats', e);
    }
}

fetchStats();

// Check for first-time setup
if (!localStorage.getItem('smart-search-setup-done')) {
    setTimeout(() => {
        if (setupWizard) {
            setupWizard.classList.remove('hidden');
            updateWindowSize();
        }
    }, 100);
}

if (setupStartBtn) {
    setupStartBtn.onclick = async () => {
        const paths = await ipcRenderer.invoke('select-folder');
        if (paths && paths.length > 0) {
            startIndexing(paths);
            localStorage.setItem('smart-search-setup-done', 'true');
            if (setupWizard) setupWizard.classList.add('hidden');
        }
    };
}

// Window management
function updateWindowSize() {
    setTimeout(() => {
        const width = 900;
        const container = document.querySelector('.launcher-container');
        // Standard padding for macOS shadows and floating effect
        const height = container.scrollHeight + 100; 
        ipcRenderer.send('resize-window', width, height);
    }, 50);
}

function showLoading() {
    document.querySelector('.top-row').classList.add('searching');
}

function hideLoading() {
    document.querySelector('.top-row').classList.remove('searching');
}

function getFileIcon(fileType) {
    const icons = { 
        image: '▣', 
        video: '🎞️', 
        audio: '≋', 
        pdf: '📕', 
        docx: '≣', 
        text: '📄' 
    };
    return icons[fileType] || '📄';
}

function getUserFriendlyFileType(fileType) {
    const map = {
        'image': 'Image',
        'video': 'Video',
        'audio': 'Audio',
        'pdf': 'PDF Document',
        'docx': 'Word Document',
        'text': 'Text Document',
        'pptx': 'PowerPoint'
    };
    return map[fileType] || fileType.toUpperCase();
}

function getSemanticScore(score) {
    if (score >= 0.8) return 'Best Match';
    if (score >= 0.5) return 'Strong Match';
    return 'Possible Match';
}

function cleanFileName(name) {
    // Remove common timestamp patterns like "Screenshot 2026-02-06 at 3.43PM" -> "Screenshot -- Feb 6"
    // Also remove file extensions for display
    let cleaned = name.replace(/\.[^/.]+$/, ""); // Remove extension
    
    // Check for macOS screenshot pattern: Screenshot 2026-02-06 at 3.43.08 PM
    const screenshotMatch = cleaned.match(/Screenshot (\d{4})-(\d{2})-(\d{2}) at (.*)/);
    if (screenshotMatch) {
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = months[parseInt(screenshotMatch[2]) - 1];
        const day = parseInt(screenshotMatch[3]);
        return `Screenshot -- ${month} ${day}`;
    }
    
    return cleaned;
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
            const semanticScore = getSemanticScore(res.score);
            const displayName = cleanFileName(res.document_name);
            
            let snippet = res.chunk_text || '';
            if (!snippet && res.file_type) {
                if (res.file_type === 'image') snippet = '🖼️ Image file — View preview on right';
                else if (res.file_type === 'video') snippet = '🎬 Video file — View preview on right';
                else if (res.file_type === 'audio') snippet = '🎵 Audio file — View preview on right';
            }
            
            div.innerHTML = `
                <div class="result-title">
                    <div class="result-name-wrapper">
                        <span class="res-icon-bg">${icon}</span>
                        <span class="result-name-text">${displayName}</span>
                    </div>
                    <span class="result-score">${semanticScore}</span>
                </div>
                ${snippet ? `<div class="result-snippet">${snippet}</div>` : ''}
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
    const friendlyType = getUserFriendlyFileType(res.file_type);
    const semanticScore = getSemanticScore(res.score);
    const displayName = cleanFileName(res.document_name);
    
    let mediaHtml = `<div class="preview-icon-large">${icon}</div>`;
    if (res.file_type === 'image') {
        mediaHtml = `<img src="file://${res.file_path}" class="preview-media-img" style="max-width: 180px; max-height: 120px;" onerror="this.outerHTML='<div class=\\'preview-icon-large\\'>${icon}</div>'">`;
    } else if (res.file_type === 'video') {
        mediaHtml = `<video src="file://${res.file_path}" class="preview-media-video" style="max-width: 180px; max-height: 120px;" controls autoplay muted loop></video>`;
    } else if (res.file_type === 'audio') {
        mediaHtml = `<audio src="file://${res.file_path}" controls autoplay style="width: 180px;"></audio>`;
    }
    
    resultPreview.innerHTML = `
        <div class="interactive-preview" style="width: auto;" onclick="ipcRenderer.send('open-file', '${res.file_path}')">
            ${mediaHtml}
        </div>
        <div class="preview-content">
            <div class="preview-meta">${semanticScore} • ${friendlyType}</div>
            <div class="preview-title clickable-title" onclick="ipcRenderer.send('open-file', '${res.file_path}')">${displayName}</div>
            ${res.chunk_text ? `<div class="preview-snippet">${res.chunk_text}</div>` : ''}
        </div>
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
            if (data.is_paused) {
                indexingFile.textContent = `⏸️ Paused: ${data.current_file}`;
                pauseIndexingBtn.textContent = 'Resume';
            } else {
                indexingFile.textContent = `Indexing: ${data.current_file || 'Preparing...'}`;
                pauseIndexingBtn.textContent = 'Pause';
            }
            
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

async function startIndexing(paths) {
    try {
        const res = await fetch(`${API_URL}/index`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: paths })
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
indexFolderBtn.onclick = async () => {
    const paths = await ipcRenderer.invoke('select-folder');
    if (paths && paths.length > 0) {
        startIndexing(paths);
    }
};

clearIndexBtn.addEventListener('click', deleteIndex);

stopIndexingBtn.onclick = async () => {
    try {
        const res = await fetch(`${API_URL}/index/stop`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            indexingFile.textContent = "🛑 Stopping...";
        }
    } catch (e) {
        console.error("Stop error", e);
    }
};

pauseIndexingBtn.onclick = async () => {
    try {
        const res = await fetch(`${API_URL}/index/pause`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            // State will be updated by polling
        }
    } catch (e) {
        console.error("Pause error", e);
    }
};

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

function showSuggestions() {
    currentResults = [];
    resultsList.innerHTML = `
        <div class="info-box" style="padding: 24px; text-align: center;">
            <div style="font-weight: 600; font-size: 14px; color: var(--accent); margin-bottom: 16px; opacity: 0.8;">✦ QUICK FILTERS</div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                <div class="filter-chip active" style="border-radius: 8px; width: auto; padding: 0 14px; height: 32px; font-size: 13px;" onclick="setActiveFilter('text')">≣ Documents</div>
                <div class="filter-chip active" style="border-radius: 8px; width: auto; padding: 0 14px; height: 32px; font-size: 13px;" onclick="setActiveFilter('image')">▣ Images</div>
                <div class="filter-chip active" style="border-radius: 8px; width: auto; padding: 0 14px; height: 32px; font-size: 13px;" onclick="setActiveFilter('video')">🎞️ Videos</div>
                <div class="filter-chip active" style="border-radius: 8px; width: auto; padding: 0 14px; height: 32px; font-size: 13px;" onclick="setActiveFilter('audio')">≋ Audio</div>
            </div>
            <div style="margin-top: 24px; font-size: 12px; color: var(--text-secondary); opacity: 0.6;">
                Try searching for "project notes", "vacation photos", or "meeting recording"
            </div>
        </div>
    `;
    resultPreview.innerHTML = '';
    resultsContainer.classList.remove('hidden');
    updateWindowSize();
}

searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const val = e.target.value.trim();
    if (!val) {
        showSuggestions();
        return;
    }
    if (val.startsWith('index ') || val.startsWith('ask ') || val === 'status') return;

    debounceTimer = setTimeout(() => {
        handleCommand(val);
    }, 400);
});

searchInput.addEventListener('focus', () => {
    if (!searchInput.value.trim()) {
        showSuggestions();
    }
});

// Drag and Drop support
document.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.body.style.background = 'rgba(0, 122, 255, 0.05)';
});

document.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.body.style.background = 'transparent';
});

document.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.body.style.background = 'transparent';
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
        const paths = files.map(f => f.path);
        startIndexing(paths);
    }
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
    } else if (e.key === ' ') {
        // Space to open file if a result is selected and search input is not focused or is empty
        const isResultsVisible = !resultsContainer.classList.contains('hidden');
        if (isResultsVisible && currentResults.length > 0 && selectedIndex >= 0 && (document.activeElement !== searchInput || searchInput.value === '')) {
            e.preventDefault();
            ipcRenderer.send('open-file', currentResults[selectedIndex].file_path);
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
    } else if (e.key === 'ArrowRight' && (searchInput.value === '' || e.ctrlKey || e.metaKey)) {
        cycleFilter('next');
    } else if (e.key === 'ArrowLeft' && (searchInput.value === '' || e.ctrlKey || e.metaKey)) {
        cycleFilter('prev');
    }
 else if (e.key === 'r' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        const isResultsVisible = !resultsContainer.classList.contains('hidden');
        if (isResultsVisible && currentResults.length > 0 && selectedIndex >= 0) {
            ipcRenderer.send('reveal-file', currentResults[selectedIndex].file_path);
        }
    }
});

window.addEventListener('focus', () => {
    searchInput.focus();
    fetchStats();
});
