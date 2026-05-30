async function loadMeeting() {
  const res = await fetch('/api/meeting/init', { method: 'POST' });
  if (!res.ok) {
    showMeetingEnded();
    return;
  }
  const data = await res.json();
  renderMeeting(data);
}

function renderMeeting(data) {
  const info = document.getElementById('meeting-info');
  info.innerHTML = `
    <h2>会议信息</h2>
    <p>会议名：${data.meeting_name}</p>
    <p>会议码：<b>${data.meeting_code}</b></p>
    <p>局域网地址：${data.join_url}</p>
    <p>在线人数：<span id="online-count">${data.online_count}</span></p>
    <img class="qr" src="${data.qr_data_url}" alt="二维码" />
  `;
  document.getElementById('meeting-name').value = data.meeting_name;
  document.getElementById('translation-enabled').value = String(data.translation_enabled);
  document.getElementById('summary-language').value = data.summary_language;
  setControlsEnabled(true);
}

function showMeetingEnded() {
  document.getElementById('meeting-info').innerHTML = `
    <h2>会议已结束</h2>
    <p>旧聊天窗口已经失效。需要继续使用时，请创建新会议。</p>
  `;
  document.getElementById('members').innerHTML = '';
  document.getElementById('summary-preview').innerText = '';
  setControlsEnabled(false);
}

function setControlsEnabled(enabled) {
  for (const id of ['save-settings', 'generate-summary', 'download-md', 'download-txt', 'dissolve']) {
    document.getElementById(id).disabled = !enabled;
  }
}

async function refreshStatus() {
  const res = await fetch('/api/meeting/status');
  if (!res.ok) {
    showMeetingEnded();
    return;
  }
  const data = await res.json();
  const members = document.getElementById('members');
  members.innerHTML = data.participants.map(p => `<li>${p.nickname} (${p.language}) ${p.online ? '在线' : '离线'}</li>`).join('');
  document.getElementById('online-count').innerText = data.online_count;
}

document.getElementById('create-meeting').onclick = async () => {
  const res = await fetch('/api/meeting/create', { method: 'POST' });
  const data = await res.json();
  renderMeeting(data);
  refreshStatus();
};

document.getElementById('save-settings').onclick = async () => {
  await fetch('/api/meeting/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      meeting_name: document.getElementById('meeting-name').value,
      translation_enabled: document.getElementById('translation-enabled').value === 'true',
      summary_language: document.getElementById('summary-language').value,
    })
  });
  refreshStatus();
};

document.getElementById('generate-summary').onclick = async () => {
  const res = await fetch('/api/meeting/summary', { method: 'POST' });
  const data = await res.json();
  document.getElementById('summary-preview').innerText = data.summary || data.detail;
};

document.getElementById('download-md').onclick = () => { window.location.href = '/api/meeting/summary/download?fmt=md'; };
document.getElementById('download-txt').onclick = () => { window.location.href = '/api/meeting/summary/download?fmt=txt'; };

document.getElementById('dissolve').onclick = async () => {
  await fetch('/api/meeting/dissolve', { method: 'POST' });
  showMeetingEnded();
};

loadMeeting();
setInterval(refreshStatus, 3000);
