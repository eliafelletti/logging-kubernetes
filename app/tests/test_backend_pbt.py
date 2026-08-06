from hypothesis import HealthCheck, given, settings, strategies as st, assume
from pytest import raises
from src.models import db, User

class TestAppInvariants:
    @given(
            # blacklist_categories=['Cc', 'Cs'] to avoid control characters and surrogate pairs
            # control caracters like \n, \r or \t can cause issues in headers, and surrogate pairs can lead to encoding problems
            request_id=st.text(alphabet=st.characters(blacklist_categories=['Cc', 'Cs']), min_size=1, max_size=100)
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tracing_header(self, client, request_id):  
        """
            PROPERTY:
            The request-id into the header is correctly propagated and returned in the response.
        """
        headers = {"X-Request-ID": request_id}
        response = client.get("/api/health", headers=headers)

        # Check that the response status code is either 200 (OK) or 503 (Service Unavailable)
        assert response.status_code in [200, 503]

        # Check that the request-id header is present in the response and matches the one sent in the request
        assert response.headers.get("X-Request-ID") == request_id


    @given(
            random_path=st.text(alphabet=st.characters(blacklist_categories=('Cs',)), min_size=1, max_size=30)
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_json_response_guarantee(self, client, random_path):
        """
            PROPERTY:
            The application always returns a JSON response, even for random or invalid paths.
        """
        response = client.get(f'/api/{random_path}')
        
        # response should always be JSON, even for invalid paths
        assert response.is_json is True
        assert response.headers['Content-Type'] == 'application/json'
        
        # Check that the response status code is in [200, 404, 405] (OK, Not Found, Method Not Allowed)
        # sometimes the random path might match an existing route, hence 200 is also valid
        assert response.status_code in [200, 404, 405]


    # generator for arbitrary JSON values (None, bool, int, float, str)
    json_values = st.one_of(
        st.none(), 
        st.booleans(), 
        st.integers(), 
        st.floats(allow_nan=False, allow_infinity=False), 
        st.text()
    )
    # fuzz JSON dictionary
    fuzz_payload = st.dictionaries(keys=st.text(), values=json_values)

    @given(
            payload = fuzz_payload
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_robustness_fuzz_user_creation(self, client, payload):
        """
            PROPERTY:
            For every fuzzy payload sent to the user creation endpoint, the application should not crash and return a valid JSON response with an appropriate status code (201, 400, or 409).
        """
        response = client.post('/api/user', json=payload)
        
        # Check that the response status code is either 201 (Created), 400 (Bad Request) or 409 (Conflict)
        assert response.status_code in [201, 400, 409]
        
        # Check that the response is always JSON
        assert response.is_json is True
        assert response.headers['Content-Type'] == 'application/json'


    @given(
                username = st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=3, max_size=20),
                email = st.emails(),
                payload = fuzz_payload
            )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_robustness_fuzz_user_update(self, client, payload, username, email):
        """
            PROPERTY:
            For every fuzzy payload sent to the user update endpoint, the application should not crash and return a valid JSON response with an appropriate status code (200, 201, 400, or 409).
        """
        # Clean User table before starting the test
        db.session.query(User).delete()
        db.session.commit()
        db.session.expunge_all()  # Clear the session to avoid SQLAlchemy Identity Map stale data

        # Create a valid user to update
        res_post = client.post('/api/user', json={'username': username, 'email': email})
        assert res_post.status_code == 201

        response = client.put('/api/user/1', json=payload)
        
        # Check that the response status code is either 201 (Created), 400 (Bad Request) or 409 (Conflict)
        assert response.status_code in [200, 201, 400, 409]
        
        # Check that the response is always JSON
        assert response.is_json is True
        assert response.headers['Content-Type'] == 'application/json'

class TestCRUDUsersProperties:
    valid_usernames = st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), 
        min_size=3, 
        max_size=20
    )
    valid_emails = st.emails()

    @given(
            username=valid_usernames,
            email=valid_emails
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_user_complete_lifecycle(self, client, username, email):
        """
            PROPERTY:
            For every user created, it should be possible to retrieve it, update it, and delete it. After that the retrieval should return 404
        """
        # Clean User table before starting the test
        db.session.query(User).delete()
        db.session.commit()

        # 1. CREATE (POST)
        post_res = client.post('/api/user', json={'username': username, 'email': email})
        assert post_res.status_code == 201
        created_user = post_res.get_json()
        user_id = created_user['id'] # retrieve user id for further operations

        # 2. READ (GET)
        get_res = client.get(f'/api/user/{user_id}')
        assert get_res.status_code == 200
        fetched_user = get_res.get_json()
        assert fetched_user['username'] == username
        assert fetched_user['email'] == email

        # 3. UPDATE (PUT)
        new_email = f"updated_{email}"
        put_res = client.put(f'/api/user/{user_id}', json={'email': new_email})
        assert put_res.status_code == 200
        updated_user = put_res.get_json()
        assert updated_user['email'] == new_email

        # 4. DELETE (DELETE)
        del_res = client.delete(f'/api/user/{user_id}')
        assert del_res.status_code == 200
        assert del_res.get_json()['message'] == "User deleted successfully"

        # 5. VERIFY DELETED (GET -> 404)
        get_after_del = client.get(f'/api/user/{user_id}')
        assert get_after_del.status_code == 404


    @given(
            username=valid_usernames,
            email=valid_emails
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_create_unique_constraint(self, client, username, email):
        """
            PROPERTY:
            The database enforces unique constraints on username and email during creation. Attempting to create a user with an existing username or email should return a 409 Conflict status code.
        """
        # Clean User table before starting the test
        db.session.query(User).delete()
        db.session.commit()

        # Create the first user
        post_res1 = client.post('/api/user', json={'username': username, 'email': email})
        assert post_res1.status_code == 201

        # Attempt to create a second user with the same username
        post_res2 = client.post('/api/user', json={'username': username, 'email': f"new_{email}"})
        assert post_res2.status_code == 409
        assert post_res2.get_json()['error'] == "Username or email already exists (or DB error)"

        # Attempt to create a second user with the same email
        post_res3 = client.post('/api/user', json={'username': f"new_{username}", 'email': email})
        assert post_res3.status_code == 409
        assert post_res3.get_json()['error'] == "Username or email already exists (or DB error)"


    @given(
            user1_name=valid_usernames,
            user1_email=valid_emails,
            user2_name=valid_usernames,
            user2_email=valid_emails
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_update_unique_constraint(self, client, user1_name, user1_email, user2_name, user2_email):
        """
            PROPERTY:
            The database enforces unique constraints on username and email during updates. Attempting to update a user to have an existing username or email should return a 409 Conflict status code.
        """
        # Assume that the two users have different usernames and emails
        # This is necessary to prevent Hypothesis from generating the same username/email for both users, which would make the test invalid
        assume(user1_name != user2_name)
        assume(user1_email != user2_email)

        # Clean User table before starting the test
        db.session.query(User).delete()
        db.session.commit()
        db.session.expunge_all()  # Clear the session to avoid SQLAlchemy Identity Map stale data

        # Create User 1 and User 2
        post_res1 = client.post('/api/user', json={'username': user1_name, 'email': user1_email})
        assert post_res1.status_code == 201

        post_res2 = client.post('/api/user', json={'username': user2_name, 'email': user2_email})
        assert post_res2.status_code == 201
        
        user1_id = post_res1.get_json()['id']

        # User 1 tries to steal User 2's email
        put_res = client.put(f'/api/user/{user1_id}', json={'username': user1_name, 'email': user2_email})
        
        assert put_res.status_code == 409