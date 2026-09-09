from locust import HttpUser, task, between
import random

class ThesisChaosUser(HttpUser):
    # Every fake user will wait between 1 and 3 seconds before executing the next task
    wait_time = between(1, 3)

    @task(10)  # Weight 10: Very frequent
    def get_users(self):
        self.client.get("/api/users")

    @task(10)  # Weight 10: Very frequent
    def health_check(self):
        self.client.get("/api/health")

    @task(3)   # Weight 3: Less frequent
    def log_storm(self):
        # Generate a random count between 10 and 50 for the log storm
        count = random.randint(10, 50)
        self.client.get(f"/api/log_storm?count={count}")

    @task(2)   # Weight 2: Even less frequent (puts load on the CPU)
    def stress_cpu(self):
        self.client.get("/api/stress_cpu?duration=2")

    @task(1)   # Weight 1: Rare (the Panic causes a 500 error)
    def trigger_panic(self):
        # catch_response=True is used to tell Locust not to consider the 500 as a "test error", but as an expected behavior
        with self.client.get("/api/panic", catch_response=True) as response:
            if response.status_code == 500:
                response.success()