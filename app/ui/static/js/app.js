let sessionId = null;
let currentFindings = [];
let sortCol = -1;
let sortAsc = true;

const SEV_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3};
const SESSION_KEY = 'qrt_session_id';

// ── Helpers ───────────────────────────────────────────────────────

function setStatus(msg, type = 'info') {
    const el = document.getElementById('status');
    el.className = 'status ' + type;
    el.textContent = msg;
}

function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }

function activateStep(n) {
    [1,2,3,4].forEach(i => {
        const el = document.getElementById('step' + i);
        if (!el) return;
        el.classList.remove('active', 'done');
        if (i < n) el.classList.add('done');
        else if (i === n) el.classList.add('active');
    });
}

function setLoading(btnId, loading, label) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading
        ? '<span class="spinner"></span>' + label
        : label;
}

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Session persistence ───────────────────────────────────────────

function saveSession(id) {
    sessionId = id;
    localStorage.setItem(SESSION_KEY, id);
}

function clearSession() {
    sessionId = null;
    localStorage.removeItem(SESSION_KEY);
    hide('sessionBanner');
    hide('fileSection');
    hide('resultsSection');
    hide('repairSection');
    hide('repairResults');
    setStatus('', 'info');
    currentFindings = [];
}

function restoreSession() {
    const saved = localStorage.getItem(SESSION_KEY);
    if (!saved) return;
    sessionId = saved;
    const banner = document.getElementById('sessionBanner');
    banner.innerHTML = `
        Resuming session <strong>${saved.slice(0, 8)}…</strong>
        <button onclick="clearSession()">Start new session</button>
    `;
    show('sessionBanner');
    // Reload files for the saved session
    loadFiles().catch(() => {
        // Session expired or gone — clear silently
        clearSession();
    });
}

// ── Upload ────────────────────────────────────────────────────────

async function uploadZip() {
    const input = document.getElementById('zipFile');
    if (!input.files.length) { setStatus('Please select a ZIP file', 'error'); return; }

    setLoading('uploadBtn', true, 'Uploading...');
    setStatus('Uploading...', 'info');
    const form = new FormData();
    form.append('archive', input.files[0]);

    try {
        const res = await fetch('/api/session/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');
        saveSession(data.session_id);
        hide('sessionBanner');
        setStatus('Upload successful! Session: ' + sessionId.slice(0, 8) + '...', 'success');
        activateStep(2);
        await loadFiles();
    } catch (e) {
        setStatus('Upload failed: ' + e.message, 'error');
    } finally {
        setLoading('uploadBtn', false, 'Upload ZIP');
    }
}

// ── Clone ─────────────────────────────────────────────────────────

async function cloneRepo() {
    const url = document.getElementById('gitUrl').value.trim();
    if (!url) { setStatus('Please enter a GitHub URL', 'error'); return; }

    setLoading('cloneBtn', true, 'Cloning...');
    setStatus('Cloning repository...', 'info');

    try {
        const res = await fetch('/api/session/clone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ git_url: url }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Clone failed');
        saveSession(data.session_id);
        hide('sessionBanner');
        setStatus('Clone successful! Session: ' + sessionId.slice(0, 8) + '...', 'success');
        activateStep(2);
        await loadFiles();
    } catch (e) {
        setStatus('Clone failed: ' + e.message, 'error');
    } finally {
        setLoading('cloneBtn', false, 'Clone Repo');
    }
}

// ── File List ─────────────────────────────────────────────────────

async function loadFiles() {
    const res = await fetch(`/api/session/${sessionId}/files`);
    if (!res.ok) throw new Error('Session not found');
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

// ── Analyse ───────────────────────────────────────────────────────

async function runAnalysis() {
    const btn = document.getElementById('analyseBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Analysing...';

    const selected = [...document.querySelectorAll('#fileList input:checked')].map(cb => cb.value);
    if (!selected.length) {
        setStatus('Select at least one file', 'error');
        btn.disabled = false;
        btn.textContent = 'Run Analysis (all 4 tools)';
        return;
    }

    // Reset repair section for a fresh analysis
    hide('repairResults');
    hide('repairSection');

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
        activateStep(3);

        if (currentFindings.length > 0) {
            await loadProviders();
            renderRepairHint(currentFindings.length);
            show('repairSection');
        }

        // Hide verification from a previous run when re-analysing
        hide('verificationSection');
        hide('verificationResults');

        setStatus(`Analysis complete: ${currentFindings.length} findings`, 'success');
    } catch (e) {
        setStatus('Analysis failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Analysis (all 4 tools)';
    }
}

// --- Summary ---
function renderSummary(s, targetId = 'summary') {

    if (!s) return;
    const el = document.getElementById(targetId);
    el.innerHTML = `
        <span class="badge total">${s.total} Total</span>
        <span class="badge critical">${s.by_severity.CRITICAL || 0} Critical</span>
        <span class="badge high">${s.by_severity.HIGH || 0} High</span>
        <span class="badge medium">${s.by_severity.MEDIUM || 0} Medium</span>
        <span class="badge low">${s.by_severity.LOW || 0} Low</span>
    `;
}

// ── Findings Table ────────────────────────────────────────────────

function renderFindings(findings) {
    const body = document.getElementById('findingsBody');
    if (!findings.length) {
        body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--muted)">No findings 🎉</td></tr>';
        return;
    }

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

// ── Sort ──────────────────────────────────────────────────────────

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

// ── LLM Model Selection ───────────────────────────────────────────

async function loadProviders() {
    try {
        const res = await fetch('/api/llm/providers');
        const data = await res.json();
        const select = document.getElementById('providerSelect');
        select.innerHTML = '';

        const autoOpt = document.createElement('option');
        autoOpt.value = '';
        autoOpt.textContent = 'Auto (route by severity)';
        autoOpt.selected = true;
        select.appendChild(autoOpt);

        (data.configured || []).forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            select.appendChild(opt);
        });

        (data.available || []).filter(n => !(data.configured || []).includes(n)).forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name + ' (not configured)';
            opt.disabled = true;
            select.appendChild(opt);
        });
    } catch (e) { console.error('Failed to load models:', e); }
}

