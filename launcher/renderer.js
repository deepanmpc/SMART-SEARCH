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
const helpBtn = document.getElementById('helpBtn');

const wizardNext1 = document.getElementById('wizardNext1');
const wizardNext2 = document.getElementById('wizardNext2');
const wizardBack2 = document.getElementById('wizardBack2');
const wizardBack3 = document.getElementById('wizardBack3');
const getKeyBtn = document.getElementById('getKeyBtn');
const apiKeyInput = document.getElementById('apiKeyInput');

const step1 = document.getElementById('wizardStep1');
const step2 = document.getElementById('wizardStep2');
const step3 = document.getElementById('wizardStep3');

const API_URL = 'http://localhost:8000';
let debounceTimer;
let progressPollingInterval;
let activeFilter = 'all';
let currentResults = [];
let selectedIndex = -1;

const PLACEHOLDERS = {
    all: 'Search files or ask AI... (e.g. "image of a dog")',
    text: '≣ Search docs (e.g. "notes about neural networks")',
    image: '▣ Search pics (e.g. "photo of sunset")',
    video: '🎞️ Search video (e.g. "meeting recording")',
    audio: '≋ Search audio (e.g. "podcast episode")'
};

// Fetch stats on load
async function checkOnboarding() {
    try {
        const config = await ipcRenderer.invoke('get-config');
        const hasKey = !!config.google_api_key;

        // If key is missing, show wizard Step 2 immediately
        if (!hasKey) {
            setupWizard.classList.remove('hidden');
            showStep(2);
            updateWindowSize();
            return true; // Still onboarding
        }
        
        // If we have a key, we can try to fetch stats
        return false; 
    } catch (e) {
        console.error('Failed to check onboarding', e);
        return false;
    }
}

async function fetchStats() {
    try {
        const config = await ipcRenderer.invoke('get-config');
        const hasKey = !!config.google_api_key;

        const res = await fetch(`${API_URL}/stats`);
        if (!res.ok) throw new Error('Backend not ready');
        
        const data = await res.json();
        
        // Show Index Capacity as the primary "Increasing" data
        const totalChunks = data.total_chunks || 0;
        const chunkLimit = data.plan_limit || 50000;
        const indexPercent = Math.min((totalChunks / chunkLimit) * 100, 100);
        
        planText.textContent = `Index Status: ${totalChunks.toLocaleString()} / ${chunkLimit.toLocaleString()} chunks`;
        progressBar.style.width = `${indexPercent}%`;
        
        // Show RAM Usage as secondary info
        const usageMb = data.ram_usage_mb || 0;
        usageText.textContent = `System RAM: ${Math.round(usageMb)} MB`;
        
        if (indexPercent > 90) progressBar.style.background = 'linear-gradient(90deg, #ff416c, #ff4b2b)';
        else progressBar.style.background = 'linear-gradient(90deg, #007aff, #5ac8fa)';

        // AUTO-SHOW INDEXING: Check backend status
        const statusRes = await fetch(`${API_URL}/index/status`);
        const statusData = await statusRes.json();
        if (statusData.is_indexing && !progressPollingInterval) {
            startPollingProgress();
        }

        // Only hide/show based on stats if we ALREADY HAVE A KEY
        // BUT: Do not force onboarding if index is empty but we have a key.
        // Users can just index a folder later.
        if (hasKey) {
            setupWizard.classList.add('hidden');
        } else {
            // No key, must show wizard
            setupWizard.classList.remove('hidden');
            showStep(1);
        }
        updateWindowSize();
    } catch (e) {
        // If backend fails but we have no key, checkOnboarding already handled it.
        // If backend fails but we HAVE a key, just log and wait for next poll.
        console.log('Backend not ready yet, retrying soon...');
    }
}

function showStep(num) {
    [step1, step2, step3].forEach((s, i) => {
        s.classList.toggle('hidden', i + 1 !== num);
    });
    updateWindowSize();
}

