/**
 * GCP Knowledge Catalog Agent - Frontend Client Logic
 */

let currentAssets = [];
let selectedAssetForSchema = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  refreshCatalogData();
  updateTagTemplateFields();
});

// Switch Navigation Tabs
function switchTab(tabId) {
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));

  const navBtn = document.getElementById(`nav-${tabId}`);
  const pane = document.getElementById(`pane-${tabId}`);

  if (navBtn) navBtn.classList.add("active");
  if (pane) pane.classList.add("active");

  const titles = {
    chat: { title: "Live Agent Chat", desc: "Interact with the GCP Knowledge Catalog AI Agent deployed for Gemini Enterprise." },
    explorer: { title: "Knowledge Catalog Explorer", desc: "Search, filter, and discover BigQuery datasets, tables, and Dataplex assets." },
    schema: { title: "Metadata & Schema Inspector", desc: "View detailed column types, descriptions, and resource hierarchies." },
    tags: { title: "Tag Management Studio", desc: "Attach and update governance, compliance, and classification tag templates." },
    mcp: { title: "Remote MCP Server Hub", desc: "Model Context Protocol (MCP) tool testing, live RPC execution, and SSE endpoints." }
  };

  if (titles[tabId]) {
    document.getElementById("page-title").textContent = titles[tabId].title;
    document.getElementById("page-description").textContent = titles[tabId].desc;
  }
}

// Fetch and Refresh Catalog Data
async function refreshCatalogData() {
  showToast("Syncing with GCP Knowledge Catalog...");
  try {
    const res = await fetch("/api/catalog/search?query=");
    const data = await res.json();
    if (data && data.results) {
      currentAssets = data.results;
      renderAssetCards(currentAssets);
      populateAssetSelects(currentAssets);
      loadActiveTags();
      showToast("Catalog synced successfully!", "success");
    }
  } catch (err) {
    console.error("Error syncing catalog:", err);
    showToast("Using local catalog cache.", "warning");
  }
}

// Render Asset Cards in Explorer Tab
function renderAssetCards(assets) {
  const container = document.getElementById("asset-results-container");
  if (!container) return;

  if (assets.length === 0) {
    container.innerHTML = `<div class="text-muted p-4">No data assets match the search criteria.</div>`;
    return;
  }

  container.innerHTML = assets.map(asset => {
    const typeBadgeClass = asset.asset_type === "TABLE" ? "badge-table" : (asset.asset_type === "DATASET" ? "badge-dataset" : "badge-stream");
    return `
      <div class="asset-card">
        <div class="asset-card-header">
          <div class="asset-title-group">
            <h3>${escapeHtml(asset.display_name)}</h3>
            <div class="fqn-code">${escapeHtml(asset.fully_qualified_name || asset.entry_name)}</div>
          </div>
          <span class="badge ${typeBadgeClass}">${escapeHtml(asset.asset_type)}</span>
        </div>
        <p class="asset-desc">${escapeHtml(asset.description)}</p>
        <div class="asset-card-actions">
          <button class="btn btn-sm btn-secondary" onclick="inspectAsset('${escapeHtml(asset.entry_name)}')">View Schema</button>
          <button class="btn btn-sm btn-outline" onclick="openTagManagerFor('${escapeHtml(asset.entry_name)}')">Manage Tags</button>
        </div>
      </div>
    `;
  }).join("");
}

// Filter Explorer
function handleExplorerSearch() {
  const q = document.getElementById("explorer-search-input").value.toLowerCase();
  const typeFilter = document.getElementById("filter-asset-type").value;
  const sysFilter = document.getElementById("filter-system").value;

  const filtered = currentAssets.filter(a => {
    const matchesQ = !q || a.display_name.toLowerCase().includes(q) || (a.description && a.description.toLowerCase().includes(q)) || (a.fully_qualified_name && a.fully_qualified_name.toLowerCase().includes(q));
    const matchesType = typeFilter === "ALL" || a.asset_type === typeFilter;
    const matchesSys = sysFilter === "ALL" || (a.system && a.system === sysFilter);
    return matchesQ && matchesType && matchesSys;
  });

  renderAssetCards(filtered);
}

// Populate Asset Selectors
function populateAssetSelects(assets) {
  const schemaSelect = document.getElementById("schema-asset-select");
  const tagAssetSelect = document.getElementById("tag-target-asset");

  const optionsHtml = assets.map(a => `<option value="${escapeHtml(a.entry_name)}">${escapeHtml(a.display_name)} (${escapeHtml(a.asset_type)})</option>`).join("");

  if (schemaSelect) {
    schemaSelect.innerHTML = optionsHtml;
    loadAssetSchema();
  }
  if (tagAssetSelect) {
    tagAssetSelect.innerHTML = optionsHtml;
  }
}

// Inspect Asset Schema
function inspectAsset(entryName) {
  switchTab("schema");
  const schemaSelect = document.getElementById("schema-asset-select");
  if (schemaSelect) {
    schemaSelect.value = entryName;
    loadAssetSchema();
  }
}

