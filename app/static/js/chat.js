const p = JSON.parse(sessionStorage.getItem('participant') || '{}');
if (!p.participant_id || !p.room_id) location.href = '/join';

const messages = document.getElementById('messages');
const sendBtn = document.getElementById('send-btn');
const input = document.getElementById('message-input');
const note = document.getElementById('system-note');

let nextIndex = 0;
let pollingTimer = null;
let initialLoaded = false;

async function readErrorMessage(res, fallback) {
  try {
    const data = await res.json();
    return data.detail || fallback;
  } catch (e) {
    return fallback;
  }
}

function appendLine(data) {
  const line = document.createElement('div');
  line.className = 'msg';
  line.innerHTML = `
    <div class="meta">${data.sender_name} (${data.sender_language}) ${data.timestamp}</div>
    <div class="orig">原文：${data.original_text}</div>
    <div class="trans">译文：${data.translated_text || '无'}</div>
  `;
  messages.appendChild(line);
  messages.scrollTop = messages.scrollHeight;
}

async function pollMessages() {
  try {
    const params = new URLSearchParams({
      room_id: p.room_id,
      participant_id: p.participant_id,
      from_index: String(nextIndex),
    });
    const res = await fetch(`/api/meeting/messages?${params.toString()}`);
    if (!res.ok) {
      note.innerText = await readErrorMessage(res, '会议已结束');
      sendBtn.disabled = true;
      if (pollingTimer) clearInterval(pollingTimer);
      return;
    }
    const data = await res.json();
    for (const msg of data.messages || []) {
      appendLine(msg);
    }
    nextIndex = Number.isInteger(data.next_index) ? data.next_index : nextIndex;
    note.innerText = '已连接，可发送消息';
    sendBtn.disabled = false;
  } catch (e) {
    note.innerText = '网络波动，正在重试…';
    sendBtn.disabled = true;
  }
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;
  sendBtn.disabled = true;
  try {
    const res = await fetch('/api/meeting/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        room_id: p.room_id,
        participant_id: p.participant_id,
        sender_name: p.nickname,
        sender_language: p.language,
        text,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      note.innerText = err.detail || '发送失败';
      sendBtn.disabled = false;
      return;
    }
    input.value = '';
    input.focus();
    await pollMessages();
  } catch (e) {
    note.innerText = '发送失败，请检查网络';
    sendBtn.disabled = false;
  }
}

async function init() {
  const statusRes = await fetch('/api/meeting/status');
  if (!statusRes.ok) {
    note.innerText = await readErrorMessage(statusRes, '会议已结束');
    return;
  }
  const status = await statusRes.json();
  document.getElementById('title').innerText = status.meeting_name;
  document.getElementById('mode').innerText = status.translation_enabled ? '当前模式：开启双向翻译' : '当前模式：不翻译';
  note.innerText = '正在连接会议…';
  sendBtn.disabled = true;

  try {
    const params = new URLSearchParams({
      room_id: p.room_id,
      participant_id: p.participant_id,
      tail: '20',
    });
    const recentRes = await fetch(`/api/meeting/messages?${params.toString()}`);
    if (recentRes.ok) {
      const recent = await recentRes.json();
      for (const msg of recent.messages || []) {
        appendLine(msg);
      }
      nextIndex = Number.isInteger(recent.next_index) ? recent.next_index : nextIndex;
      initialLoaded = true;
    } else {
      note.innerText = await readErrorMessage(recentRes, '会议已结束');
    }
  } catch (e) {
    // Fall back to normal polling when recent preload fails.
  }

  if (!initialLoaded) {
    await pollMessages();
  } else {
    note.innerText = '已连接，可发送消息';
    sendBtn.disabled = false;
  }
  pollingTimer = setInterval(pollMessages, 1200);
}

sendBtn.onclick = sendMessage;
input.addEventListener('keydown', (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
    sendMessage();
  }
});
window.addEventListener('beforeunload', () => {
  if (pollingTimer) clearInterval(pollingTimer);
});

init();
