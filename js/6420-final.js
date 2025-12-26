// js/6420-final.js
// Hamburger toggle (ARIA-aware). No inline handlers.
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.site-nav');
  const list = nav ? nav.querySelector('ul') : null;

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));

      // Support both nav-level and ul-level toggles
      nav.classList.toggle('nav-open');
      if (list) list.classList.toggle('open');
    });
  }
});

// Responsive image map for sitemap (percent-based hotspots)
(function () {
  function applyPercentMap(img, map) {
    const w = img.clientWidth;
    const h = img.clientHeight;
    if (!w || !h) return;

    const areas = map.querySelectorAll('area[data-pct]');
    areas.forEach((area) => {
      const parts = area.dataset.pct.split(',').map((x) => parseFloat(x.trim()));
      if (parts.length !== 4 || parts.some((n) => Number.isNaN(n))) return;
      const coords = [
        Math.round((w * parts[0]) / 100),
        Math.round((h * parts[1]) / 100),
        Math.round((w * parts[2]) / 100),
        Math.round((h * parts[3]) / 100),
      ];
      area.setAttribute('coords', coords.join(','));
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const img = document.querySelector('img[usemap="#sitemapmap"]');
    const map = document.getElementById('sitemapmap');
    if (!img || !map) return;

    let t = null;
    const update = () => applyPercentMap(img, map);

    if (img.complete) update();
    else img.addEventListener('load', update);

    window.addEventListener('resize', () => {
      window.clearTimeout(t);
      t = window.setTimeout(update, 120);
    });
  });
})();

// Accordion toggles
document.addEventListener('DOMContentLoaded', function () {
  const accordions = document.querySelectorAll('.accordion-header');
  accordions.forEach((btn) => {
    const panelId = btn.getAttribute('aria-controls');
    const panel = document.getElementById(panelId);
    if (!panel) return;

    btn.addEventListener('click', () => {
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!expanded));
      panel.classList.toggle('open', !expanded);
    });
  });
});

