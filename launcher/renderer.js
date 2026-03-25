const { ipcRenderer } = require('electron');

const searchInput = document.getElementById('searchInput');
const indexFolderBtn = document.getElementById('indexFolderBtn');
const clearIndexBtn = document.getElementById('clearIndexBtn');
const resultsContainer = document.getElementById('resultsContainer');
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
    loadingIndicator.classList.remove('hidden');
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

function displayResults(results) {
    resultsContainer.innerHTML = '';
    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="info-box">No results found.</div>';
    } else {
        results.forEach(res => {
            const div = document.createElement('div');
            div.className = 'result-item';
            div.innerHTML = `
                <div class="result-title">
                    <span>📄 ${res.document_name}</span>
                    <span class="result-score">${(res.score * 100).toFixed(0)}%</span>
                </div>
                <div class="result-snippet">${res.chunk_text || ''}</div>
            `;
            div.onclick = () => {
                if (res.file_path) {
                    ipcRenderer.send('open-file', res.file_path);
                }
            };
            resultsContainer.appendChild(div);
        });
    }
    resultsContainer.classList.remove('hidden');
    updateWindowSize();
}

function displayAnswer(answer) {
    resultsContainer.innerHTML = `<div class="answer-box">🤖 ${answer}</div>`;
    resultsContainer.classList.remove('hidden');
    updateWindowSize();
}

function displayInfo(message) {
    resultsContainer.innerHTML = `<div class="info-box">${message}</div>`;
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
        resultsContainer.innerHTML = '';
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
        const data = await res.json();
        hideLoading();
        displayResults(data.results);
    } catch (e) {
        hideLoading();
        displayInfo('❌ Search API error.');
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
        resultsContainer.innerHTML = '';
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
        handleCommand(e.target.value.trim());
    } else if (e.key === 'Escape') {
        ipcRenderer.send('hide-window');
        searchInput.value = '';
        resultsContainer.classList.add('hidden');
        updateWindowSize();
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