// Wizard Event Listeners
if (wizardNext1) wizardNext1.onclick = () => showStep(2);
if (wizardBack2) wizardBack2.onclick = () => showStep(1);
if (wizardNext2) wizardNext2.onclick = async () => {
    const key = apiKeyInput.value.trim();
    if (!key || key.length < 20) {
        displayInfo("⚠️ Please enter a valid Gemini API Key.");
        return;
    }
    await ipcRenderer.invoke('save-config', { google_api_key: key });
    showStep(3);
};
if (wizardBack3) wizardBack3.onclick = () => showStep(2);
if (getKeyBtn) getKeyBtn.onclick = () => {
    require('electron').shell.openExternal('https://aistudio.google.com/app/apikey');
};
if (helpBtn) helpBtn.onclick = () => {
    ipcRenderer.send('open-docs');
    const tips = [
        "<b>Enter:</b> Open File",
        "<b>Space:</b> Preview File",
        "<b>Cmd+Shift+Space:</b> Toggle Launcher",
        "<b>ask query:</b> AI Assistant mode",
        "<b>Shift + Arrow:</b> Cycle Filters"
    ];
    const randomTip = tips[Math.floor(Math.random() * tips.length)];
    displayInfo(`
        <div style="text-align: left; padding: 10px;">
            <div style="margin-bottom: 15px;">
                <h4 style="color: var(--accent); margin-bottom: 5px;">🔒 Privacy First</h4>
                <p style="font-size: 11px; opacity: 0.8; line-height: 1.4;">Search Wizard runs 100% locally. Your files never leave your machine. Only semantic embeddings are generated via your Gemini API key.</p>
            </div>
            <div style="margin-bottom: 10px;">
                <h4 style="color: var(--accent); margin-bottom: 5px;">💡 Quick Tip</h4>
                <p style="font-size: 11px; opacity: 0.8; line-height: 1.4;">${randomTip}</p>
            </div>
            <div style="font-size: 10px; opacity: 0.5;">Documentation opened in background.</div>
        </div>
    `);
};

fetchStats();
// Periodically refresh stats to keep UI sync'd
setInterval(fetchStats, 10000);

if (setupStartBtn) {
    setupStartBtn.onclick = async () => {
        const paths = await ipcRenderer.invoke('select-folder');
        if (paths && paths.length > 0) {
            startIndexing(paths);
            if (setupWizard) setupWizard.classList.add('hidden');
        }
    };
}

