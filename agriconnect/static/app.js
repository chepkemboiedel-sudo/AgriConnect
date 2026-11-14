"use strict";
// Customer chat client. Server is the source of truth; we poll for new
// messages so a staff takeover appears here without a refresh.

const api = {
  tenants: () => fetch("/api/tenants").then(r => r.json()),
  health: () => fetch("/api/health").then(r => r.json()),
  newConvo: (tenant, customer_name) =>
    fetch("/api/conversations", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant, customer_name })
    }).then(r => r.json()),
  messages: (cid, tenant) =>
    fetch(`/api/conversations/${cid}/messages?tenant=${encodeURIComponent(tenant)}`).then(r => r.json()),
  send: (cid, tenant, text) =>
    fetch(`/api/conversations/${cid}/message`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant, text })
    }).then(r => r.json()),
};

let state = { tenant: null, cid: null, lastCount: 0, status: "bot", poll: null };

const $ = id => document.getElementById(id);

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function renderMessages(messages, status) {
  const chat = $("chat");
  chat.innerHTML = "";
  for (const m of messages) {
    if (m.role === "system") continue;
    const wrap = document.createElement("div");
    wrap.className = "msg " + m.role;
    const who = m.role === "customer" ? "You"
      : m.role === "staff" ? ("Staff" + (m.meta && m.meta.staff_name ? " · " + esc(m.meta.staff_name) : ""))
      : "AgriConnect";
    let sources = "";
    const meta = m.meta || {};
    if (meta.tool || (meta.sources && meta.sources.length)) {
      const chips = [];
      if (meta.tool) chips.push(`<span class="chip tool">${esc(meta.tool)}</span>`);
      (meta.sources || []).forEach(s => chips.push(`<span class="chip">${esc(s.title)}</span>`));
      if (meta.provider === "openai") chips.push(`<span class="chip">LLM</span>`);
      sources = `<div class="sources">${chips.join("")}</div>`;
    }
    wrap.innerHTML = `<div class="bubble"><div class="who">${who}</div>${esc(m.text)}${sources}</div>`;
    chat.appendChild(wrap);
  }
  chat.scrollTop = chat.scrollHeight;

  // status banner + badge
  const badge = $("statusBadge");
  badge.textContent = status === "staff" ? "staff" : status === "waiting_staff" ? "waiting for staff" : "assistant";
  const banner = $("banner");
  if (status === "waiting_staff") {
    banner.innerHTML = `<div class="banner">Handed off to a staff member — they can see this whole conversation in the inbox and will reply here.</div>`;
  } else if (status === "staff") {
    banner.innerHTML = `<div class="banner">A staff member has joined this conversation.</div>`;
  } else {
    banner.innerHTML = "";
  }
  state.status = status;
}

async function refresh() {
  if (!state.cid) return;
  try {
    const data = await api.messages(state.cid, state.tenant);
    renderMessages(data.messages, data.status);
  } catch (e) { /* ignore transient poll errors */ }
}

async function start() {
  state.tenant = $("tenant").value;
  const name = $("name").value.trim() || "Guest";
  const res = await api.newConvo(state.tenant, name);
  state.cid = res.conversation_id;
  $("startCard").classList.add("hidden");
  $("chatCard").classList.remove("hidden");
  $("who").textContent = "· " + name + " · " + $("tenant").selectedOptions[0].text;
  await refresh();
  $("input").focus();
  if (state.poll) clearInterval(state.poll);
  state.poll = setInterval(refresh, 2000);
}

async function send() {
  const input = $("input");
  const text = input.value.trim();
  if (!text || !state.cid) return;
  input.value = "";
  $("sendBtn").disabled = true;
  // optimistic echo
  const chat = $("chat");
  const wrap = document.createElement("div");
  wrap.className = "msg customer";
  wrap.innerHTML = `<div class="bubble"><div class="who">You</div>${esc(text)}</div>`;
  chat.appendChild(wrap); chat.scrollTop = chat.scrollHeight;
  try {
    await api.send(state.cid, state.tenant, text);
    await refresh();
  } finally {
    $("sendBtn").disabled = false;
    input.focus();
  }
}

async function init() {
  const sel = $("tenant");
  const tenants = await api.tenants();
  sel.innerHTML = tenants.map(t => `<option value="${esc(t.id)}">${esc(t.name)}</option>`).join("");
  try { const h = await api.health(); $("provider").textContent = "provider: " + h.provider; } catch (e) {}
  $("startBtn").onclick = start;
  $("sendBtn").onclick = send;
  $("input").addEventListener("keydown", e => { if (e.key === "Enter") send(); });
  $("name").addEventListener("keydown", e => { if (e.key === "Enter") start(); });
}

init();
