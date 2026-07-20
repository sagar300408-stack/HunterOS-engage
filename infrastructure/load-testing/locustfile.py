from locust import HttpUser, task, between

class HunterOSUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """
        Runs when a user starts. We could authenticate here and grab a token.
        """
        # self.client.post("/api/v1/auth/login", data={"username": "...", "password": "..."})
        pass

    @task(3)
    def view_dashboard(self):
        """
        Simulate an executive viewing their dashboard.
        """
        # Normally this would be /api/v1/dashboard/summary but we'll hit health for the stub
        self.client.get("/api/v1/health")

    @task(1)
    def view_metrics(self):
        """
        Simulate fetching observability metrics.
        """
        self.client.get("/metrics")
