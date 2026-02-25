let sid = null;
let selectedFiles = [];
let selectedAnalyzers = [];

/* -------------------------------
   Utility helpers
-------------------------------- */

function el(id) {
  return document.getElementById(id);
}

function showStatus(msg) {
  el("status").innerText = msg;
}

/* -------------------------------
   Session Creation
-------------------------------- */

async function createSession() {
  const res = await fetch("/api/session", { method: "POST" });
  const data = await res.json();
  sid = data.session_id;
  showStatus("Session created: " + sid);
  loadAnalyzers();
}

/* -------------------------------
   Upload ZIP
-------------------------------- */

async function uploadZip() {
  if (!sid) await createSession();

  const fileInput = el("zipFile");
  if (!fileInput.files.length) {
    alert("Select a zip file first.");
    return;
  }

  const form = new FormData();
  form.append("file", fileInput.files[0]);

  await fetch(`/api/session/${sid}/upload`, {
    method: "POST",
    body: form
  });

  await loadFiles();
}

/* -------------------------------
   Clone GitHub
-------------------------------- */

async function cloneRepo() {
  if (!sid) await createSession();

  const url = el("gitUrl").value;
  if (!url) {
    alert("Enter Git URL");
    return;
  }

  await fetch(`/api/session/${sid}/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });

  await loadFiles();
}

/* -------------------------------
   Load Files from workspace_raw
-------------------------------- */

async function loadFiles() {
  const res = await fetch(`/api/session/${sid}/files`);
  const files = await res.json();

  const container = el("fileList");
  container.innerHTML = "";

  selectedFiles = [];

  files.forEach(f => {
    const div = document.createElement("div");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;

    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedFiles.push(f);
      } else {
        selectedFiles = selectedFiles.filter(x => x !== f);
      }
    });

    selectedFiles.push(f);

    div.appendChild(checkbox);
    div.appendChild(document.createTextNode(" " + f));
    container.appendChild(div);
  });

  showStatus(files.length + " files loaded.");
}

/* -------------------------------
   Load Available Analyzers
-------------------------------- */

async function loadAnalyzers() {
  const res = await fetch("/api/analyzers");
  const tools = await res.json();

  const container = el("analyzerList");
  container.innerHTML = "";

  selectedAnalyzers = [];

  tools.forEach(t => {
    const div = document.createElement("div");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;

    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedAnalyzers.push(t);
      } else {
        selectedAnalyzers = selectedAnalyzers.filter(x => x !== t);
      }
    });

    selectedAnalyzers.push(t);

    div.appendChild(checkbox);
    div.appendChild(document.createTextNode(" " + t));
    container.appendChild(div);
  });
}

/* -------------------------------
   Apply Selection
-------------------------------- */

async function applySelection() {
  if (!selectedFiles.length) {
    alert("No files selected.");
    return;
  }

  await fetch(`/api/session/${sid}/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_files: selectedFiles })
  });
}

/* -------------------------------
   Analyse
-------------------------------- */

async function analyse() {
  showStatus("Applying selection...");
  await applySelection();

  showStatus("Running analysis...");
  await fetch(`/api/session/${sid}/analyse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analyzers: selectedAnalyzers })
  });

  await refreshReport();
}

/* -------------------------------
   Repair
-------------------------------- */

async function repair() {
  showStatus("Running repair...");

  await fetch(`/api/session/${sid}/repair`, {
    method: "POST"
  });

  await refreshReport();
}

/* -------------------------------
   Refresh Report + Verification
-------------------------------- */

async function refreshReport() {
  const report = await fetch(`/api/session/${sid}/report`);
  const reportData = await report.json();

  const verify = await fetch(`/api/session/${sid}/verification`);
  const verifyData = await verify.json();

  el("reportOutput").innerText =
    JSON.stringify(reportData, null, 2);

  el("verificationOutput").innerText =
    JSON.stringify(verifyData, null, 2);

  showStatus("Done.");
}

/* -------------------------------
   Auto-init
-------------------------------- */

//window.onload = () => {
//  createSession();
//};