async function loadAssetSchema() {
  const schemaSelect = document.getElementById("schema-asset-select");
  if (!schemaSelect || !schemaSelect.value) return;

  const entryName = schemaSelect.value;
  try {
    const res = await fetch(`/api/catalog/entry?name=${encodeURIComponent(entryName)}`);
    const data = await res.json();

    const summaryBox = document.getElementById("asset-meta-summary-box");
    const tbody = document.getElementById("schema-columns-tbody");
    const countBadge = document.getElementById("schema-column-count");

    if (data.status === "success") {
      summaryBox.innerHTML = `
        <div class="meta-box"><div class="lbl">Asset Type</div><div class="val">${escapeHtml(data.asset_type || 'TABLE')}</div></div>
        <div class="meta-box"><div class="lbl">System</div><div class="val">${escapeHtml(data.system || 'BIGQUERY')}</div></div>
        <div class="meta-box"><div class="lbl">Full Path</div><div class="val text-sm text-accent">${escapeHtml(data.fully_qualified_name || data.entry_name)}</div></div>
      `;

      const cols = (data.schema && data.schema.columns) || [];
      countBadge.textContent = `${cols.length} Columns`;

      if (cols.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-muted">No explicit columns defined for this asset container.</td></tr>`;
      } else {
        tbody.innerHTML = cols.map(c => `
          <tr>
            <td><strong>${escapeHtml(c.name)}</strong></td>
            <td><span class="col-type-badge">${escapeHtml(c.type)}</span></td>
            <td>${escapeHtml(c.mode || 'NULLABLE')}</td>
            <td>${escapeHtml(c.description || '—')}</td>
            <td><span class="badge badge-accent">Governed</span></td>
          </tr>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Error loading schema:", err);
  }
}

// Tag Management Logic
function openTagManagerFor(entryName) {
  switchTab("tags");
  const select = document.getElementById("tag-target-asset");
  if (select) select.value = entryName;
}

function updateTagTemplateFields() {
  const tpl = document.getElementById("tag-template-name").value;
  const container = document.getElementById("dynamic-tag-fields-container");
  if (!container) return;

  if (tpl === "Data Governance") {
    container.innerHTML = `
      <div class="form-group">
        <label>Classification</label>
        <select id="field-classification" class="form-control">
          <option value="Public">Public</option>
          <option value="Internal">Internal</option>
          <option value="Confidential" selected>Confidential</option>
          <option value="Restricted">Restricted</option>
        </select>
      </div>
      <div class="dynamic-field-row">
        <div class="form-group">
          <label>Data Owner Email</label>
          <input type="email" id="field-data_owner" class="form-control" value="governance-team@example.com">
        </div>
        <div class="form-group">
          <label>Retention Days</label>
          <input type="number" id="field-retention_days" class="form-control" value="365">
        </div>
      </div>
    `;
  } else if (tpl === "Privacy Compliance") {
    container.innerHTML = `
      <div class="form-group">
        <label>PII Category</label>
        <input type="text" id="field-pii_type" class="form-control" value="Direct Identifier (Email, Phone)">
      </div>
      <div class="dynamic-field-row">
        <div class="form-group">
          <label>GDPR Regulated</label>
          <select id="field-gdpr_regulated" class="form-control">
            <option value="true" selected>Yes</option>
            <option value="false">No</option>
          </select>
        </div>
        <div class="form-group">
          <label>Compliance Officer</label>
          <input type="email" id="field-compliance_contact" class="form-control" value="privacy-officer@example.com">
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div class="form-group">
        <label>Model Readiness</label>
        <select id="field-model_readiness" class="form-control">
          <option value="Production-Ready" selected>Production-Ready</option>
          <option value="Experimental">Experimental</option>
        </select>
      </div>
      <div class="form-group">
        <label>Pipeline Owner</label>
        <input type="email" id="field-pipeline_owner" class="form-control" value="mlops@example.com">
      </div>
    `;
  }
}

async function handleTagFormSubmit(e) {
  e.preventDefault();
  const entryName = document.getElementById("tag-target-asset").value;
  const tplName = document.getElementById("tag-template-name").value;
  const col = document.getElementById("tag-target-column").value;

  const fields = {};
  if (tplName === "Data Governance") {
    fields.classification = document.getElementById("field-classification").value;
    fields.data_owner = document.getElementById("field-data_owner").value;
    fields.retention_days = parseInt(document.getElementById("field-retention_days").value, 10);
  } else if (tplName === "Privacy Compliance") {
    fields.pii_type = document.getElementById("field-pii_type").value;
    fields.gdpr_regulated = document.getElementById("field-gdpr_regulated").value === "true";
    fields.compliance_contact = document.getElementById("field-compliance_contact").value;
  } else {
    fields.model_readiness = document.getElementById("field-model_readiness").value;
    fields.pipeline_owner = document.getElementById("field-pipeline_owner").value;
  }

  showToast("Applying tag to Knowledge Catalog...");
  try {
    const res = await fetch("/api/catalog/tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entry_name: entryName,
        tag_template_display_name: tplName,
        tag_fields: fields,
        column: col
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(data.message, "success");
      loadActiveTags();
    } else {
      showToast("Error updating tag: " + data.message, "danger");
    }
  } catch (err) {
    console.error("Tag update error:", err);
    showToast("Failed to attach tag.", "danger");
  }
}

async function loadActiveTags() {
  const container = document.getElementById("active-tags-container");
  if (!container) return;

  try {
    const res = await fetch("/api/catalog/search?query=");
    const data = await res.json();
    const assets = data.results || [];

    let allTagsHtml = "";
    for (const a of assets) {
      const tagRes = await fetch(`/api/catalog/tags?name=${encodeURIComponent(a.entry_name)}`);
      const tagData = await tagRes.json();
      const tags = tagData.tags || [];

      for (const t of tags) {
        const fieldsEntries = Object.entries(t.fields || {}).map(([k, v]) => `
          <div class="tag-field-val"><strong>${escapeHtml(k)}:</strong> ${escapeHtml(String(v))}</div>
        `).join("");

        allTagsHtml += `
          <div class="governance-tag-item">
            <div class="tag-item-header">
              <h4>🏷️ ${escapeHtml(t.template_display_name || 'Tag Template')}</h4>
              <span class="badge badge-accent">${escapeHtml(a.display_name)} (${escapeHtml(t.column || 'Asset Level')})</span>
            </div>
            <div class="tag-fields-grid">
              ${fieldsEntries}
            </div>
          </div>
        `;
      }
    }
    container.innerHTML = allTagsHtml || `<div class="text-muted">No governance tags attached yet.</div>`;
  } catch (err) {
    console.error("Error loading tags list:", err);
  }
}

// Remote MCP Testing
async function runMcpTester(toolName, params) {
  const consoleStatus = document.getElementById("mcp-console-status");
  const jsonOutput = document.getElementById("mcp-json-output");

  consoleStatus.textContent = "Executing...";
  consoleStatus.className = "badge badge-accent";
  jsonOutput.textContent = `// Sending MCP JSON-RPC call for tool '${toolName}'...\n`;

  try {
    const res = await fetch("/api/catalog/mcp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, parameters: params })
    });
    const data = await res.json();
    consoleStatus.textContent = "Success (200 OK)";
    consoleStatus.className = "badge text-success";
    jsonOutput.textContent = JSON.stringify(data, null, 2);
    showToast(`MCP Tool '${toolName}' executed!`, "success");
  } catch (err) {
    consoleStatus.textContent = "Error";
    consoleStatus.className = "badge text-danger";
    jsonOutput.textContent = `// Error executing MCP tool:\n` + err.message;
  }
}

// Live Agent Chat Interface
function sendPrompt(text) {
  const input = document.getElementById("chat-input-text");
  if (input) {
    input.value = text;
    switchTab("chat");
    document.getElementById("chat-form").dispatchEvent(new Event("submit"));
  }
}

function handleTextareaKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("chat-form").dispatchEvent(new Event("submit"));
  }
}

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input-text");
  const msg = input.value.trim();
  if (!msg) return;

  appendChatMessage("user", msg);
  input.value = "";

  const thinkingId = appendThinkingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: msg })
    });
    const data = await res.json();
    removeThinkingIndicator(thinkingId);

    const reply = data.response || data.message || "I've processed your request regarding the Knowledge Catalog.";
    appendChatMessage("agent", reply);
  } catch (err) {
    console.error("Chat error:", err);
    removeThinkingIndicator(thinkingId);
    appendChatMessage("agent", "Sorry, I encountered an error communicating with the agent backend. Please check your network or server logs.");
  }
}

