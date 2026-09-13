/**
 * 🚌 VINBUS REACT AGENT CHATBOT FRONTEND LOGIC
 * Tương tác thời gian thực với FastAPI Backend, Render ReAct Thought Trace, Voice Input.
 */

let conversationHistory = [];
let isTraceViewVisible = true;
let isVoiceRecording = false;
let recognition = null;
let latestTraceLogs = [];

document.addEventListener('DOMContentLoaded', () => {
    initAppInfo();
    setupSpeechRecognition();
});

/**
 * Khởi tạo thông tin hệ thống từ FastAPI Backend
 */
async function initAppInfo() {
    try {
        const res = await fetch('/api/info');
        if (!res.ok) throw new Error('API offline');
        const data = await res.json();

        document.getElementById('provider-name').textContent = `${data.provider} (${data.model})`;
        document.getElementById('mcp-name').textContent = data.mcp_server;
        document.getElementById('tools-count').textContent = `${data.tools_count} Tools`;
        document.getElementById('model-name-badge').textContent = `${data.model} ReAct`;

        // Render Test Cases vào Sidebar
        if (data.test_cases && data.test_cases.length > 0) {
            renderTestCases(data.test_cases);
        }
    } catch (err) {
        console.warn('Lỗi kết nối API Server:', err);
        document.getElementById('provider-name').textContent = 'Chế độ Demo Web';
    }
}

/**
 * Hiển thị danh sách 5 Test Cases nghiệm thu
 */
function renderTestCases(testCases) {
    const container = document.getElementById('test-cases-container');
    container.innerHTML = '';
    testCases.forEach((tc, idx) => {
        const btn = document.createElement('button');
        btn.className = 'test-case-btn';
        btn.innerHTML = `<strong>${tc.id}:</strong> ${tc.question.substring(0, 32)}...`;
        btn.onclick = () => useQuickPrompt(tc.question);
        container.appendChild(btn);
    });
}

/**
 * Gửi tin nhắn câu hỏi của người dùng
 */
async function handleSendMessage(e) {
    if (e) e.preventDefault();

    const inputEl = document.getElementById('user-input');
    const query = inputEl.value.trim();
    if (!query) return;

    // Ẩn welcome banner nếu có
    const welcomeCard = document.getElementById('welcome-card');
    if (welcomeCard) welcomeCard.style.display = 'none';

    // Clear input
    inputEl.value = '';
    autoResizeTextarea(inputEl);

    // Append User Message to UI
    appendUserMessage(query);

    // Show Typing Indicator
    const typingId = appendTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                history: conversationHistory
            })
        });

        removeTypingIndicator(typingId);

        if (!response.ok) {
            const errData = await response.json();
            appendAssistantMessage(`❌ Lỗi: ${errData.detail || 'Không thể xử lý yêu cầu.'}`);
            return;
        }

        const data = await response.json();
        
        // Update history & latest trace logs
        conversationHistory = data.history || [];
        latestTraceLogs = data.logs || [];

        // Append Assistant Message with ReAct trace dropdown
        appendAssistantMessage(data.final_answer, data.logs);

        // Auto update modal trace if open
        updateTraceModalData(data.logs);

    } catch (err) {
        removeTypingIndicator(typingId);
        appendAssistantMessage(`⚠️ Không thể kết nối với server backend. Vui lòng kiểm tra lại dịch vụ (server.py).`);
    }
}

/**
 * Chèn Bong bóng tin nhắn Người dùng
 */
function appendUserMessage(text) {
    const messagesContainer = document.getElementById('chat-messages');
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const msgRow = document.createElement('div');
    msgRow.className = 'message-row user';
    msgRow.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-user"></i></div>
        <div class="message-content-wrapper">
            <div class="message-bubble">${escapeHtml(text)}</div>
            <div class="message-timestamp">${timeStr}</div>
        </div>
    `;

    messagesContainer.appendChild(msgRow);
    scrollToBottom();
}

/**
 * Chèn Bong bóng tin nhắn Trợ lý VinBus ReAct Agent (kèm Waterfall Trace)
 */
function appendAssistantMessage(text, logs = []) {
    const messagesContainer = document.getElementById('chat-messages');
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const msgRow = document.createElement('div');
    msgRow.className = 'message-row assistant';

    let traceHtml = '';
    if (isTraceViewVisible && logs && logs.length > 0) {
        traceHtml = buildReActAccordionHtml(logs);
    }

    // Process formatting (markdown & custom cards)
    const formattedContent = formatAssistantResponse(text);

    msgRow.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content-wrapper">
            ${traceHtml}
            <div class="message-bubble">${formattedContent}</div>
            <div class="message-timestamp">${timeStr} • VinBus ReAct Agent</div>
        </div>
    `;

    messagesContainer.appendChild(msgRow);
    scrollToBottom();
}

/**
 * Xây dựng ReAct Thought Accordion HTML
 */
