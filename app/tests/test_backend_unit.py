import pytest

class FakeUser:
    def __todict__(self):
        return {
            "id": 1,
            "username": "testuser",
            "email": "test@mail.com"
        }

def test_health_check_success(client, mocker):
    """
        Test /api/health endpoint simulating a healthy database connection (200).
    """

    # mock of db call to return a successful result
    mock_execute = mocker.patch('src.main.db.session.execute')
    
    # API call
    response = client.get('/api/health')

    # verify that the db call was made exactly once
    mock_execute.assert_called_once()
    
    # assertion: status code 200 and response body contains "healthy"
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_health_check_db_failure(client, mocker):
    """
        Test /api/health endpoint simulating a database failure (503).
    """

    # mock of db call to raise an exception simulating DB offline
    mock_execute = mocker.patch('src.main.db.session.execute', side_effect=Exception("DB Offline"))
    
    # API call
    response = client.get('/api/health')

    # verify that the db call was made exactly once
    mock_execute.assert_called_once()
    
    # assertion: status code 503 and response body contains "unhealthy"
    assert response.status_code == 503
    assert response.get_json()["status"] == "unhealthy"

    
def test_get_users(client, mocker):
    '''
        Test /api/users endpoint to ensure it returns a list of users.
    '''

    # mock of db call to return the mocked user
    mock_execute = mocker.patch('src.main.User.query')
    mock_execute.all.return_value = [FakeUser()]

    # API call
    response = client.get('/api/users')
    data = response.get_json()

    assert response.status_code == 200
    assert data[0]["username"] == "testuser"
    assert data[0]["email"] == "test@mail.com"

def test_get_users_delay(client, mocker):
    '''
        Test /api/users endpoint simulating a delayed response.
    '''

    # mock of db call to return the mocked user
    mock_execute = mocker.patch('src.main.User.query')
    mock_execute.all.return_value = [FakeUser()]

    # mock of time.sleep to simulate delay
    mock_sleep = mocker.patch('src.main.time.sleep', return_value=None)

    # API call
    response = client.get('/api/users?delay=2')
    data = response.get_json()

    # verify that time.sleep was called with the correct delay
    mock_sleep.assert_called_once_with(2)

    assert response.status_code == 200
    assert data[0]["username"] == "testuser"
    assert data[0]["email"] == "test@mail.com"

    
    