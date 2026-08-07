// ============================================================
// CONFIG
// ============================================================
// Point this at wherever your FastAPI backend is running.
// Local dev default — change to your deployed URL when you host it.
const API_BASE_URL = "https://college-ai-assistant-rag.onrender.com";
const CHAT_ENDPOINT = `${API_BASE_URL}/chat`;
const HEALTH_ENDPOINT = `${API_BASE_URL}/`;

const REDUCE_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const QUERY_TYPE_META = {
  academic: { label: "Academic", icon: "📚" },
  fee: { label: "Fee", icon: "💰" },
  general: { label: "General", icon: "💬" },
};

let currentProgramme = null;

// ============================================================
// DOM REFS
// ============================================================
const onboarding = document.getElementById("onboarding");
const chatScreen = document.getElementById("chatScreen");
const programmeGrid = document.getElementById("programmeGrid");
const programmeBadge = document.getElementById("programmeBadge");

const chatBody = document.querySelector(".chat-body");
const chatLog = document.getElementById("chatLog");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");

const apiStatus = document.getElementById("apiStatus");
const graphToggleBtn = document.getElementById("graphToggleBtn");
const graphCloseBtn = document.getElementById("graphCloseBtn");
const graphBackdrop = document.getElementById("graphBackdrop");

// ============================================================
// PROGRAMME SELECTION
// ============================================================
programmeGrid.querySelectorAll(".programme-card").forEach((card) => {
  card.addEventListener("click", () => selectProgramme(card.dataset.programme));
});

programmeBadge.addEventListener("click", () => {
  onboarding.hidden = false;
  chatScreen.hidden = true;
});

function selectProgramme(programme) {
  currentProgramme = programme;
  programmeBadge.textContent = programme;

  onboarding.hidden = true;
  chatScreen.hidden = false;

  chatLog.innerHTML = "";
  appendMessage(
    "assistant",
    `Hi! I'm the SNJB College Assistant \uD83D\uDC4B Welcome! You're set as a ${programme} student. Ask me anything about attendance, exams, fees, or campus life.`,
    "general"
  );

  // Graph panel open by default on desktop, closed on mobile.
  if (window.innerWidth >= 900) {
    chatBody.classList.add("graph-open");
  } else {
    chatBody.classList.remove("graph-open");
  }

  chatInput.focus();
}

// ============================================================
// CHAT — sending & rendering messages
// ============================================================
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text || !currentProgramme) return;

  appendMessage("user", text);
  chatInput.value = "";
  autoResize();
  setSending(true);
  showTyping();

  try {
    const res = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ programme: currentProgramme, message: text }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ? String(body.detail) : `Request failed (${res.status}).`);
    }

    const data = await res.json();
    hideTyping();
    appendMessage("assistant", data.response, data.query_type);
    animateGraphPath(data.query_type);
  } catch (err) {
    hideTyping();
    appendMessage(
      "assistant",
      "I couldn't reach the server just now. Make sure the FastAPI backend is running, then try again.",
      "general"
    );
  } finally {
    setSending(false);
  }
});

function appendMessage(role, text, queryType) {
  const msg = document.createElement("div");
  msg.className = `msg msg-${role}`;

  if (role === "assistant" && queryType && QUERY_TYPE_META[queryType]) {
    const badge = document.createElement("span");
    badge.className = `msg-badge badge-${queryType}`;
    badge.textContent = `${QUERY_TYPE_META[queryType].icon} ${QUERY_TYPE_META[queryType].label}`;
    msg.appendChild(badge);
    msg.appendChild(document.createElement("br"));
  }

  const textNode = document.createTextNode(text);
  msg.appendChild(textNode);

  chatLog.appendChild(msg);
  scrollToBottom();
}

function showTyping() {
  const typing = document.createElement("div");
  typing.className = "msg msg-assistant msg-typing";
  typing.id = "typingIndicator";
  typing.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
  chatLog.appendChild(typing);
  scrollToBottom();
}

function hideTyping() {
  const typing = document.getElementById("typingIndicator");
  if (typing) typing.remove();
}

function scrollToBottom() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setSending(isSending) {
  sendBtn.disabled = isSending;
}

// ============================================================
// INPUT — auto-grow + Enter to send
// ============================================================
chatInput.addEventListener("input", autoResize);

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

function autoResize() {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + "px";
}

// ============================================================
// ROUTING GRAPH — animates the actual LangGraph path taken
// ============================================================
const ALL_NODE_IDS = ["node-start", "node-classifier", "node-academic", "node-fee", "node-general", "node-response", "node-end"];
const ALL_EDGE_IDS = [
  "edge-start-classifier",
  "edge-classifier-academic",
  "edge-classifier-fee",
  "edge-classifier-general",
  "edge-academic-response",
  "edge-fee-response",
  "edge-general-response",
  "edge-response-end",
];

function resetGraph() {
  ALL_NODE_IDS.forEach((id) => document.getElementById(id)?.classList.remove("active"));
  ALL_EDGE_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("active-academic", "active-fee", "active-general", "active-neutral");
  });
}

function animateGraphPath(type) {
  if (!QUERY_TYPE_META[type]) type = "general";
  resetGraph();

  const step = (fn) => fn();
  const delay = REDUCE_MOTION ? 0 : 180;
  let t = 0;

  const sequence = [
    () => document.getElementById("node-start")?.classList.add("active"),
    () => document.getElementById("edge-start-classifier")?.classList.add("active-neutral"),
    () => document.getElementById("node-classifier")?.classList.add("active"),
    () => document.getElementById(`edge-classifier-${type}`)?.classList.add(`active-${type}`),
    () => document.getElementById(`node-${type}`)?.classList.add("active"),
    () => document.getElementById(`edge-${type}-response`)?.classList.add(`active-${type}`),
    () => document.getElementById("node-response")?.classList.add("active"),
    () => document.getElementById("edge-response-end")?.classList.add("active-neutral"),
    () => document.getElementById("node-end")?.classList.add("active"),
  ];

  sequence.forEach((fn) => {
    setTimeout(() => step(fn), t);
    t += delay;
  });

  const hint = document.getElementById("graphHint");
  if (hint) {
    const label = QUERY_TYPE_META[type].label;
    hint.textContent = `Last question was classified as "${label}" and routed through ${label === "General" ? "no retrieval" : label + " RAG"}.`;
  }
}

// ============================================================
// GRAPH PANEL TOGGLE (desktop sidebar / mobile drawer)
// ============================================================
graphToggleBtn.addEventListener("click", () => {
  const isOpen = chatBody.classList.toggle("graph-open");
  graphToggleBtn.setAttribute("aria-expanded", String(isOpen));
});

graphCloseBtn.addEventListener("click", () => {
  chatBody.classList.remove("graph-open");
  graphToggleBtn.setAttribute("aria-expanded", "false");
});

graphBackdrop.addEventListener("click", () => {
  chatBody.classList.remove("graph-open");
  graphToggleBtn.setAttribute("aria-expanded", "false");
});

// ============================================================
// API HEALTH CHECK
// ============================================================
async function checkApiStatus() {
  try {
    const res = await fetch(HEALTH_ENDPOINT, { method: "GET" });
    if (!res.ok) throw new Error("bad status");
    apiStatus.classList.add("online");
    apiStatus.classList.remove("offline");
    apiStatus.lastChild.textContent = "API connected";
  } catch {
    apiStatus.classList.add("offline");
    apiStatus.classList.remove("online");
    apiStatus.lastChild.textContent = "API unreachable";
  }
}

// ============================================================
// INIT
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  checkApiStatus();
});