function buildReActAccordionHtml(logs) {
    let stepsContent = '';

    logs.forEach(log => {
        if (log.action_type === "TOOL_EXECUTION") {
            stepsContent += `
                <div class="trace-step-item">
                    <span class="trace-label thought-label">🧠 Thought (Step ${log.step}):</span>
                    <div>${escapeHtml(log.thought || '')}</div>
                    
                    <span class="trace-label action-label" style="margin-top: 0.3rem; display: inline-block;">🛠️ Action:</span>
                    <div>Called Tool <code>${log.tool_name}</code> with arguments:</div>
                    <div class="trace-code-block">${escapeHtml(JSON.stringify(log.arguments, null, 2))}</div>

                    <span class="trace-label observation-label" style="margin-top: 0.3rem; display: inline-block;">👁️ Observation từ MCP Server (${log.latency_ms}ms):</span>
                    <div class="trace-code-block">${escapeHtml(JSON.stringify(log.observation, null, 2))}</div>
                </div>
            `;
        } else if (log.action_type === "FINAL_ANSWER") {
            stepsContent += `
                <div class="trace-step-item">
                    <span class="trace-label thought-label">🧠 Final Thought (Step ${log.step}):</span>
                    <div>${escapeHtml(log.thought || 'Tổng hợp kết quả phản hồi khách hàng.')}</div>
                </div>
            `;
        }
    });

    return `
        <div class="react-trace-accordion">
            <details open>
                <summary class="react-trace-summary">
                    <span><i class="fa-solid fa-microchip"></i> Quy Trình Suy Luận ReAct (${logs.length} sự kiện)</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </summary>
                <div class="react-trace-body">
                    ${stepsContent}
                </div>
            </details>
        </div>
    `;
}

/**
 * Định dạng Markdown và Bus Route Cards
 */
function formatAssistantResponse(rawText) {
    if (typeof marked !== 'undefined') {
        try {
            return marked.parse(rawText);
        } catch (e) {
            console.warn("Marked parse error:", e);
        }
    }
    return rawText.replace(/\n/g, '<br>');
}

/**
 * Hiệu ứng Typing Indicator
 */
function appendTypingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');
    const id = 'typing-' + Date.now();

    const msgRow = document.createElement('div');
    msgRow.className = 'message-row assistant';
    msgRow.id = id;
    msgRow.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content-wrapper">
            <div class="message-bubble typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;

    messagesContainer.appendChild(msgRow);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

/**
 * Gợi ý Prompt nhanh
 */
function useQuickPrompt(text) {
    const inputEl = document.getElementById('user-input');
    inputEl.value = text;
    autoResizeTextarea(inputEl);
    handleSendMessage();
}

/**
 * Đặt lại đoạn hội thoại
 */
async function clearChat() {
    conversationHistory = [];
    latestTraceLogs = [];
    
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
        <div class="welcome-card" id="welcome-card">
          <div class="welcome-icon">
            <i class="fa-solid fa-bus"></i>
          </div>
          <h2>Đã Khởi Tạo Phiên Trò Chuyện Mới</h2>
          <p>Hệ thống ReAct Agent & MCP Server đã sẵn sàng phục vụ quý khách.</p>
        </div>
    `;
    
    try {
        await fetch('/api/reset', { method: 'POST' });
    } catch (e) {}
}

/**
 * Bật / Tắt hiển thị Thought Process trong khung Chat
 */
function toggleReActTraceView() {
    isTraceViewVisible = !isTraceViewVisible;
    alert(isTraceViewVisible ? 'Đã BẬT hiển thị Thought Process ReAct.' : 'Đã TẮT hiển thị Thought Process ReAct.');
}

/**
 * Modal Observability Waterfall Trace Log
 */
function toggleTraceModal() {
    const modal = document.getElementById('trace-modal');
    modal.classList.toggle('hidden');
    if (!modal.classList.contains('hidden')) {
        updateTraceModalData(latestTraceLogs);
    }
}

function updateTraceModalData(logs) {
    const codeEl = document.getElementById('trace-json-code');
    if (codeEl) {
        codeEl.textContent = JSON.stringify(logs, null, 2);
        if (typeof hljs !== 'undefined') {
            hljs.highlightElement(codeEl);
        }
    }
}

function copyTraceJson() {
    const codeEl = document.getElementById('trace-json-code');
    navigator.clipboard.writeText(codeEl.textContent);
    alert('Đã sao chép Waterfall Trace JSON!');
}

function closeModalOnBackdrop(e) {
    if (e.target.id === 'trace-modal') {
        toggleTraceModal();
    }
}

/**
 * Giọng nói (Web Speech API)
 */
function setupSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'vi-VN';
        recognition.continuous = false;

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const inputEl = document.getElementById('user-input');
            inputEl.value = transcript;
            autoResizeTextarea(inputEl);
            toggleVoiceInput();
        };

        recognition.onerror = () => {
            toggleVoiceInput();
        };

        recognition.onend = () => {
            if (isVoiceRecording) toggleVoiceInput();
        };
    }
}

function toggleVoiceInput() {
    const btn = document.getElementById('voice-btn');
    if (!recognition) {
        alert('Trình duyệt của bạn không hỗ trợ nhận diện giọng nói Web Speech API.');
        return;
    }

    if (isVoiceRecording) {
        recognition.stop();
        isVoiceRecording = false;
        btn.classList.remove('recording');
    } else {
        recognition.start();
        isVoiceRecording = true;
        btn.classList.add('recording');
    }
}

/**
 * Utilities
 */
function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = (el.scrollHeight) + 'px';
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function toggleMobileSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('active');
}

function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const icon = document.getElementById('theme-icon');
    if (document.body.classList.contains('light-theme')) {
        icon.className = 'fa-solid fa-sun';
    } else {
        icon.className = 'fa-solid fa-moon';
    }
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
