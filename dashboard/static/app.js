const charts = {};
let currentPage = 1;
const rowsPerPage = 10;
let allRuns = [];

// Helpers
const n = v => (v === null || v === undefined || v === "") ? "-" : v;
const pill = (cls, text, title = "") => `<span class="pill ${cls}" title="${title}">${text}</span>`;
const link = url => url ? `<a href="${url}" target="_blank" rel="noopener">Open</a>` : "-";

function getBadValueClass(val) {
  if (val === null || val === undefined || val === '-') return 'val-neutral';
  return Number(val) > 0 ? 'val-bad' : 'val-good';
}
function getGoodValueClass(val) {
  if (val === null || val === undefined || val === '-') return 'val-neutral';
  const num = Number(val);
  if (num >= 80) return 'val-good';
  if (num >= 50) return 'val-warn';
  return 'val-bad';
}
function getDupValueClass(val) {
  if (val === null || val === undefined || val === '-') return 'val-neutral';
  const num = Number(val);
  if (num > 5) return 'val-bad';
  if (num > 1) return 'val-warn';
  return 'val-good';
}
function renderRating(val) {
  if (!val) return '-';
  return val.split('/').map(v => `<span class="rating-${v}">${v}</span>`).join('/');
}

function renderMetricsCells(m) {
  const bugs = n(m.bugs);
  const vulns = n(m.vulnerabilities);
  const smells = n(m.code_smells);
  const cov = n(m.coverage);
  const dup = n(m.duplicated_lines_density);
  const funcRate = m.func_pass_rate !== undefined ? Math.round(m.func_pass_rate * 100) : '-';
  
  let instability = "-";
  if (m.dep_avg_instability !== null && m.dep_avg_instability !== undefined) {
    instability = m.dep_avg_instability.toFixed(2);
  }
  
  const ratings = [m.reliability_rating, m.security_rating, m.sqale_rating].filter(Boolean).join('/');

  return `
    <td class="${getBadValueClass(bugs)}">${bugs}</td>
    <td class="${getBadValueClass(vulns)}">${vulns}</td>
    <td class="${getBadValueClass(smells)}">${smells}</td>
    <td class="${getGoodValueClass(cov)}">${cov}</td>
    <td class="${getDupValueClass(dup)}">${dup}</td>
    <td>${n(m.ncloc)}</td>
    <td>${n(m.sqale_index)}</td>
    <td class="${getGoodValueClass(funcRate)}">${funcRate === '-' ? '-' : funcRate + '%'}</td>
    <td>${n(m.dep_modules)}</td>
    <td class="${getBadValueClass(m.dep_cycles)}">${n(m.dep_cycles)}</td>
    <td class="${getBadValueClass(m.dep_orphans)}">${n(m.dep_orphans)}</td>
    <td>${instability}</td>
    <td>${renderRating(ratings)}</td>
    <td>${link(m.sonar_url)}</td>
  `;
}

function renderRow(r) {
  const statusTitle = (r.error || r.step || "").replaceAll('"', "'");
  return `<tr>
    <td>${r.id}</td>
    <td style="text-align:left">${r.task_name}</td>
    <td>${pill(r.status, r.status, statusTitle)}</td>
    <td><strong>${r.provider}</strong> / ${r.model}</td> <!-- เพิ่มคอลัมน์แสดง AI Provider/Model -->
    ${renderMetricsCells(r.metrics || {})}
  </tr>`;
}

// Pagination Logic
function renderTable() {
  const totalPages = Math.ceil(allRuns.length / rowsPerPage);
  const start = (currentPage - 1) * rowsPerPage;
  const end = start + rowsPerPage;
  const paginatedRuns = allRuns.slice(start, end);

  document.getElementById("rows").innerHTML = paginatedRuns.map(renderRow).join("");
  document.getElementById("page-info").textContent = `Page ${currentPage} of ${totalPages || 1}`;
  
  document.getElementById("prev-btn").disabled = currentPage === 1;
  document.getElementById("next-btn").disabled = currentPage >= totalPages;
}

// Charts
function draw(id, type, labels, datasets, title) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), { 
    type, 
    data: { labels, datasets },
    options: { 
      plugins: { title: { display: true, text: title } }, 
      responsive: true, 
      scales: type === 'bar' ? { y: { beginAtZero: true } } : {} 
    } 
  });
}