// Show how many findings will be repaired vs total
function renderRepairHint(totalCount) {
    const CAP = 10; // mirrors MAX_REPAIR_ISSUES default
    const hint = document.querySelector('.repair-hint');
    if (!hint) return;
    const nonSecret = currentFindings.filter(f => f.type !== 'SECRET').length;
    const willRepair = Math.min(nonSecret, CAP);
    if (nonSecret > CAP) {
        hint.textContent = `Top ${willRepair} of ${nonSecret} findings will be repaired (secrets excluded, sorted by severity)`;
        hint.style.color = 'var(--warning)';
    } else {
        hint.textContent = `${willRepair} finding${willRepair !== 1 ? 's' : ''} queued for repair`;
        hint.style.color = 'var(--muted)';
    }
}

// ── Repair ────────────────────────────────────────────────────────

async function runRepair() {
    const btn = document.getElementById('repairBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Repairing...';


    // Reset verification state from any previous run

    hide('verificationResults');

    // Hide previous results while re-running
    hide('repairResults');


    const provider = document.getElementById('providerSelect').value || null;

    try {
        const res = await fetch(`/api/repair/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: provider }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Repair failed');

        renderRepairResults(data);
        show('repairResults');

        setStatus(`Repair complete: ${data.repaired_count} patches applied via ${data.provider_used}. Now run verification ↓`, 'success');

        // Reveal Step 5 automatically after a successful repair
        show('verificationSection');
        document.getElementById('verificationSection').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (e) {
        setStatus('Repair failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Repair Findings';
    }
}

function renderRepairResults(data) {
    const summaryEl = document.getElementById('repairSummary');
    const tu = data.token_usage || {};
    const cost = tu.total_cost_usd;
    const costBadge = cost > 0
        ? `<span class="badge total">$${cost.toFixed(6)}</span>`
        : `<span class="badge total">Free (local)</span>`;

    summaryEl.innerHTML = `
        <span class="badge total">${(data.patches || []).length} Patches</span>
        <span class="badge high">${data.repaired_count || 0} Applied</span>
        <span class="badge medium">${tu.total_tokens || 0} Tokens</span>
        <span class="badge low">${tu.remaining || 0} Remaining</span>
        ${costBadge}
        <span class="badge">${data.provider_used || '?'}</span>
    `;

    const listEl = document.getElementById('patchList');
    const patches = data.patches || [];
    if (!patches.length) {
        listEl.innerHTML = '<p style="color:var(--muted)">No patches generated.</p>';
        return;
    }

    listEl.innerHTML = patches.map((p, i) => `
        <div class="patch-card ${p.applied ? 'patch-applied' : p.error ? 'patch-error' : 'patch-noop'}">
            <div class="patch-header">
                <strong>#${i + 1}</strong>
                <span class="patch-status">${p.applied ? '✅ Applied' : p.error ? '❌ ' + escHtml(p.error) : '⏭ No change'}</span>
            </div>
            <p class="patch-desc">${escHtml(p.description)}</p>
            ${p.unified_diff ? '<details><summary>Show diff</summary><pre class="diff">' + escHtml(p.unified_diff) + '</pre></details>' : ''}
        </div>
    `).join('');
}


// --- Verification ---
async function runVerification() {
    const btn = document.getElementById('verifyBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Re-running analysis...';
    setStatus('Running post-repair analysis...', 'info');

    try {
        const res = await fetch(`/api/verify/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const data = await res.json();
        if (!res.ok) {
          const detail = data.detail;
          const msg = typeof detail === 'string' ? detail : JSON.stringify(detail);
          throw new Error(msg || 'Verification failed');
        }

        renderVerificationResults(data);
        show('verificationResults');

        const improved = (data.before.total - data.after.total);
        const pct = data.before.total > 0
            ? Math.round((data.resolved / data.before.total) * 100)
            : 0;

        const msg = data.new > 0
            ? `Verification complete: ${data.resolved} resolved, ${data.new} regressions introduced.`
            : `Verification complete: ${pct}% of issues resolved (${data.resolved} fixed, ${data.remaining} remaining).`;

        setStatus(msg, data.new > 0 ? 'error' : 'success');

    } catch (e) {
        setStatus('Verification failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Verification';
    }
}

function renderVerificationResults(data) {
    // Score cards
    document.getElementById('verifyResolved').textContent = data.resolved;
    document.getElementById('verifyRemaining').textContent = data.remaining;
    document.getElementById('verifyNew').textContent = data.new;

    // Colour the "new" card red if regressions exist
    const newCard = document.getElementById('verifyNew').closest('.scorecard');
    newCard.classList.toggle('scorecard-danger', data.new > 0);

    // Before / after summary badges
    renderSummary(data.before, 'verifyBefore');
    renderSummary(data.after,  'verifyAfter');

    // Regression warning
    if (data.new > 0 && data.new_ids && data.new_ids.length) {
        document.getElementById('regressionIds').textContent = data.new_ids.join('\n');
        show('regressionWarning');
        document.getElementById('regressionWarning').classList.remove('hidden');
    } else {
        hide('regressionWarning');
    }
}

