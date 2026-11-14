"use strict";
// Staff inbox client. Lists handed-off conversations for the selected tenant,
// shows the full thread plus the evidence the assistant had, and lets staff reply.

const api = {
  tenants: () => fetch("/api/tenants").then(r => r.json()),
  list: (tenant) => fetch(`/api/inbox?tenant=${encodeURIComponent(tenant)}`).then(r => r.json()),
  detail: (cid, tenant) => fetch(`/api/inbox/${cid}?tenant=${encodeURIComponent(tenant)}`).then(r => r.json()),
  reply: (cid, tenant, staff_name, text) =>
    fetch(`/api/inbox/${cid}/reply`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant, staff_name, text })
    }).then(r => r.json()),
};

let state = { tenant: null, cid: null, poll: null };
const $ = id => document.getElementById(id);
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const REASON_LABEL = {
  customer_requested_human: "Customer asked for a human",
  insufficient_evidence: "No supporting evidence found",
  model_abstained: "Assistant abstained",
  product_not_found: "Item not in this catalog",
};

async function loadList() {
  if (!state.tenant) return;
  let items;
  try { items = await api.list(state.tenant); } catch (e) { return; }
  const list = $("list");
  if (!items.length) { list.innerHTML = `<p class="muted">No conversations need attention.</p>`; return; }
  list.innerHTML = items.map(c => `
    <div class="conv-item ${c.id === state.cid ? "active" : ""}" data-cid="${c.id}">
      <div class="name">${esc(c.customer_name)}
        <span class="badge">${c.status === "staff" ? "in progress" : "waiting"}</span></div>
      ${c.reason ? `<div class="reason">${esc(REASON_LABEL[c.reason] || c.reason)}</div>` : ""}
      <div class="preview">${esc((c.last_role === "customer" ? "" : c.last_role + ": ") + c.last_message).slice(0, 90)}</div>
    </div>`).join("");
  list.querySelectorAll(".conv-item").forEach(el =>
    el.onclick = () => openConvo(parseInt(el.dataset.cid, 10)));
}

async function openConvo(cid) {
  state.cid = cid;
  const d = await api.detail(cid, state.tenant);
  const msgs = d.messages.filter(m => m.role !== "system").map(m => {
    const who = m.role === "customer" ? esc(d.conversation.customer_name)
      : m.role === "staff" ? "Staff" : "AgriConnect";
    return `<div class="msg ${m.role}"><div class="bubble"><div class="who">${who}</div>${esc(m.text)}</div></div>`;
  }).join("");

  let evidence = "";
  if (d.assistant_evidence && d.assistant_evidence.length) {
    evidence = `<div class="evidence"><h4>What the assistant checked</h4>` +
      d.assistant_evidence.map(s =>
        `<div class="src"><b>${esc(s.title)}</b> <span class="muted">(score ${s.score ?? "-"})</span>` +
        (s.text ? `<div class="muted">${esc(s.text).slice(0, 180)}…</div>` : "") + `</div>`).join("") +
      `</div>`;
  }
  const reason = d.handoff_reason ? `<div class="reason" style="margin-bottom:8px">Reason: ${esc(REASON_LABEL[d.handoff_reason] || d.handoff_reason)}</div>` : "";

  $("detail").innerHTML = `
    <div class="row" style="justify-content:space-between">
      <h2 style="margin:0">${esc(d.conversation.customer_name)}</h2>
      <span class="badge">${esc(d.conversation.status)}</span>
    </div>
    ${reason}
    <div id="thread" style="max-height:44vh;overflow-y:auto;margin-top:10px">${msgs}</div>
    ${evidence}
    <div class="row" style="margin-top:10px">
      <input class="text" id="reply" placeholder="Reply to the customer as staff…" />
      <button class="btn" id="replyBtn">Send as staff</button>
    </div>`;
  $("replyBtn").onclick = sendReply;
  $("reply").addEventListener("keydown", e => { if (e.key === "Enter") sendReply(); });
  const t = $("thread"); t.scrollTop = t.scrollHeight;
}

async function sendReply() {
  const input = $("reply");
  const text = input.value.trim();
  if (!text || !state.cid) return;
  input.value = "";
  await api.reply(state.cid, state.tenant, $("staffName").value.trim() || "Staff", text);
  await openConvo(state.cid);
  await loadList();
}

async function init() {
  const sel = $("tenant");
  const tenants = await api.tenants();
  sel.innerHTML = tenants.map(t => `<option value="${esc(t.id)}">${esc(t.name)}</option>`).join("");
  state.tenant = sel.value;
  sel.onchange = () => { state.tenant = sel.value; state.cid = null;
    $("detail").innerHTML = `<p class="muted">Select a conversation to view it.</p>`; loadList(); };
  await loadList();
  if (state.poll) clearInterval(state.poll);
  state.poll = setInterval(loadList, 3000);
}

init();
