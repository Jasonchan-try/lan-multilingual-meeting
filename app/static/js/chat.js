const p = JSON.parse(sessionStorage.getItem('participant') || '{}');
if (!p.participant_id || !p.room_id) location.href = '/join';

const messages = document.getElementById('messages');
const sendBtn = document.getElementById('send-btn');
const input = document.getElementById('message-input');
const note = document.getElementById('system-note');
const fileInput = document.getElementById('file-input');
const attachPreview = document.getElementById('attach-preview');
const emojiBtn = document.getElementById('emoji-btn');
const emojiPanel = document.getElementById('emoji-panel');

let nextIndex = 0;
let pollingTimer = null;
let initialLoaded = false;
let isPolling = false; // 防并发锁

// 当前待发送的附件
let pendingFile = null; // { file, type: 'image'|'text'|'other', previewUrl }

// ── 图片灯箱 ──────────────────────────────────────────
const lightbox = document.createElement('div');
lightbox.id = 'lightbox';
const lightboxImg = document.createElement('img');
lightbox.appendChild(lightboxImg);
document.body.appendChild(lightbox);
lightbox.addEventListener('click', () => lightbox.classList.remove('active'));

function openLightbox(src) {
  lightboxImg.src = src;
  lightbox.classList.add('active');
}

// ── emoji 面板 ────────────────────────────────────────
emojiBtn.addEventListener('click', (ev) => {
  ev.stopPropagation();
  emojiPanel.classList.toggle('hidden');
});

// 点击 emoji 插入到输入框光标位置
emojiPanel.addEventListener('click', (ev) => {
  const emoji = ev.target.closest('span');
  if (!emoji) return;
  const val = emoji.innerText;
  const start = input.selectionStart;
  const end = input.selectionEnd;
  input.value = input.value.slice(0, start) + val + input.value.slice(end);
  // 光标移到插入位置之后
  input.selectionStart = input.selectionEnd = start + val.length;
  input.focus();
  emojiPanel.classList.add('hidden');
});

// 点击其他地方关闭 emoji 面板
document.addEventListener('click', (ev) => {
  if (!emojiPanel.contains(ev.target) && ev.target !== emojiBtn) {
    emojiPanel.classList.add('hidden');
  }
});

// ── 附件类型判断 ──────────────────────────────────────
function getFileType(file) {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type === 'text/plain' || file.name.endsWith('.txt')) return 'text';
  return 'other';
}

// ── 附件选择处理 ──────────────────────────────────────
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;

  const MAX_MB = 10;
  if (file.size > MAX_MB * 1024 * 1024) {
    note.innerText = `附件不能超过 ${MAX_MB}MB`;
    fileInput.value = '';
    return;
  }

  const type = getFileType(file);
  pendingFile = { file, type, previewUrl: null };

  // 渲染发送前预览
  attachPreview.innerHTML = '';
  const box = document.createElement('div');
  box.className = 'attach-preview-box';

  if (type === 'image') {
    const url = URL.createObjectURL(file);
    pendingFile.previewUrl = url;
    const img = document.createElement('img');
    img.src = url;
    box.appendChild(img);
  } else {
    const icon = document.createElement('span');
    icon.style.fontSize = '24px';
    icon.innerText = type === 'text' ? '📄' : '📦';
    box.appendChild(icon);
  }

  const name = document.createElement('span');
  name.className = 'attach-name';
  name.innerText = `${file.name}（${(file.size / 1024).toFixed(1)} KB）`;
  box.appendChild(name);

  const removeBtn = document.createElement('button');
  removeBtn.className = 'attach-remove';
  removeBtn.innerText = '✕';
  removeBtn.onclick = clearPendingFile;
  box.appendChild(removeBtn);

  attachPreview.appendChild(box);
  fileInput.value = '';
});

function clearPendingFile() {
  if (pendingFile && pendingFile.previewUrl) {
    URL.revokeObjectURL(pendingFile.previewUrl);
  }
  pendingFile = null;
  attachPreview.innerHTML = '';
}

// ── 附件上传 ──────────────────────────────────────────
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('room_id', p.room_id);
  formData.append('participant_id', p.participant_id);

  const res = await fetch('/api/meeting/upload', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || '上传失败');
  }
  return await res.json(); // { url, filename, original_name, file_type, file_size }
}

