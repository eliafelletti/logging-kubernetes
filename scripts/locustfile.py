from locust import HttpUser, task, between
import random

class ThesisChaosUser(HttpUser):
    # Ogni utente finto aspetta tra 1 e 3 secondi prima di fare un'altra richiesta
    wait_time = between(1, 3)

    @task(10)  # Peso 10: Molto frequente
    def get_users(self):
        self.client.get("/api/users")

    @task(10)  # Peso 10: Molto frequente
    def health_check(self):
        self.client.get("/api/health")

    @task(3)   # Peso 3: Meno frequente
    def log_storm(self):
        # Genera un numero casuale di log per variare il traffico
        count = random.randint(10, 50)
        self.client.get(f"/api/log_storm?count={count}")

    @task(8)   # Peso 8: Ancora meno frequente (pesa sulla CPU)
    def stress_cpu(self):
        self.client.get("/api/stress_cpu?duration=20")

    @task(1)   # Peso 1: Raro (il Panic fa restituire 500)
    def trigger_panic(self):
        # Usiamo catch_response=True per dire a Locust di non considerare 
        # il 500 come un "errore del test", ma come un comportamento atteso
        with self.client.get("/api/panic", catch_response=True) as response:
            if response.status_code == 500:
                response.success()