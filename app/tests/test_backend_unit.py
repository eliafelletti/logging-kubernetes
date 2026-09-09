import pytest
from werkzeug.exceptions import NotFound

class FakeUser:
    def __init__(self):
        self.id = 1
        self.username = "testuser"
        self.email = "test@mail.com"
    
    def __todict__(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
        }

# generator to simulate time.time() increasing by 10 seconds on each call
def time_side_effect():
    t = 0.0
    while True:
        yield t
        t += 1000.0

"""   CRUD Tests on users   """   

def test_get_users(client, mocker):
    '''
        Test /api/users endpoint to ensure it returns a list of users.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.all.return_value = [FakeUser()]

    # API call
    response = client.get('/api/users')
    data = response.get_json()

    # verify that the query was executed once
    mock_query.all.assert_called_once() 

    assert response.status_code == 200
    assert data[0]["username"] == "testuser"
    assert data[0]["email"] == "test@mail.com"

def test_get_users_delay(client, mocker):
    '''
        Test /api/users endpoint simulating a delayed response.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.all.return_value = [FakeUser()]

    # mock of time.sleep to simulate delay
    mock_sleep = mocker.patch('src.main.time.sleep', return_value=None)

    # API call
    response = client.get('/api/users?delay=2')
    data = response.get_json()

    # verify that time.sleep was called with the correct delay
    mock_sleep.assert_called_once_with(2)

    # verify that the query was executed once
    mock_query.all.assert_called_once()

    assert response.status_code == 200
    assert data[0]["username"] == "testuser"
    assert data[0]["email"] == "test@mail.com"

def test_get_user_delay_out_of_bounds(client):
    """
        Test /api/users endpoint with a delay value exceeding max threshold (>10). 
    """

    # API call with out-of-bounds delay
    response = client.get('/api/users?delay=15')

    assert response.status_code == 400
    assert response.get_json()["error"] == "Delay parameter must be between 0 and 10"

def test_get_user_delay_negative(client):
    """
        Test /api/users endpoint with a negative delay value (<0). 
    """

    # API call with negative delay
    response = client.get('/api/users?delay=-1')

    assert response.status_code == 400
    assert response.get_json()["error"] == "Delay parameter must be between 0 and 10"

def test_get_user_delay_invalid_type(client):
    """
        Test /api/users endpoint with a non-integer delay parameter. 
    """

    # API call with invalid delay type (string)
    response = client.get('/api/users?delay=abc')
    
    assert response.status_code == 400
    assert response.get_json()["error"] == "Delay parameter must be an integer"
  
def test_get_user_by_id(client, mocker):
    '''
        Test /api/users/<id> endpoint to ensure it returns the correct user.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.return_value = FakeUser()

    # API call
    response = client.get('/api/user/1')
    data = response.get_json()

    # verify that the query was executed once with the correct ID
    mock_query.get_or_404.assert_called_once_with(1)

    assert response.status_code == 200
    assert data["username"] == "testuser"
    assert data["email"] == "test@mail.com"

def test_get_user_by_id_not_found(client, mocker):
    '''
        Test /api/users/<id> endpoint to ensure it returns 404 for non-existent user.
    '''

    # mock of db call to return None simulating user not found
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.side_effect = NotFound()

    # API call
    response = client.get('/api/user/999999999999')

    # verify that the query was executed once with the correct ID
    mock_query.get_or_404.assert_called_once_with(999999999999)

    assert response.status_code == 404
    assert response.get_json()["error"] == "Resource not found"



def test_create_user(client):
    '''
        Test /api/user endpoint to ensure it creates a new user.
    '''

    # API call
    response = client.post('/api/user', json={
        "username": "newuser",
        "email": "newuser@mail.com"
    })

    assert response.status_code == 201
    assert response.get_json()["username"] == "newuser"
    assert response.get_json()["email"] == "newuser@mail.com"

def test_create_user_error(client, mocker):
    '''
        Test /api/user endpoint to ensure it returns 409
    '''

    # mock of db call to raise an exception simulating conflict
    mock_add = mocker.patch('src.main.db.session.add', side_effect=Exception("Conflict"))
    mock_rollback = mocker.patch('src.main.db.session.rollback')

    # API call
    response = client.post('/api/user', json={
        "username": "newuser",
        "email": "newuser@mail.com"
    })

    # verify that the db session add and rollback were called
    mock_add.assert_called_once()
    mock_rollback.assert_called_once()

    assert response.status_code == 409
    assert response.get_json()["error"] == "Username or email already exists (or DB error)"

def test_create_user_no_data(client):
    '''
        Test /api/user endpoint to ensure it returns 400 for invalid input data.
    '''

    # API call with missing username
    response = client.post('/api/user', json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid request, username and email are required"

def test_create_user_missing_email(client):
    '''
        Test /api/user endpoint to ensure it returns 400 for invalid input data.
    '''

    # API call with missing email
    response = client.post('/api/user', json={
        "username": "newuser"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid request, username and email are required"

def test_create_user_missing_username(client):
    '''
        Test /api/user endpoint to ensure it returns 400 for invalid input data.
    '''

    # API call with missing username
    response = client.post('/api/user', json={
        "email": "newuser@mail.com"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid request, username and email are required"



def test_update_user(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it updates an existing user.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_user = FakeUser()
    mock_query.get_or_404.return_value = mock_user

    # mock of db session commit to do nothing
    mock_commit = mocker.patch('src.main.db.session.commit')

    # API call
    response = client.put('/api/user/1', json={
        "username": "updateduser",
        "email": "updateduser@mail.com"
    })

    # verify that the db session commit was called once
    mock_commit.assert_called_once()

    assert response.status_code == 200
    assert response.get_json()["username"] == "updateduser"
    assert response.get_json()["email"] == "updateduser@mail.com"

def test_update_user_not_found(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it returns 404 for non-existent user.
    '''

    # mock of db call to return None simulating user not found
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.side_effect = NotFound()

    # API call
    response = client.put('/api/user/999999999999', json={
        "username": "updateduser",
        "email": "updateduser@mail.com"
    })

    assert response.status_code == 404  
    assert response.get_json()["error"] == "Resource not found"