// Court documents dashboard (CSV-driven)
document.addEventListener('DOMContentLoaded', () => {
  const tableEl = document.getElementById('court-doc-table');
  if (!tableEl) return;

  const filters = {
    case: document.getElementById('filter-case'),
    type: document.getElementById('filter-type'),
    confidence: document.getElementById('filter-confidence'),
    search: document.getElementById('filter-search'),
  };

  const statEls = {
    totalDocs: document.getElementById('stat-total-docs'),
    totalCases: document.getElementById('stat-total-cases'),
    totalTypes: document.getElementById('stat-total-types'),
  };

  const auditList = document.getElementById('audit-list');
  let rows = [];

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    if (!lines.length) return [];
    const headers = lines[0].split(',');
    return lines.slice(1).map((line) => {
      const cells = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i += 1) {
        const char = line[i];
        if (char === '"' && line[i + 1] === '"') {
          current += '"';
          i += 1;
          continue;
        }
        if (char === '"') {
          inQuotes = !inQuotes;
          continue;
        }
        if (char === ',' && !inQuotes) {
          cells.push(current);
          current = '';
        } else {
          current += char;
        }
      }
      cells.push(current);
      const row = {};
      headers.forEach((h, idx) => {
        row[h] = cells[idx] || '';
      });
      return row;
    });
  }

  function renderTable(data) {
    const body = tableEl.querySelector('tbody');
    body.innerHTML = '';
    data.forEach((row) => {
      const tr = document.createElement('tr');
      [
        row.case_number,
        row.document_type,
        row.filed_date,
        row.party_petitioner,
        row.party_respondent,
        row.party_guardian,
        row.event_type_code,
        row.judge,
        row.low_confidence,
        row.notes,
        row.file_name,
      ].forEach((val) => {
        const td = document.createElement('td');
        td.textContent = val || '';
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  }

  function applyFilters() {
    const caseVal = filters.case.value;
    const typeVal = filters.type.value;
    const confVal = filters.confidence.value;
    const searchVal = filters.search.value.toLowerCase();

    const filtered = rows.filter((r) => {
      if (caseVal && r.case_number !== caseVal) return false;
      if (typeVal && r.document_type !== typeVal) return false;
      if (confVal === 'low' && r.low_confidence !== 'yes') return false;
      if (confVal === 'high' && r.low_confidence === 'yes') return false;
      if (searchVal) {
        const hay = `${r.case_number} ${r.document_type} ${r.notes}`.toLowerCase();
        if (!hay.includes(searchVal)) return false;
      }
      return true;
    });
    renderTable(filtered);
  }

  function populateFilters(data) {
    const cases = Array.from(new Set(data.map((r) => r.case_number))).sort();
    const types = Array.from(new Set(data.map((r) => r.document_type))).sort();

    cases.forEach((c) => {
      if (!c) return;
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      filters.case.appendChild(opt);
    });

    types.forEach((t) => {
      if (!t) return;
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      filters.type.appendChild(opt);
    });
  }

  function renderDatasetSummary(data) {
    const totalEvents = data.length;
    const uniqueCases = new Set(data.map((r) => r.case_number)).size;
    const uniqueSources = new Set(data.map((r) => r.source_view)).size;

    let statsDiv = document.getElementById('data-stats');
    if (!statsDiv) {
      statsDiv = document.createElement('div');
      statsDiv.id = 'data-stats';
      statsDiv.className = 'card';

      const filtersSection = document.querySelector('.filters');
      if (filtersSection && filtersSection.parentElement) {
        filtersSection.parentElement.insertBefore(statsDiv, filtersSection);
      } else {
        document.body.insertBefore(statsDiv, document.body.firstChild);
      }
    }

    statsDiv.innerHTML = `
      <h3>Dataset Summary</h3>
      <div class="stats-grid">
        <div class="stat">
          <span class="stat-value">${totalEvents}</span>
          <span class="stat-label">Total Events</span>
        </div>
        <div class="stat">
          <span class="stat-value">${uniqueCases}</span>
          <span class="stat-label">Cases</span>
        </div>
        <div class="stat">
          <span class="stat-value">${uniqueSources}</span>
          <span class="stat-label">Data Sources</span>
        </div>
      </div>
    `;
  }

  function updateStats(data) {
    const cases = new Set(data.map((r) => r.case_number).filter(Boolean));
    const types = new Set(data.map((r) => r.document_type).filter(Boolean));
    if (statEls.totalDocs) statEls.totalDocs.textContent = data.length;
    if (statEls.totalCases) statEls.totalCases.textContent = cases.size;
    if (statEls.totalTypes) statEls.totalTypes.textContent = types.size;
  }

  function renderAudit(rowsAudit) {
    if (!auditList) return;
    auditList.innerHTML = '';
    if (!rowsAudit.length) {
      const li = document.createElement('li');
      li.textContent = 'No audit issues detected.';
      auditList.appendChild(li);
      return;
    }
    rowsAudit.forEach((r) => {
      const li = document.createElement('li');
      li.textContent = `${r.issue_type} - ${r.case_id} - ${r.detail} (${r.file_name || 'n/a'})`;
      auditList.appendChild(li);
    });
  }

  function updateAuditStats(auditRows) {
    const issueCountEl = document.getElementById('audit-issue-count');
    const orphanCountEl = document.getElementById('audit-orphan-count');
    const cleanCountEl = document.getElementById('audit-clean-count');
    if (!issueCountEl && !orphanCountEl && !cleanCountEl) return;

    const totalIssues = auditRows.length;
    const orphanIssues = auditRows.filter((r) => (r.issue_type || '').toLowerCase() === 'orphan_document').length;

    const parsedCases = new Set(rows.map((r) => r.case_number).filter(Boolean));
    const issueCases = new Set(auditRows.map((r) => r.case_id).filter(Boolean));
    let cleanCases = 0;
    parsedCases.forEach((cid) => {
      if (!issueCases.has(cid)) cleanCases += 1;
    });

    if (issueCountEl) issueCountEl.textContent = totalIssues;
    if (orphanCountEl) orphanCountEl.textContent = orphanIssues;
    if (cleanCountEl) cleanCountEl.textContent = cleanCases;
  }

  async function loadData() {
    try {
      const parsedRes = await fetch('data/court_docs_parsed.csv');
      if (!parsedRes.ok) throw new Error('parsed CSV not found');
      rows = parseCsv(await parsedRes.text());
      updateStats(rows);
       renderDatasetSummary(rows);
      populateFilters(rows);
      applyFilters();
    } catch (err) {
      tableEl.querySelector('tbody').innerHTML = '';
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 11;
      td.textContent = 'Parsed documents not available. Run OCR + parse steps.';
      tr.appendChild(td);
      tableEl.querySelector('tbody').appendChild(tr);
    }

    try {
      const auditRes = await fetch('data/court_docs_audit.csv');
      if (!auditRes.ok) throw new Error('audit CSV not found');
      const auditRows = parseCsv(await auditRes.text());
      renderAudit(auditRows);
      updateAuditStats(auditRows);
    } catch (err) {
      renderAudit([]);
    }
  }

  async function loadParserHealth() {
    const filesCountEl = document.getElementById('parser-files-count');
    const tableCountEl = document.getElementById('parser-table-count');
    const fallbackCountEl = document.getElementById('parser-fallback-count');
    const warningsList = document.getElementById('parser-warnings-list');
    if (!filesCountEl || !tableCountEl || !fallbackCountEl || !warningsList) return;

    try {
      const res = await fetch('data/parse_report.json');
      if (!res.ok) throw new Error('parse_report.json not found');
      const reports = await res.json();

      const totalFiles = reports.length;
      const tableMode = reports.filter((r) => String(r.strategy_used || '').toLowerCase().startsWith('table')).length;
      const fallbackMode = totalFiles - tableMode;

      filesCountEl.textContent = totalFiles;
      tableCountEl.textContent = tableMode;
      fallbackCountEl.textContent = fallbackMode;

      warningsList.innerHTML = '';
      let hasWarnings = false;
      reports.forEach((r) => {
        if (r.warnings && r.warnings.length) {
          hasWarnings = true;
          r.warnings.forEach((w) => {
            const li = document.createElement('li');
            li.className = 'audit-item warning';
            li.textContent = `[${r.filename}] ${w}`;
            warningsList.appendChild(li);
          });
        }
      });

      if (!hasWarnings) {
        const li = document.createElement('li');
        li.textContent = 'No parser warnings. System healthy.';
        warningsList.appendChild(li);
      }
    } catch (err) {
      warningsList.innerHTML = '<li>Parser report unavailable. Run parse_court_docs.py first.</li>';
    }
  }

  Object.values(filters).forEach((el) => {
    if (!el) return;
    el.addEventListener('input', applyFilters);
    el.addEventListener('change', applyFilters);
  });

  loadData();
  loadParserHealth();
});
