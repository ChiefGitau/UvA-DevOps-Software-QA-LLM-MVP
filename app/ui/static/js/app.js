let sessionId = null;
let currentFindings = [];
let sortCol = -1;
let sortAsc = true;

const SEV_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3};

function setStatus(msg, type = 'info') {
    const el = document.getElementById('status');
    el.className = 'status ' + type;
    el.textContent = msg;
}

function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }

// --- Upload ---
async function uploadZip() {
    const input = document.getElementById('zipFile');
    if (!input.files.length) { setStatus('Please select a ZIP file', 'error'); return; }

    setStatus('Uploading...', 'info');
    const form = new FormData();
    form.append('archive', input.files[0]);

    try {
        const res = await fetch('/api/session/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');
        sessionId = data.session_id;
        setStatus('Upload successful! Session: ' + sessionId.slice(0, 8) + '...', 'success');
        await loadFiles();
    } catch (e) { setStatus('Upload failed: ' + e.message, 'error'); }
}

// --- Clone ---
async function cloneRepo() {
    const url = document.getElementById('gitUrl').value.trim();
    if (!url) { setStatus('Please enter a GitHub URL', 'error'); return; }

    setStatus('Cloning repository...', 'info');
    try {
        const res = await fetch('/api/session/clone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ git_url: url }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Clone failed');
        sessionId = data.session_id;
        setStatus('Clone successful! Session: ' + sessionId.slice(0, 8) + '...', 'success');
        await loadFiles();
    } catch (e) { setStatus('Clone failed: ' + e.message, 'error'); }
}

// --- File List ---
async function loadFiles() {
    const res = await fetch(`/api/session/${sessionId}/files`);
    const data = await res.json();
    const files = data.files || [];

    const container = document.getElementById('fileList');
    container.innerHTML = files.map(f =>
        `<label><input type="checkbox" value="${f}" checked> ${f}</label>`
    ).join('');
    document.getElementById('fileCount').textContent = `${files.length} files`;
    show('fileSection');
}

function toggleAll(checked) {
    document.querySelectorAll('#fileList input').forEach(cb => cb.checked = checked);
}

// --- Analyse ---
async function runAnalysis() {
    const btn = document.getElementById('analyseBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Analysing...';

    const selected = [...document.querySelectorAll('#fileList input:checked')].map(cb => cb.value);
    if (!selected.length) { setStatus('Select at least one file', 'error'); btn.disabled = false; btn.textContent = 'Run Analysis (all 4 tools)'; return; }

    try {
        const res = await fetch('/api/analyse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, selected_files: selected }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Analysis failed');

        currentFindings = data.findings || [];
        renderSummary(data.summary);
        renderFindings(currentFindings);
        show('resultsSection');
        setStatus(`Analysis complete: ${currentFindings.length} findings`, 'success');
    } catch (e) {
        setStatus('Analysis failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Analysis (all 4 tools)';
    }
}

// --- Summary ---
function renderSummary(s) {
    if (!s) return;
    const el = document.getElementById('summary');
    el.innerHTML = `
        <span class="badge total">${s.total} Total</span>
        <span class="badge critical">${s.by_severity.CRITICAL || 0} Critical</span>
        <span class="badge high">${s.by_severity.HIGH || 0} High</span>
        <span class="badge medium">${s.by_severity.MEDIUM || 0} Medium</span>
        <span class="badge low">${s.by_severity.LOW || 0} Low</span>
    `;
}

// --- Findings Table ---
function renderFindings(findings) {
    const body = document.getElementById('findingsBody');
    if (!findings.length) { body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--muted)">No findings 🎉</td></tr>'; return; }

    body.innerHTML = findings.map((f, i) => `<tr>
        <td>${i + 1}</td>
        <td><span class="sev sev-${f.severity}">${f.severity}</span></td>
        <td><span class="type">${f.type}</span></td>
        <td>${f.tool}</td>
        <td>${f.file || '—'}</td>
        <td>${f.line || '—'}</td>
        <td>${escHtml(f.message)}</td>
        <td>${f.code_snippet ? '<code class="snippet">' + escHtml(f.code_snippet) + '</code>' : '—'}</td>
    </tr>`).join('');
}

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// --- Sort ---
function sortTable(col) {
    if (sortCol === col) sortAsc = !sortAsc; else { sortCol = col; sortAsc = true; }

    const keys = ['_idx','severity','type','tool','file','line','message','code_snippet'];
    const key = keys[col];

    currentFindings.sort((a, b) => {
        let va = a[key], vb = b[key];
        if (key === 'severity') { va = SEV_ORDER[va] ?? 9; vb = SEV_ORDER[vb] ?? 9; }
        if (key === 'line') { va = va || 0; vb = vb || 0; }
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
    });
    renderFindings(currentFindings);
}