// Window management
function updateWindowSize() {
    setTimeout(() => {
        const width = 900;
        const container = document.querySelector('.launcher-container');
        // Ensure we capture the full scroll height plus some buffer for the shadow
        const height = Math.max(container.scrollHeight + 40, 180); 
        ipcRenderer.send('resize-window', width, height);
    }, 10);
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
    // Remove extension
    let cleaned = name.replace(/\.[^/.]+$/, ""); 
    
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    // 1. macOS screenshot pattern: Screenshot 2026-02-06 at 3.43.08 PM
    const screenshotMatch = cleaned.match(/Screenshot (\d{4})-(\d{2})-(\d{2}) at (.*)/);
    if (screenshotMatch) {
        const month = months[parseInt(screenshotMatch[2]) - 1];
        const day = parseInt(screenshotMatch[3]);
        return `Screenshot -- ${month} ${day}`;
    }

    // 2. Photo on pattern: Photo on 08-05-24 at 10.51 PM
    const photoMatch = cleaned.match(/Photo on (\d{2})-(\d{2})-(\d{2}) at (.*)/);
    if (photoMatch) {
        // Assuming DD-MM-YY or MM-DD-YY. Let's try to be smart or just simplify to "Photo -- Month Day"
        // Based on the user's screenshot "08-05-24", likely May 8 or Aug 5.
        const monthIndex = parseInt(photoMatch[1]) - 1;
        if (monthIndex >= 0 && monthIndex < 12) {
            const month = months[monthIndex];
            const day = parseInt(photoMatch[2]);
            return `Photo -- ${month} ${day}`;
        }
        return `Photo -- ${photoMatch[1]}-${photoMatch[2]}`;
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
            // REMOVE DEVELOPER METADATA: Filter out [Image: tile...] or [Video: ...]
            if (snippet.startsWith('[') && snippet.includes(': ')) {
                snippet = '';
            }

            if (!snippet && res.file_type) {
                if (res.file_type === 'image') snippet = '🖼️ Image file — View preview';
                else if (res.file_type === 'video') snippet = '🎬 Video file — View preview';
                else if (res.file_type === 'audio') snippet = '🎵 Audio file — View preview';
            }
            
            const isTopResult = i === 0;
            const topResultBadge = isTopResult ? `<span style="background: var(--accent); color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 800; text-transform: uppercase; margin-right: 8px; vertical-align: middle;">TOP RESULT</span>` : '';

            div.innerHTML = `
                <div class="result-title">
                    <div class="result-name-wrapper">
                        <span class="res-icon-bg">${icon}</span>
                        <span class="result-name-text">${topResultBadge}${displayName}</span>
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

async function selectResult(index) {
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
    
    let snippet = res.chunk_text || '';
    if (snippet.startsWith('[') && (snippet.includes(': ') || snippet.includes(' Content]'))) {
        snippet = '';
    }

    let mediaHtml = `<div class="preview-icon-large">${icon}</div>`;
    if (res.file_type === 'image') {
        mediaHtml = `<img src="file://${res.file_path}" class="preview-media-img" loading="lazy" onerror="this.outerHTML='<div class=\'preview-icon-large\'>${icon}</div>'">`;
    } else if (res.file_type === 'video') {
        mediaHtml = `<video src="file://${res.file_path}" class="preview-media-video" controls autoplay muted loop></video>`;
    } else if (res.file_type === 'audio') {
        mediaHtml = `<audio src="file://${res.file_path}" controls autoplay style="width: 180px; border-radius: 20px;"></audio>`;
    }
    
    // Initial display
    resultPreview.innerHTML = `
        <div class="interactive-preview" style="width: auto;" onclick="ipcRenderer.send('open-file', '${res.file_path}')">
            ${mediaHtml}
        </div>
        <div class="preview-content">
            <div class="preview-meta">${semanticScore} • ${friendlyType}</div>
            <div class="preview-title clickable-title" onclick="ipcRenderer.send('open-file', '${res.file_path}')">${displayName}</div>
            <div id="enhancedPreview" class="preview-snippet">${snippet || 'Loading preview...'}</div>
        </div>
    `;

    // Fetch enhanced preview
    try {
        const pRes = await fetch(`${API_URL}/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: res.file_path })
        });
        const pData = await pRes.json();
        const enhancedEl = document.getElementById('enhancedPreview');
        if (enhancedEl) {
            if (pData.content) {
                enhancedEl.innerHTML = `<pre style="white-space: pre-wrap; font-size: 11px; font-family: 'SF Mono', monospace; opacity: 0.9;">${pData.content}</pre>`;
            } else {
                enhancedEl.innerHTML = '';
            }
            const metaEl = document.querySelector('.preview-meta');
            if (metaEl) metaEl.innerText = `${semanticScore} • ${friendlyType} • ${pData.size_mb} MB`;
        }
    } catch (e) {
        console.error("Preview fetch error", e);
    }
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
        displayInfo(`Thinking about "${query}"... `);
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
            displayInfo('❌ Something went wrong. Please try again.');
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
        displayInfo('❌ Unable to reach Search Wizard backend. Make sure it is running.');
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
            console.log("Indexing started successfully");
            startPollingProgress();
        } else {
            // If already in progress, just show the UI
            if (data.message && data.message.includes("already in progress")) {
                startPollingProgress();
            } else {
                displayInfo(`❌ Indexing failed: ${data.message || data.detail}`);
            }
        }
    } catch (e) {
        displayInfo('❌ Index API error. Make sure backend is running.');
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
            displayInfo(`❌ Delete failed: ${data.detail}`);
        }
    } catch (e) {
        displayInfo('❌ Delete API error.');
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
    searchInput.placeholder = PLACEHOLDERS[type] || 'search with magic';
    
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

searchInput.addEventListener('focus', () => {
    // Just focus, no suggestions
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

async function init() {
    console.log('Search Wizard Renderer Initializing...');
    const onboarding = await checkOnboarding();
    if (!onboarding) {
        fetchStats();
    }
}

// Start polling for stats periodically if not onboarding
setInterval(() => {
    const isWizardVisible = !setupWizard.classList.contains('hidden');
    if (!isWizardVisible) fetchStats();
}, 5000);

// Initialize on load
init();

window.addEventListener('focus', () => {
    searchInput.focus();
    checkOnboarding().then(onboarding => {
        if (!onboarding) fetchStats();
    });
});