def test_update_user_no_data(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it returns 400 for invalid input data.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.return_value = FakeUser()

    # API call
    response = client.put('/api/user/1', json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "No data provided"

def test_update_user_only_username(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it updates only the username.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_user = FakeUser()
    mock_query.get_or_404.return_value = mock_user

    # mock of db session commit to do nothing
    mock_commit = mocker.patch('src.main.db.session.commit')

    # API call
    response = client.put('/api/user/1', json={
        "username": "updateduser"
    })

    # verify that the db session commit was called once
    mock_commit.assert_called_once()

    assert response.status_code == 200
    assert response.get_json()["username"] == "updateduser"
    assert response.get_json()["email"] == "test@mail.com"  # email should remain unchanged

def test_update_user_only_email(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it updates only the email.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_user = FakeUser()
    mock_query.get_or_404.return_value = mock_user

    # mock of db session commit to do nothing
    mock_commit = mocker.patch('src.main.db.session.commit')  

    # API call
    response = client.put('/api/user/1', json={
        "email": "updateduser@mail.com"
    })

    # verify that the db session commit was called once
    mock_commit.assert_called_once()

    assert response.status_code == 200
    assert response.get_json()["email"] == "updateduser@mail.com"
    assert response.get_json()["username"] == "testuser"  # username should remain unchanged

def test_update_error(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it returns 409 on update conflict.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.return_value = FakeUser()

    # mock of db session commit to raise an exception simulating conflict
    mock_commit = mocker.patch('src.main.db.session.commit', side_effect=Exception("Conflict"))
    mock_rollback = mocker.patch('src.main.db.session.rollback')

    # API call
    response = client.put('/api/user/1', json={
        "username": "updateduser",
        "email": "updateduser@mail.com"
    })

    # verify that the db session commit and rollback were called once
    mock_commit.assert_called_once()
    mock_rollback.assert_called_once()

    assert response.status_code == 409
    assert response.get_json()["error"] == "Username or email already exists (or DB error)"



def test_delete_user(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it deletes an existing user.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.return_value = FakeUser()

    # mock of db session delete and commit to do nothing
    mock_delete = mocker.patch('src.main.db.session.delete')
    mock_commit = mocker.patch('src.main.db.session.commit')

    # API call
    response = client.delete('/api/user/1')

    # verify that the db session delete and commit were called once
    mock_delete.assert_called_once()
    mock_commit.assert_called_once()

    assert response.status_code == 200
    assert response.get_json()["message"] == "User deleted successfully"

def test_delete_user_not_found(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it returns 404 for non-existent user.
    '''

    # mock of db call to return None simulating user not found
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.side_effect = NotFound()

    # API call
    response = client.delete('/api/user/999999999999')

    assert response.status_code == 404
    assert response.get_json()["error"] == "Resource not found"

def test_delete_user_error(client, mocker):
    '''
        Test /api/user/<id> endpoint to ensure it returns 500 on delete error.
    '''

    # mock of db call to return the mocked user
    mock_query = mocker.patch('src.main.User.query')
    mock_query.get_or_404.return_value = FakeUser()

    # mock of db session delete and commit to raise an exception simulating error
    mock_delete = mocker.patch('src.main.db.session.delete')
    mock_commit = mocker.patch('src.main.db.session.commit', side_effect=Exception("DB Error"))
    mock_rollback = mocker.patch('src.main.db.session.rollback')

    # API call
    response = client.delete('/api/user/1')

    # verify that the db session delete, commit, and rollback were called once
    mock_delete.assert_called_once()
    mock_commit.assert_called_once()
    mock_rollback.assert_called_once()

    assert response.status_code == 500
    assert "DB error during deletion" in response.get_json()["error"]

"""   Extra features tests   """

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



def test_panic_button(client):
    """
        Test /api/panic endpoint to ensure it simulates a server crash and raises an exception.
    """
    
    with pytest.raises(Exception, match="Simulated server crash for testing purposes"):
        client.get('/api/panic')



def test_log_storm_default(client):
    """
        Test /api/log_storm endpoint to ensure it generates 100 log messages.
    """

    # API call
    response = client.get('/api/log_storm')
    data = response.get_json()

    assert response.status_code == 200
    assert data["message"] == "Generati 100 log strutturati"

def test_log_storm_custom_count(client):
    """
        Test /api/log_storm endpoint to ensure it generates a custom number of log messages.
    """

    # API call with custom count
    response = client.get('/api/log_storm?count=50')
    data = response.get_json()

    assert response.status_code == 200
    assert data["message"] == "Generati 50 log strutturati"

def test_log_storm_count_out_of_bounds(client):
    """
        Test /api/log_storm endpoint with count exceeding upper limit (>1000).
    """

    # API call with out-of-bounds count
    response = client.get('/api/log_storm?count=1500')

    assert response.status_code == 400
    assert response.get_json()["error"] == "Count parameter must be between 0 and 1000"


def test_log_storm_count_invalid_type(client):
    """ 
        Test /api/log_storm endpoint with a non-integer count parameter. 
    """

    # API call with invalid count type (string)
    response = client.get('/api/log_storm?count=not_a_number')

    assert response.status_code == 400
    assert response.get_json()["error"] == "Count parameter must be an integer"



def test_stress_cpu(client, mocker):
    """
        Test /api/stress_cpu endpoint to ensure it simulates CPU stress with default duration (5 seconds)
    """

    # mock of time.time
    mocker.patch('src.main.time.time', side_effect=time_side_effect())

    # API call
    response = client.get('/api/stress_cpu')
    data = response.get_json()

    assert response.status_code == 200
    assert data["message"] == "CPU stress test completed after 5 seconds"

def test_stress_cpu_custom_duration(client, mocker):
    """
        Test /api/stress_cpu endpoint to ensure it simulates CPU stress with a custom duration
    """

    # mock of time.time
    mocker.patch('src.main.time.time', side_effect=time_side_effect())

    # API call with custom duration
    response = client.get('/api/stress_cpu?duration=10')
    data = response.get_json()

    assert response.status_code == 200
    assert data["message"] == "CPU stress test completed after 10 seconds"

def test_stress_cpu_out_of_bounds_duration(client):
    """
        Test /api/stress_cpu endpoint with duration outside valid limits (1-20s). 
    """

    # API call with out-of-bounds duration
    response = client.get('/api/stress_cpu?duration=60')

    assert response.status_code == 400
    assert response.get_json()["error"] == "Duration parameter must be between 1 and 20 seconds"


def test_stress_cpu_invalid_type_duration(client):
    """
        Test /api/stress_cpu endpoint with a non-integer duration parameter.
    """

    # API call with invalid duration type (string)
    response = client.get('/api/stress_cpu?duration=invalid_val')

    assert response.status_code == 400
    assert response.get_json()["error"] == "Duration parameter must be an integer"

def test_index_page(client):
    """
        Test / endpoint to ensure it returns the correct HTML content.
    """

    # API call
    response = client.get('/')
    data = response.data.decode('utf-8')

    assert response.status_code == 200
    assert "<span class=\"navbar-brand mb-0 h1\">🛠️ Flask Microservice - Control Panel</span>" in data