from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_meeting_init_and_status():
    res = client.post('/api/meeting/create')
    assert res.status_code == 200
    data = res.json()
    assert data['meeting_code']

    status = client.get('/api/meeting/status')
    assert status.status_code == 200
    assert 'meeting_name' in status.json()


def test_join_and_summary_and_dissolve():
    init = client.post('/api/meeting/create').json()
    code = init['meeting_code']
    room_id = init['room_id']

    join = client.post('/api/meeting/join', json={
        'meeting_code': code,
        'nickname': '测试用户',
        'language': 'zh',
        'participant_id': 'u-test-1',
    })
    assert join.status_code == 200

    message = client.post('/api/meeting/message', json={
        'room_id': room_id,
        'participant_id': 'u-test-1',
        'sender_name': '测试用户',
        'sender_language': 'zh',
        'text': '你好',
    })
    assert message.status_code == 200

    messages = client.get('/api/meeting/messages', params={
        'room_id': room_id,
        'participant_id': 'u-test-1',
    })
    assert messages.status_code == 200
    assert messages.json()['messages'][0]['original_text'] == '你好'

    legacy_messages = client.get('/api/meeting/messages', params={'from_index': 0})
    assert legacy_messages.status_code == 200
    assert legacy_messages.json()['inactive'] is True

    summary = client.post('/api/meeting/summary')
    assert summary.status_code == 200
    assert 'summary' in summary.json()

    dissolve = client.post('/api/meeting/dissolve')
    assert dissolve.status_code == 200

    old_message = client.post('/api/meeting/message', json={
        'room_id': room_id,
        'participant_id': 'u-test-1',
        'sender_name': '测试用户',
        'sender_language': 'zh',
        'text': '会议结束后不应发送',
    })
    assert old_message.status_code == 404
