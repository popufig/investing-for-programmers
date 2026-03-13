from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import InvestmentThesis, ThesisCheckpoint, ThesisTicker  # noqa: E402
import backend.routers.thesis as thesis_router  # noqa: E402


@pytest.fixture
def db_setup():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_setup):
    return db_setup[0]


def test_thesis_crud_and_checkpoint_flow(client, monkeypatch):
    monkeypatch.setattr(thesis_router, '_baseline_close_price', lambda ticker: 10.0)

    create_resp = client.post(
        '/api/thesis',
        json={
            'title': 'Rates down will re-rate LiDAR',
            'summary': 'Macro thesis for next 6 months',
            'tickers': ['AEVA', 'LAZR', 'INVZ', 'OUST'],
            'category': 'macro',
            'status': 'active',
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    thesis_id = created['id']
    assert len(created['tickers']) == 4
    assert created['tickers'][0]['baseline_price'] == 10.0

    list_resp = client.get('/api/thesis', params={'status': 'active'})
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert any(row['id'] == thesis_id for row in rows)

    update_resp = client.put(
        f'/api/thesis/{thesis_id}',
        json={
            'status': 'validated',
            'tickers': ['AEVA', 'LAZR'],
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated['status'] == 'validated'
    assert len(updated['tickers']) == 2

    cp_resp = client.post(
        f'/api/thesis/{thesis_id}/checkpoints',
        json={
            'note': 'Fed cut 25bp, thesis still on track',
            'status_at_check': 'on_track',
        },
    )
    assert cp_resp.status_code == 201
    assert cp_resp.json()['status_at_check'] == 'on_track'

    detail_resp = client.get(f'/api/thesis/{thesis_id}')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail['status'] == 'validated'
    assert len(detail['checkpoints']) == 1


def test_thesis_snapshot_and_delete_cascade(client, monkeypatch):
    monkeypatch.setattr(thesis_router, '_baseline_close_price', lambda ticker: 10.0)
    monkeypatch.setattr(
        thesis_router,
        'get_multiple_quotes',
        lambda tickers: {
            ticker: {
                'current_price': 12.5,
                'change_pct': 1.2,
            }
            for ticker in tickers
        },
    )

    create_resp = client.post(
        '/api/thesis',
        json={
            'title': 'Vision replacement risk for LiDAR',
            'summary': 'Competitive thesis',
            'tickers': ['LAZR', 'OUST'],
            'category': 'sector',
            'status': 'active',
        },
    )
    thesis_id = create_resp.json()['id']

    cp_resp = client.post(
        f'/api/thesis/{thesis_id}/checkpoints',
        json={'note': 'Competitive launch observed', 'status_at_check': 'at_risk'},
    )
    assert cp_resp.status_code == 201

    snapshot_resp = client.get(f'/api/thesis/{thesis_id}/snapshot')
    assert snapshot_resp.status_code == 200
    snapshot = snapshot_resp.json()
    assert snapshot['thesis_id'] == thesis_id
    assert len(snapshot['tickers']) == 2
    assert snapshot['tickers'][0]['baseline_price'] == 10.0
    assert snapshot['tickers'][0]['current_price'] == 12.5
    assert snapshot['tickers'][0]['change_pct'] == 25.0

    delete_resp = client.delete(f'/api/thesis/{thesis_id}')
    assert delete_resp.status_code == 200

    missing_resp = client.get(f'/api/thesis/{thesis_id}')
    assert missing_resp.status_code == 404


def test_thesis_create_validates_payload(client):
    bad_title_resp = client.post(
        '/api/thesis',
        json={'title': '   ', 'tickers': ['LAZR'], 'status': 'active'},
    )
    assert bad_title_resp.status_code == 400
    assert 'title' in bad_title_resp.json()['detail']

    no_ticker_resp = client.post(
        '/api/thesis',
        json={'title': 'Missing tickers', 'tickers': [], 'status': 'active'},
    )
    assert no_ticker_resp.status_code == 400
    assert 'ticker' in no_ticker_resp.json()['detail'].lower()

    bad_status_resp = client.post(
        '/api/thesis',
        json={'title': 'Bad status', 'tickers': ['LAZR'], 'status': 'unknown'},
    )
    assert bad_status_resp.status_code == 400
    assert 'status' in bad_status_resp.json()['detail'].lower()


def test_thesis_update_and_checkpoint_validation_errors(client, monkeypatch):
    monkeypatch.setattr(thesis_router, '_baseline_close_price', lambda ticker: 10.0)
    created = client.post(
        '/api/thesis',
        json={'title': 'Validation thesis', 'tickers': ['LAZR'], 'status': 'active'},
    )
    assert created.status_code == 201
    thesis_id = created.json()['id']

    bad_update = client.put(
        f'/api/thesis/{thesis_id}',
        json={'status': 'bad_status'},
    )
    assert bad_update.status_code == 400
    assert 'status' in bad_update.json()['detail'].lower()

    empty_tickers_update = client.put(
        f'/api/thesis/{thesis_id}',
        json={'tickers': []},
    )
    assert empty_tickers_update.status_code == 400
    assert 'ticker' in empty_tickers_update.json()['detail'].lower()

    bad_checkpoint_status = client.post(
        f'/api/thesis/{thesis_id}/checkpoints',
        json={'note': 'test', 'status_at_check': 'bad_status'},
    )
    assert bad_checkpoint_status.status_code == 400
    assert 'status' in bad_checkpoint_status.json()['detail'].lower()

    blank_checkpoint_note = client.post(
        f'/api/thesis/{thesis_id}/checkpoints',
        json={'note': '   ', 'status_at_check': 'on_track'},
    )
    assert blank_checkpoint_note.status_code == 400
    assert 'note' in blank_checkpoint_note.json()['detail'].lower()


def test_thesis_filter_and_not_found_paths(client):
    bad_filter = client.get('/api/thesis', params={'status': 'bad'})
    assert bad_filter.status_code == 400
    assert 'status' in bad_filter.json()['detail'].lower()

    missing_detail = client.get('/api/thesis/99999')
    assert missing_detail.status_code == 404

    missing_snapshot = client.get('/api/thesis/99999/snapshot')
    assert missing_snapshot.status_code == 404

    missing_delete = client.delete('/api/thesis/99999')
    assert missing_delete.status_code == 404


def test_thesis_delete_removes_children_rows(db_setup, monkeypatch):
    client, session_factory = db_setup
    monkeypatch.setattr(thesis_router, '_baseline_close_price', lambda ticker: 10.0)

    create_resp = client.post(
        '/api/thesis',
        json={'title': 'Cascade check', 'tickers': ['LAZR', 'OUST'], 'status': 'active'},
    )
    assert create_resp.status_code == 201
    thesis_id = create_resp.json()['id']

    cp_resp = client.post(
        f'/api/thesis/{thesis_id}/checkpoints',
        json={'note': 'checkpoint', 'status_at_check': 'on_track'},
    )
    assert cp_resp.status_code == 201

    with session_factory() as db:
        assert db.query(InvestmentThesis).count() == 1
        assert db.query(ThesisTicker).count() == 2
        assert db.query(ThesisCheckpoint).count() == 1

    delete_resp = client.delete(f'/api/thesis/{thesis_id}')
    assert delete_resp.status_code == 200

    with session_factory() as db:
        assert db.query(InvestmentThesis).count() == 0
        assert db.query(ThesisTicker).count() == 0
        assert db.query(ThesisCheckpoint).count() == 0
