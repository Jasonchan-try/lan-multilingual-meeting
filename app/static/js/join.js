function makeParticipantId() {
  if (window.crypto && typeof window.crypto.randomUUID === 'function') {
    return window.crypto.randomUUID();
  }
  return `p-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function setMessage(text) {
  document.getElementById('join-message').innerText = text;
}

async function joinMeeting() {
  try {
    const payload = {
      meeting_code: document.getElementById('meeting-code').value.trim(),
      nickname: document.getElementById('nickname').value.trim(),
      language: document.getElementById('language').value,
      participant_id: makeParticipantId(),
    };

    if (!payload.meeting_code || !payload.nickname) {
      setMessage('请填写会议码和昵称');
      return;
    }

    const res = await fetch('/api/meeting/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      setMessage(err.detail || '加入失败');
      return;
    }

    const data = await res.json();
    sessionStorage.setItem('participant', JSON.stringify({
      ...payload,
      room_id: data.room_id,
    }));
    location.href = '/chat';
  } catch (e) {
    setMessage(`加入失败：${e && e.message ? e.message : '未知错误'}`);
  }
}

const code = new URLSearchParams(location.search).get('code');
if (code) document.getElementById('meeting-code').value = code;
document.getElementById('join-btn').addEventListener('click', joinMeeting);
