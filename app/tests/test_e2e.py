import re
from playwright.sync_api import Page, expect

def test_dashboard_is_online(page: Page, minikube_url: str):
    """
        Verify that the dashboard is online and accessible via the Minikube URL.
    """
    page.goto(minikube_url)

    # Upper section: Verify that the main elements of the dashboard are visible
    expect(page.get_by_text("Flask Microservice - Control Panel")).to_be_visible()

    # User Management Section: Verify that the user management section is visible and functional
    expect(page.get_by_text("Gestione Utenti (Database)")).to_be_visible()
    expect(page.get_by_placeholder("Username")).to_be_visible()
    expect(page.get_by_placeholder("Email")).to_be_visible()
    expect(page.get_by_role("button", name="Crea")).to_be_visible()

    # Chaos Engineering Section: Verify that the chaos engineering section is visible and functional
    expect(page.get_by_text("Chaos Engineering")).to_be_visible()
    expect(page.get_by_text("Ultima Risposta API")).to_be_visible()
    expect(page.get_by_text("In attesa di comandi...")).to_be_visible()

def test_chaos_health_check(page: Page, minikube_url: str):
    """
        Verify that the 'Health Check' button correctly calls the /api/health endpoint and displays the expected response.
    """
    page.goto(minikube_url)
    
    # Find the Health Check button using a case-insensitive regex match
    health_btn = page.get_by_role("button", name=re.compile(r"Health Check", re.IGNORECASE))
    expect(health_btn).to_be_visible()
    health_btn.click()
    
    # check that the response box shows the expected text indicating the API call is in progress
    response_box = page.locator("#api-response")
    expect(response_box).to_contain_text("Chiamata in corso verso /api/health...")
    
    # check that the response box eventually shows a successful status code (200) indicating the health check passed
    expect(response_box).to_contain_text("Status: 200")


def test_chaos_panic_button(page: Page, minikube_url: str):
    """
        Verify that the 'Panic' button generates a 500 error from the server 
        and that the JS handles it correctly without crashing (Status 500).
    """
    page.goto(minikube_url)
    
    panic_btn = page.get_by_role("button", name=re.compile(r"Panic", re.IGNORECASE))
    expect(panic_btn).to_be_visible()
    panic_btn.click()
    
    response_box = page.locator("#api-response")
    expect(response_box).to_contain_text("Chiamata in corso verso /api/panic...")
    
    # check that the response box eventually shows a 500 status code indicating the server error was handled
    expect(response_box).to_contain_text("Status: 500")


def test_chaos_log_storm(page: Page, minikube_url: str):
    """
        Verify that the 'Log Storm' button completes the request successfully.
    """
    page.goto(minikube_url)
    
    storm_btn = page.get_by_role("button", name=re.compile(r"Log Storm", re.IGNORECASE))
    expect(storm_btn).to_be_visible()
    storm_btn.click()
    
    response_box = page.locator("#api-response")
    expect(response_box).to_contain_text("Chiamata in corso verso /api/log_storm?count=50...")
    
    expect(response_box).to_contain_text("Status: 200")


def test_chaos_cpu_stress(page: Page, minikube_url: str):
    """
        Verify that the 'CPU Stress' button invokes the API and waits 
        correctly for the stress test to complete.
    """
    page.goto(minikube_url)
    
    stress_btn = page.get_by_role("button", name=re.compile(r"CPU Stress", re.IGNORECASE))
    expect(stress_btn).to_be_visible()
    stress_btn.click()
    
    response_box = page.locator("#api-response")
    expect(response_box).to_contain_text("Chiamata in corso verso /api/stress_cpu?duration=5...")
    
    # this test will take at least 5 seconds to complete, so we set a longer timeout for the expectation
    expect(response_box).to_contain_text("Status: 200", timeout=10000)