// ── 消息渲染 ──────────────────────────────────────────
function appendLine(data) {
  const line = document.createElement('div');
  line.className = 'msg';

  let attachHtml = '';
  if (data.attachment_url) {
    if (data.attachment_type === 'image') {
      attachHtml = `
        <div class="msg-image">
          <img src="${data.attachment_url}" alt="${data.attachment_name}" data-src="${data.attachment_url}" />
        </div>`;
    } else if (data.attachment_type === 'text') {
      const content = data.attachment_text ? data.attachment_text : '';
      attachHtml = `
        <div class="msg-text-content">${escapeHtml(content)}</div>
        <div class="msg-file"><a href="${data.attachment_url}" download="${data.attachment_name}">⬇ ${escapeHtml(data.attachment_name)}</a></div>`;
    } else {
      attachHtml = `
        <div class="msg-file"><a href="${data.attachment_url}" download="${data.attachment_name}">⬇ ${escapeHtml(data.attachment_name)}</a></div>`;
    }
  }

  const origHtml = data.original_text
    ? `<div class="orig">原文：${escapeHtml(data.original_text)}</div>`
    : '';
  const transHtml = (data.translated_text && data.translated_text !== '无')
    ? `<div class="trans">译文：${escapeHtml(data.translated_text)}</div>`
    : '';

  line.innerHTML = `
    <div class="meta">${escapeHtml(data.sender_name)} (${escapeHtml(data.sender_language)}) ${escapeHtml(data.timestamp)}</div>
    ${origHtml}${transHtml}${attachHtml}
  `;

  // 图片点击放大
  const img = line.querySelector('.msg-image img');
  if (img) {
    img.addEventListener('click', () => openLightbox(img.dataset.src));
  }

  messages.appendChild(line);
  messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── 错误读取 ──────────────────────────────────────────
async function readErrorMessage(res, fallback) {
  try {
    const data = await res.json();
    return data.detail || fallback;
  } catch (e) {
    return fallback;
  }
}

// ── 轮询消息 ──────────────────────────────────────────
async function pollMessages() {
  if (isPolling) return;
  isPolling = true;
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
  } finally {
    isPolling = false;
  }
}

// ── 发送消息 ──────────────────────────────────────────
async function sendMessage() {
  const text = input.value.trim();
  if (!text && !pendingFile) return;
  sendBtn.disabled = true;

  try {
    // 1. 如果有附件，先上传
    let attachmentInfo = null;
    if (pendingFile) {
      note.innerText = '正在上传附件…';
      try {
        attachmentInfo = await uploadFile(pendingFile.file);
      } catch (e) {
        note.innerText = `附件上传失败：${e.message}`;
        sendBtn.disabled = false;
        return;
      }
    }

    // 2. 发送消息（含附件信息）
    const body = {
      room_id: p.room_id,
      participant_id: p.participant_id,
      sender_name: p.nickname,
      sender_language: p.language,
      text: text || '',
    };
    if (attachmentInfo) {
      body.attachment_url = attachmentInfo.url;
      body.attachment_name = attachmentInfo.original_name;
      body.attachment_type = attachmentInfo.file_type;
      body.attachment_size = attachmentInfo.file_size;
      body.attachment_text = attachmentInfo.text_content || null;
    }

    const res = await fetch('/api/meeting/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      note.innerText = err.detail || '发送失败';
      sendBtn.disabled = false;
      return;
    }

    input.value = '';
    clearPendingFile();
    input.focus();
    sendBtn.disabled = false;
  } catch (e) {
    note.innerText = '发送失败，请检查网络';
    sendBtn.disabled = false;
  }
}

// ── 键盘事件 ──────────────────────────────────────────
input.addEventListener('keydown', (ev) => {
  if (ev.key === 'Enter' && !ev.shiftKey) {
    // Enter 直接发送，Shift+Enter 换行
    ev.preventDefault();
    sendMessage();
  }
});

// ── 初始化 ────────────────────────────────────────────
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
window.addEventListener('beforeunload', () => {
  if (pollingTimer) clearInterval(pollingTimer);
});

init();