function appendChatMessage(sender, text) {
  const box = document.getElementById("chat-messages-box");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}-message`;

  const isAgent = sender === "agent";
  const avatar = isAgent ? "✨" : "👤";
  const senderName = isAgent ? "Knowledge Catalog Agent" : "You";

  msgDiv.innerHTML = `
    <div class="avatar ${isAgent ? 'agent-avatar' : 'user-avatar'}">${avatar}</div>
    <div class="message-content">
      <div class="message-header">
        <strong>${senderName}</strong>
        <span class="timestamp">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
      </div>
      <div class="message-body">${formatMarkdown(text)}</div>
    </div>
  `;

  box.appendChild(msgDiv);
  box.scrollTop = box.scrollHeight;
}

function appendThinkingIndicator() {
  const box = document.getElementById("chat-messages-box");
  const id = "thinking-" + Date.now();
  const msgDiv = document.createElement("div");
  msgDiv.id = id;
  msgDiv.className = "message system-message";
  msgDiv.innerHTML = `
    <div class="avatar agent-avatar">✨</div>
    <div class="message-content">
      <div class="message-body text-muted">Thinking & querying Knowledge Catalog API...</div>
    </div>
  `;
  box.appendChild(msgDiv);
  box.scrollTop = box.scrollHeight;
  return id;
}

function removeThinkingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// Simple Markdown formatting helper
function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Inline Code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Paragraphs
  html = html.split("\n\n").map(p => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
  return html;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
