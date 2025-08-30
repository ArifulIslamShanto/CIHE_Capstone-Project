import pytest
import sys, os
from PIL import Image
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_register_pending_success(client, mocker):
    # Mock DB lookup
    mocker.patch("app.get_user_by_username", return_value=None)

    payload = {
        "full_name": "Alzina Test",
        "phone_number": "9812345678",
        "username": "alzinatest",
        "email": "alzina@example.com",
        "password": "password123"
    }
    resp = client.post("/api/register_pending", json=payload)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["ok"] is True
    assert "Capture embeddings" in data["message"]

import numpy as np

def test_upload_frame_with_face(client, mocker):
    # Fake image
    dummy_img = np.zeros((160, 160, 3), dtype=np.uint8)
    
    mocker.patch("app.extract_face_region", return_value=dummy_img)
    mocker.patch("app.preprocess_face", return_value=dummy_img)
    mocker.patch("app.get_embedding", return_value=np.ones(128))
    mocker.patch("app.Image.open", return_value=Image.new("RGB", (10, 10)))

    payload = {"username": "alzinatest", "image": "data:image/jpeg;base64,AAAA"}
    resp = client.post("/api/upload_frame", json=payload)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["ok"] is True
    assert "count" in data

def test_finalize_success(client, mocker):
    # Setup pending user & embeddings
    from app import pending_users, buffers, EMBED_SAMPLES_TARGET
    username = "alzinatest"
    pending_users[username] = {
        "full_name": "Alzina Test",
        "phone_number": "9812345678",
        "email": "alzina@example.com",
        "password": "password123"
    }
    buffers[username] = [np.ones(128)] * EMBED_SAMPLES_TARGET

    mocker.patch("app.create_user", return_value=1)
    mocker.patch("app.save_average_embedding", return_value=None)

    resp = client.post("/api/finalize", json={"username": username})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["ok"] is True
    assert "user_id" in data

def test_login_and_otp(client, mocker):
    # Mock user lookup and bcrypt
    fake_user = {"id": 1, "username": "alzinatest", "password": "$2b$12$hashedpw", "email": "alzina@example.com"}
    mocker.patch("app.get_user_by_username", return_value=fake_user)
    mocker.patch("bcrypt.checkpw", return_value=True)
    mocker.patch("app.send_email", return_value=None)
    mocker.patch("app.get_db_connection")  # avoid real DB

    resp = client.post("/api/login", json={"username": "alzinatest", "password": "password123"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["redirect"] == "otp-page"

from app import send_email, EMAIL_SENDER

def test_send_email_success(mocker):
    # Mock smtplib.SMTP
    mock_smtp = mocker.patch("app.smtplib.SMTP", autospec=True)
    mock_server = mock_smtp.return_value.__enter__.return_value

    # Call the function
    send_email("test@example.com", "Test Subject", "This is a test email sent by alzina using pytest")

    # Assertions
    mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with(EMAIL_SENDER, "mfsimuhpkdrjpdnm")
    mock_server.send_message.assert_called_once()

    # Verify the actual message content
    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg["Subject"] == "Test Subject"
    assert sent_msg["To"] == "test@example.com"
    assert "This is a test email sent by alzina using pytest" in sent_msg.get_payload()

def test_send_email_failure(mocker):
    # Mock SMTP to raise exception when instantiated
    mocker.patch("app.smtplib.SMTP", side_effect=Exception("Connection failed"))

    with pytest.raises(Exception) as excinfo:
        send_email("fail@example.com", "Fail Subject by alzina", "This email should fail.")

    # Assertions
    assert "Connection failed" in str(excinfo.value)
