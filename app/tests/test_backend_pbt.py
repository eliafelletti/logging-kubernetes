from hypothesis import HealthCheck, given, settings, strategies as st
from pytest import raises

class TestAppInvariants:
    @given(
            # blacklist_categories=['Cc', 'Cs'] to avoid control characters and surrogate pairs
            # control caracters like \n, \r or \t can cause issues in headers, and surrogate pairs can lead to encoding problems
            request_id=st.text(alphabet=st.characters(blacklist_categories=['Cc', 'Cs']), min_size=1, max_size=100)
        )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tracing_header(self, client, request_id):  
        """
            Test that the request-id into the header is correctly propagated and returned in the response.
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
            Test that the application always returns a JSON response, even for random or invalid paths.
        """
        response = client.get(f'/api/{random_path}')
        
        # response should always be JSON, even for invalid paths
        assert response.is_json is True
        assert response.headers['Content-Type'] == 'application/json'
        
        # Check that the response status code is 404 for invalid paths (random)
        assert response.status_code in [404, 405]


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
            Test the robustness of the user creation endpoint by sending fuzzed payloads.
        """
        response = client.post('/api/user', json=payload)
        
        # Check that the response status code is either 201 (Created), 400 (Bad Request) or 409 (Conflict)
        assert response.status_code in [201, 400, 409]
        
        # Check that the response is always JSON
        assert response.is_json is True
        assert response.headers['Content-Type'] == 'application/json'
    