// Main Load
async function load() {
  try {
    const res = await fetch("/api/runs");
    if (!res.ok) throw new Error("Failed to fetch runs");
    allRuns = await res.json();
    
    // Stats Cards
    const done = allRuns.filter(r => r.status === "done");
    const avg = k => done.length ? (done.reduce((a, r) => a + Number(r.metrics[k] || 0), 0) / done.length).toFixed(1) : "-";
    const rate = fn => done.length ? Math.round(100 * done.filter(fn).length / done.length) + "%" : "-";
    
    document.getElementById("cards").innerHTML = [
      ["Total runs", allRuns.length], 
      ["Gate pass rate", rate(r => r.quality_gate === "OK")], 
      ["Avg bugs", avg("bugs")],
      ["Avg vulnerabilities", avg("vulnerabilities")], 
      ["Avg code smells", avg("code_smells")], 
      ["Avg coverage %", avg("coverage")],
      ["All checks pass", rate(r => r.tests_passed === 1)]
    ].map(([l, v]) => `<div class="card"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");

    // Render Table with Pagination
    renderTable();

    // Charts
    const ordered = [...done].reverse();
    const labels = ordered.map(r => `#${r.id} ${r.model}`);
    
    draw("issues", "bar", labels, [
      { label: "Bugs", data: ordered.map(r => +r.metrics.bugs || 0), backgroundColor: "#d85a30" },
      { label: "Vulnerabilities", data: ordered.map(r => +r.metrics.vulnerabilities || 0), backgroundColor: "#ba7517" },
      { label: "Code smells", data: ordered.map(r => +r.metrics.code_smells || 0), backgroundColor: "#378add" },
    ], "Issues per run (Lower is better)");

    draw("cov", "line", labels, [
      { label: "Coverage % (Higher is better)", data: ordered.map(r => +r.metrics.coverage || 0), borderColor: "#1d9e75", tension: 0.3 },
      { label: "Duplication % (Lower is better)", data: ordered.map(r => +r.metrics.duplicated_lines_density || 0), borderColor: "#7f77dd", tension: 0.3 },
    ], "Coverage & duplication over time");

  } catch (err) {
    console.error("Load error:", err);
  } finally {
    setTimeout(load, 5000);
  }
}

// Start Run
async function startRun() {
  const taskSelect = document.getElementById("task");
  const selectedTask = taskSelect.value;
  if (!selectedTask) {
    alert("Please select a task first.");
    return;
  }

  const body = { task_file: selectedTask };
  const p = document.getElementById("provider").value;
  if (p) body.provider = p;
  
  try {
    const res = await fetch("/api/runs", { 
      method: "POST", 
      headers: { "Content-Type": "application/json" }, 
      body: JSON.stringify(body) 
    });
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Failed to start run");
    }
    await load();
  } catch (err) {
    console.error(err);
    alert("Error starting run: " + err.message);
  }
}

// Init
document.getElementById("run").addEventListener("click", startRun);
document.getElementById("refresh").addEventListener("click", load);

document.getElementById("prev-btn").addEventListener("click", () => {
  if (currentPage > 1) { currentPage--; renderTable(); }
});
document.getElementById("next-btn").addEventListener("click", () => {
  const totalPages = Math.ceil(allRuns.length / rowsPerPage);
  if (currentPage < totalPages) { currentPage++; renderTable(); }
});

// Load Tasks into Dropdown
async function loadTasks() {
  try {
    const res = await fetch("/api/tasks");
    if (res.ok) {
      const tasks = await res.json();
      const taskSelect = document.getElementById("task");
      taskSelect.innerHTML = '<option value="">-- Select a Task --</option>';
      
      tasks.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t.file; 
        opt.textContent = t.name;
        taskSelect.appendChild(opt);
      });
    }
  } catch(e) { 
    console.error("Error loading tasks:", e); 
  }
}

// ==========================================
// แก้ไขส่วนการเรียกใช้ด้านล่างสุด (Top-level await)
// ==========================================
try {
  await loadTasks();
  await load();
} catch (err) {
  console.error("Initialization failed:", err);
}