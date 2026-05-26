// ==UserScript==
// @name         BookRAG 悬浮检索助手
// @namespace    http://tampermonkey.net/
// @version      2026-05-26
// @description  适配本地图书RAG项目的油猴悬浮窗，支持流式对话、项目页切换与多行输入。
// @author       looom
// @match        http://127.0.0.1:*/*
// @match        http://localhost:*/*
// @icon         https://static.vecteezy.com/system/resources/previews/042/002/496/non_2x/rag-creative-icon-design-vector.jpg
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
    "use strict";

    if (window.__BOOKRAG_TAMER_LOADED__) {
        return;
    }
    window.__BOOKRAG_TAMER_LOADED__ = true;

    const DEFAULT_API_BASE = "http://127.0.0.1:8092";
    const STORAGE_KEY = "bookrag_tamer_state_v1";

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    const state = loadState();
    let activeConversationId = state.conversationId || "";
    let isPanelVisible = state.panelVisible === true;
    let showProjectPage = state.showProjectPage === true;
    let currentRequestController = null;
    let resizeSaveFrame = null;

    const apiBase = resolveApiBase();

    const rootHost = document.createElement("div");
    rootHost.id = "bookrag-tamer-root";
    document.body.appendChild(rootHost);
    const shadow = rootHost.attachShadow({ mode: "open" });

    shadow.innerHTML = `
    <style>
      :host { all: initial; }
      .launcher {
        position: fixed;
        right: 22px;
        bottom: 22px;
        z-index: 2147483647;
        width: 58px;
        height: 58px;
        border: none;
        border-radius: 18px;
        cursor: pointer;
        color: #0c4a6e;
        background: linear-gradient(145deg, #ffffff, #dff4ff 45%, #bfe8ff 100%);
        box-shadow: 0 16px 36px rgba(59, 130, 246, 0.28), 0 0 0 1px rgba(255, 255, 255, 0.7) inset;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: 700;
        user-select: none;
      }
      .launcher:hover { transform: translateY(-2px); }
      .panel {
        position: fixed;
        right: 24px;
        bottom: 90px;
        width: 420px;
        height: 640px;
        min-width: 360px;
        min-height: 520px;
        max-width: calc(100vw - 16px);
        max-height: calc(100vh - 16px);
        resize: both;
        z-index: 2147483647;
        display: none;
        flex-direction: column;
        overflow: hidden;
        box-sizing: border-box;
        border-radius: 22px;
        border: 1px solid rgba(125, 211, 252, 0.55);
        background: linear-gradient(180deg, rgba(247, 252, 255, 0.98), rgba(232, 245, 255, 0.98));
        box-shadow: 0 24px 68px rgba(59, 130, 246, 0.24), 0 0 0 1px rgba(255, 255, 255, 0.88) inset;
        color: #134e7d;
        backdrop-filter: blur(18px);
      }
      .panel.visible { display: flex; }
      .header {
        padding: 14px 16px;
        background: linear-gradient(135deg, rgba(191, 232, 255, 0.95), rgba(223, 244, 255, 0.95));
        border-bottom: 1px solid rgba(125, 211, 252, 0.35);
        cursor: move;
        user-select: none;
      }
      .header-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      .title-wrap { display: flex; flex-direction: column; gap: 2px; }
      .title { font-size: 16px; font-weight: 800; letter-spacing: 0.02em; }
      .subtitle { font-size: 12px; color: #4f7da0; }
      .status-pill {
        display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px;
        background: rgba(255, 255, 255, 0.75); border: 1px solid rgba(125, 211, 252, 0.45); font-size: 12px; color: #0f6aa0;
      }
      .dots { width: 8px; height: 8px; border-radius: 999px; background: #38bdf8; box-shadow: 0 0 0 6px rgba(56, 189, 248, 0.15); }
      .actions { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
      .btn {
        border: 1px solid rgba(125, 211, 252, 0.45); background: rgba(255, 255, 255, 0.8); color: #14638f;
        border-radius: 12px; padding: 8px 12px; cursor: pointer; font-size: 12px;
        transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
      }
      .btn:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(125, 211, 252, 0.18); background: rgba(255, 255, 255, 0.95); }
      .btn.primary { background: linear-gradient(135deg, #dff4ff, #bfe8ff); }
      .btn.active { background: linear-gradient(135deg, #8fd5ff, #c3ebff); color: #0b4f78; font-weight: 700; }
      .content { flex: 1; display: flex; flex-direction: column; min-height: 0; }
      .tabbar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 10px 14px 0; }
      .tab { border: none; border-radius: 14px; padding: 10px 12px; background: rgba(223, 244, 255, 0.78); color: #357aa3; cursor: pointer; font-size: 12px; }
      .tab.active { background: linear-gradient(135deg, #8fd5ff, #dff4ff); color: #0f5f91; font-weight: 700; box-shadow: 0 10px 20px rgba(125, 211, 252, 0.16); }
      .messages { flex: 1; min-height: 0; overflow: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
      .message { border-radius: 16px; padding: 12px 14px; border: 1px solid rgba(125, 211, 252, 0.34); background: rgba(255, 255, 255, 0.82); box-shadow: 0 10px 24px rgba(125, 211, 252, 0.08); }
      .message.user { background: linear-gradient(135deg, rgba(224, 244, 255, 0.96), rgba(202, 236, 255, 0.92)); }
      .message.assistant { background: rgba(255, 255, 255, 0.92); }
      .role { font-size: 12px; font-weight: 700; color: #1d6ea8; margin-bottom: 8px; }
      .content-text { white-space: pre-wrap; word-break: break-word; line-height: 1.7; color: #174f78; font-size: 14px; }
      .sources { margin-top: 10px; display: grid; gap: 8px; }
      .source { border-radius: 12px; padding: 10px 12px; background: rgba(223, 244, 255, 0.72); border: 1px solid rgba(125, 211, 252, 0.28); font-size: 12px; color: #4f7da0; line-height: 1.6; }
      .composer { padding: 12px 14px 14px; border-top: 1px solid rgba(125, 211, 252, 0.25); background: rgba(247, 252, 255, 0.96); }
      .textarea {
        width: 100%; box-sizing: border-box; resize: vertical; min-height: 96px; max-height: 220px; border-radius: 16px;
        border: 1px solid rgba(125, 211, 252, 0.45); background: rgba(255, 255, 255, 0.96); color: #16557d;
        padding: 12px 14px; outline: none; font-size: 14px; line-height: 1.7; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
      }
      .textarea:focus { border-color: #5dbbf0; box-shadow: 0 0 0 4px rgba(93, 187, 240, 0.16); }
      .composer-row { margin-top: 10px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
      .send { flex: 0 0 auto; padding: 10px 18px; border: none; border-radius: 14px; background: linear-gradient(135deg, #5dbbf0, #8fd5ff); color: #fff; font-weight: 700; cursor: pointer; box-shadow: 0 12px 26px rgba(93, 187, 240, 0.28); }
      .send:hover { transform: translateY(-1px); }
      .mini-toggle { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #4f7da0; user-select: none; }
      .mini-toggle input { width: 16px; height: 16px; accent-color: #5dbbf0; }
      .hint { margin-top: 8px; font-size: 12px; color: #5f7f98; }
      .project-frame { width: 100%; height: 100%; border: 0; background: #fff; }
      .project-view { display: none; flex: 1; min-height: 0; }
      .project-view.visible { display: flex; }
      .iframe-wrap { flex: 1; min-height: 0; border-top: 1px solid rgba(125, 211, 252, 0.25); background: #f4fbff; }
      .resize-note { position: absolute; right: 10px; bottom: 8px; font-size: 11px; color: rgba(79, 125, 160, 0.7); pointer-events: none; }
      .empty { color: #6b91aa; text-align: center; padding: 18px 10px; border: 1px dashed rgba(125, 211, 252, 0.36); border-radius: 16px; background: rgba(255, 255, 255, 0.55); }
    </style>

    <button class="launcher" id="bookrag-launcher" title="打开/隐藏检索助手">R</button>
    <section class="panel" id="bookrag-panel" aria-label="BookRAG 检索助手">
      <div class="header" id="bookrag-header">
        <div class="header-top">
          <div class="title-wrap">
            <div class="title">BookRAG 检索助手</div>
            <div class="subtitle" id="bookrag-subtitle">${escapeHtml(apiBase)} · 流式响应已开启</div>
          </div>
          <div class="status-pill"><span class="dots"></span><span id="bookrag-conn-status">就绪</span></div>
        </div>
        <div class="actions">
          <button class="btn primary" id="toggle-project-btn" type="button">项目页</button>
          <button class="btn" id="clear-chat-btn" type="button">清空</button>
          <button class="btn" id="hide-btn" type="button">隐藏</button>
        </div>
      </div>

      <div class="content">
        <div class="tabbar">
          <button class="tab active" data-tab="chat" type="button">对话</button>
          <button class="tab" data-tab="status" type="button">状态</button>
          <button class="tab" data-tab="api" type="button">说明</button>
        </div>

        <div class="messages" id="bookrag-messages">
          <div class="message assistant">
            <div class="role">系统</div>
            <div class="content-text">这里是本地图书 RAG 悬浮检索助手。可以拖动窗口，切换项目页，开启流式响应，并直接向后端发起检索对话。</div>
          </div>
        </div>

        <div class="project-view" id="bookrag-project-view"></div>

        <div class="composer">
          <textarea class="textarea" id="bookrag-input" placeholder="输入问题，支持多行输入。Ctrl/⌘ + Enter 发送，Enter 换行。"></textarea>
          <div class="composer-row">
            <button class="send" id="bookrag-send" type="button">发送</button>
            <label class="mini-toggle"><input id="bookrag-stream-toggle" type="checkbox" checked />流式响应</label>
            <label class="mini-toggle"><input id="bookrag-autoscroll-toggle" type="checkbox" checked />自动滚动</label>
          </div>
          <div class="hint">对话会调用 ${escapeHtml(apiBase)}/chat，并自动传入 stream=true/false。</div>
        </div>
      </div>
      <div class="resize-note">可拖动 / 可缩放</div>
    </section>
  `;

    const panel = shadow.getElementById("bookrag-panel");
    const launcher = shadow.getElementById("bookrag-launcher");
    const header = shadow.getElementById("bookrag-header");
    const subtitle = shadow.getElementById("bookrag-subtitle");
    const connStatus = shadow.getElementById("bookrag-conn-status");
    const input = shadow.getElementById("bookrag-input");
    const sendBtn = shadow.getElementById("bookrag-send");
    const clearBtn = shadow.getElementById("clear-chat-btn");
    const hideBtn = shadow.getElementById("hide-btn");
    const toggleProjectBtn = shadow.getElementById("toggle-project-btn");
    const projectView = shadow.getElementById("bookrag-project-view");
    const messages = shadow.getElementById("bookrag-messages");
    const streamToggle = shadow.getElementById("bookrag-stream-toggle");
    const autoscrollToggle = shadow.getElementById("bookrag-autoscroll-toggle");

    applySavedPanelState();
    bindEvents();
    renderPanelVisibility();

    function loadState() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return {};
            }
            return JSON.parse(raw) || {};
        } catch {
            return {};
        }
    }

    function saveState(extra = {}) {
        const next = {
            panelVisible: isPanelVisible,
            showProjectPage,
            conversationId: activeConversationId,
            streamEnabled: streamToggle ? streamToggle.checked : true,
            autoscrollEnabled: autoscrollToggle ? autoscrollToggle.checked : true,
            ...extra,
        };
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
            // ignore storage failures
        }
    }

    function resolveApiBase() {
        try {
            if (window.location.port === "8092") {
                return window.location.origin;
            }
        } catch {
            // ignore
        }
        return DEFAULT_API_BASE;
    }

    function applySavedPanelState() {
        const savedLeft = state.left;
        const savedTop = state.top;
        const savedWidth = state.width;
        const savedHeight = state.height;

        if (savedLeft !== undefined) {
            panel.style.left = `${savedLeft}px`;
            panel.style.right = "auto";
        } else {
            panel.style.right = "24px";
            panel.style.left = "auto";
        }
        if (savedTop !== undefined) {
            panel.style.top = `${savedTop}px`;
            panel.style.bottom = "auto";
        } else {
            panel.style.bottom = "90px";
            panel.style.top = "auto";
        }
        if (savedWidth !== undefined) {
            panel.style.width = `${savedWidth}px`;
        }
        if (savedHeight !== undefined) {
            panel.style.height = `${savedHeight}px`;
        }
        if (state.streamEnabled !== undefined) {
            streamToggle.checked = !!state.streamEnabled;
        }
        if (state.autoscrollEnabled !== undefined) {
            autoscrollToggle.checked = !!state.autoscrollEnabled;
        }
        if (typeof state.showProjectPage === "boolean") {
            showProjectPage = state.showProjectPage;
        }
        if (state.conversationId) {
            activeConversationId = state.conversationId;
        }
    }

    function bindEvents() {
        launcher.addEventListener("click", () => {
            isPanelVisible = !isPanelVisible;
            renderPanelVisibility();
            saveState();
        });

        hideBtn.addEventListener("click", () => {
            isPanelVisible = false;
            renderPanelVisibility();
            saveState();
        });

        toggleProjectBtn.addEventListener("click", () => {
            showProjectPage = !showProjectPage;
            renderProjectView();
            saveState();
        });

        clearBtn.addEventListener("click", clearChat);
        sendBtn.addEventListener("click", () => sendMessage().catch(reportError));

        streamToggle.addEventListener("change", () => saveState());
        autoscrollToggle.addEventListener("change", () => saveState());

        if (typeof ResizeObserver !== "undefined") {
            const panelResizeObserver = new ResizeObserver(() => {
                if (resizeSaveFrame !== null) {
                    cancelAnimationFrame(resizeSaveFrame);
                }
                resizeSaveFrame = requestAnimationFrame(() => {
                    const rect = panel.getBoundingClientRect();
                    saveState({
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        left: Math.round(rect.left),
                        top: Math.round(rect.top),
                    });
                });
            });
            panelResizeObserver.observe(panel);
        }

        shadow.querySelectorAll(".tab").forEach((tab) => {
            tab.addEventListener("click", () => {
                const tabName = tab.dataset.tab;
                shadow
                    .querySelectorAll(".tab")
                    .forEach((item) => item.classList.toggle("active", item === tab));
                if (tabName === "chat") {
                    showProjectPage = false;
                    messages.style.display = "flex";
                    projectView.style.display = "none";
                    shadow.querySelector(".composer").style.display = "block";
                    projectView.classList.remove("visible");
                    toggleProjectBtn.textContent = "项目页";
                    toggleProjectBtn.classList.remove("active");
                } else if (tabName === "status") {
                    showProjectPage = false;
                    messages.style.display = "flex";
                    projectView.style.display = "none";
                    shadow.querySelector(".composer").style.display = "none";
                    projectView.classList.remove("visible");
                    toggleProjectBtn.textContent = "项目页";
                    toggleProjectBtn.classList.remove("active");
                    appendSystemMessage(
                        "状态说明：可点击项目页查看后台页面，聊天会通过 /chat 接口发起请求。",
                    );
                } else if (tabName === "api") {
                    showProjectPage = false;
                    messages.style.display = "flex";
                    projectView.style.display = "none";
                    shadow.querySelector(".composer").style.display = "none";
                    projectView.classList.remove("visible");
                    toggleProjectBtn.textContent = "项目页";
                    toggleProjectBtn.classList.remove("active");
                    appendSystemMessage(
                        "API 说明：\n- GET /status\n- GET /books\n- GET /books/content?path=...\n- POST /chat (支持 stream=true/false)\n- POST /scan\n- POST /reindex\n- POST /upload",
                    );
                }
                saveState();
            });
        });

        let dragging = false;
        let dragOffsetX = 0;
        let dragOffsetY = 0;

        header.addEventListener("pointerdown", (event) => {
            dragging = true;
            const rect = panel.getBoundingClientRect();
            dragOffsetX = event.clientX - rect.left;
            dragOffsetY = event.clientY - rect.top;
            if (panel.setPointerCapture) {
                try {
                    panel.setPointerCapture(event.pointerId);
                } catch (_) { }
            }
            event.preventDefault();
        });

        window.addEventListener("pointermove", (event) => {
            if (!dragging) {
                return;
            }
            const left = Math.max(
                8,
                Math.min(
                    window.innerWidth - panel.offsetWidth - 8,
                    event.clientX - dragOffsetX,
                ),
            );
            const top = Math.max(
                8,
                Math.min(
                    window.innerHeight - panel.offsetHeight - 8,
                    event.clientY - dragOffsetY,
                ),
            );
            panel.style.left = `${left}px`;
            panel.style.top = `${top}px`;
            panel.style.right = "auto";
            panel.style.bottom = "auto";
            saveState({ left, top });
        });

        window.addEventListener("pointerup", () => {
            dragging = false;
        });

        input.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                sendMessage().catch(reportError);
            }
        });

        window.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && isPanelVisible) {
                isPanelVisible = false;
                renderPanelVisibility();
                saveState();
            }
        });
    }

    function renderPanelVisibility() {
        panel.classList.toggle("visible", isPanelVisible);
        launcher.textContent = isPanelVisible ? "×" : "R";
        launcher.title = isPanelVisible ? "隐藏检索助手" : "打开检索助手";
        if (isPanelVisible) {
            renderProjectView();
        }
    }

    function renderProjectView() {
        projectView.classList.toggle("visible", showProjectPage);
        projectView.style.display = showProjectPage ? "flex" : "none";
        if (showProjectPage) {
            shadow.querySelector(".composer").style.display = "none";
            messages.style.display = "none";
            projectView.innerHTML = `
        <div class="iframe-wrap">
            <iframe class="project-frame" src="${escapeHtml(apiBase)}/" title="BookRAG 项目页"></iframe>
        </div>
        `;
            toggleProjectBtn.classList.add("active");
            toggleProjectBtn.textContent = "隐藏项目页";
        } else {
            shadow.querySelector(".composer").style.display = "block";
            messages.style.display = "flex";
            projectView.innerHTML = "";
            toggleProjectBtn.classList.remove("active");
            toggleProjectBtn.textContent = "项目页";
        }
    }

    function appendMessage(role, content, sources = []) {
        const item = document.createElement("div");
        item.className = `message ${role}`;

        const roleNode = document.createElement("div");
        roleNode.className = "role";
        roleNode.textContent = role === "user" ? "你" : "AI";

        const textNode = document.createElement("div");
        textNode.className = "content-text";
        textNode.textContent = content;

        item.appendChild(roleNode);
        item.appendChild(textNode);

        if (Array.isArray(sources) && sources.length) {
            const sourceWrap = document.createElement("div");
            sourceWrap.className = "sources";
            for (const source of sources) {
                const sourceNode = document.createElement("div");
                sourceNode.className = "source";
                sourceNode.textContent = `来源${source.source_index} | ${source.file_name || ""} | 第${(source.chunk_index || 0) + 1}块\n${source.excerpt || ""}`;
                sourceWrap.appendChild(sourceNode);
            }
            item.appendChild(sourceWrap);
        }

        messages.appendChild(item);
        if (autoscrollToggle.checked) {
            messages.scrollTop = messages.scrollHeight;
        }
        return item;
    }

    function appendSystemMessage(content) {
        appendMessage("assistant", content);
    }

    function clearChat() {
        messages.innerHTML = "";
        appendSystemMessage("聊天内容已清空。");
    }

    function reportError(error) {
        connStatus.textContent = "异常";
        appendMessage(
            "assistant",
            `请求失败：${error && error.message ? error.message : String(error)}`,
        );
    }

    function createConversationId() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        return `conv_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    }

    async function sendMessage() {
        const question = input.value.trim();
        if (!question) {
            appendSystemMessage("请输入问题后再发送。");
            return;
        }

        if (!activeConversationId) {
            activeConversationId = createConversationId();
        }

        const streamEnabled = streamToggle.checked;
        saveState({
            conversationId: activeConversationId,
            streamEnabled,
            autoscrollEnabled: autoscrollToggle.checked,
        });

        appendMessage("user", question);
        const assistantNode = appendMessage(
            "assistant",
            streamEnabled ? "AI 正在流式响应..." : "AI 正在思考...",
        );
        input.value = "";
        connStatus.textContent = "请求中";

        try {
            if (streamEnabled) {
                const finalPayload = await postChatStream(
                    question,
                    activeConversationId,
                    assistantNode,
                );
                activeConversationId =
                    finalPayload.conversation_id || activeConversationId;
                connStatus.textContent = "就绪";
                if (finalPayload.answer) {
                    updateAssistantNode(
                        assistantNode,
                        finalPayload.answer,
                        finalPayload.sources || [],
                    );
                }
                return finalPayload;
            }

            const result = await postChatJson(question, activeConversationId, false);
            activeConversationId = result.conversation_id || activeConversationId;
            connStatus.textContent = "就绪";
            updateAssistantNode(
                assistantNode,
                result.answer || "没有返回内容",
                result.sources || [],
            );
            return result;
        } catch (error) {
            connStatus.textContent = "失败";
            assistantNode.querySelector(".content-text").textContent =
                `AI 回复失败：${error && error.message ? error.message : String(error)}`;
            throw error;
        } finally {
            saveState({
                conversationId: activeConversationId,
                streamEnabled,
                autoscrollEnabled: autoscrollToggle.checked,
            });
        }
    }

    function updateAssistantNode(node, answer, sources) {
        const textNode = node.querySelector(".content-text");
        if (textNode) {
            textNode.textContent = answer;
        }
        const oldSources = node.querySelector(".sources");
        if (oldSources) {
            oldSources.remove();
        }
        if (Array.isArray(sources) && sources.length) {
            const sourceWrap = document.createElement("div");
            sourceWrap.className = "sources";
            for (const source of sources) {
                const sourceNode = document.createElement("div");
                sourceNode.className = "source";
                sourceNode.textContent = `来源${source.source_index} | ${source.file_name || ""} | 第${(source.chunk_index || 0) + 1}块\n${source.excerpt || ""}`;
                sourceWrap.appendChild(sourceNode);
            }
            node.appendChild(sourceWrap);
        }
        if (autoscrollToggle.checked) {
            messages.scrollTop = messages.scrollHeight;
        }
    }

    async function postChatJson(question, conversationId, stream) {
        const response = await fetch(`${apiBase}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                conversation_id: conversationId,
                stream,
            }),
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || response.statusText || `HTTP ${response.status}`);
        }
        return response.json();
    }

    async function postChatStream(question, conversationId, assistantNode) {
        currentRequestController = new AbortController();
        const response = await fetch(`${apiBase}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
            },
            body: JSON.stringify({
                question,
                conversation_id: conversationId,
                stream: true,
            }),
            signal: currentRequestController.signal,
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || response.statusText || `HTTP ${response.status}`);
        }
        if (!response.body) {
            throw new Error("当前浏览器不支持流式读取");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let answer = "";
        let finalPayload = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split(/\r?\n\r?\n/);
            buffer = events.pop() || "";
            for (const block of events) {
                const event = parseSseBlock(block);
                if (!event) {
                    continue;
                }
                if (
                    event.eventName === "meta" &&
                    event.payload &&
                    event.payload.conversation_id
                ) {
                    activeConversationId = event.payload.conversation_id;
                    saveState({ conversationId: activeConversationId });
                    continue;
                }
                if (
                    event.eventName === "token" &&
                    event.payload &&
                    typeof event.payload.content === "string"
                ) {
                    answer += event.payload.content;
                    updateAssistantNode(assistantNode, answer, []);
                    continue;
                }
                if (event.eventName === "done" && event.payload) {
                    finalPayload = event.payload;
                }
            }
        }

        buffer += decoder.decode();
        if (buffer.trim()) {
            const event = parseSseBlock(buffer);
            if (event) {
                if (
                    event.eventName === "token" &&
                    event.payload &&
                    typeof event.payload.content === "string"
                ) {
                    answer += event.payload.content;
                }
                if (event.eventName === "done" && event.payload) {
                    finalPayload = event.payload;
                }
            }
        }

        if (finalPayload) {
            activeConversationId =
                finalPayload.conversation_id || activeConversationId;
            if (typeof finalPayload.answer === "string" && finalPayload.answer) {
                answer = finalPayload.answer;
            }
            updateAssistantNode(
                assistantNode,
                answer || "没有返回内容",
                finalPayload.sources || [],
            );
            saveState({ conversationId: activeConversationId });
            return finalPayload;
        }

        updateAssistantNode(assistantNode, answer || "没有返回内容", []);
        return { conversation_id: activeConversationId, answer, sources: [] };
    }

    function parseSseBlock(block) {
        let eventName = "message";
        const dataLines = [];
        for (const rawLine of block.split(/\r?\n/)) {
            const line = rawLine.trimEnd();
            if (line.startsWith("event:")) {
                eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
                dataLines.push(line.slice(5).trimStart());
            }
        }
        if (!dataLines.length) {
            return null;
        }
        const dataText = dataLines.join("\n");
        try {
            return { eventName, payload: JSON.parse(dataText) };
        } catch {
            return { eventName, payload: dataText };
        }
    }

    window.addEventListener("beforeunload", () => {
        saveState({
            conversationId: activeConversationId,
            panelVisible: isPanelVisible,
            showProjectPage,
        });
        if (currentRequestController) {
            currentRequestController.abort();
        }
    });

    if (!isPanelVisible) {
        renderPanelVisibility();
    } else {
        renderProjectView();
    }

    setTimeout(() => {
        subtitle.textContent = `${apiBase} · 已连接本地图书RAG服务`;
        connStatus.textContent = "就绪";
    }, 0);
})();
