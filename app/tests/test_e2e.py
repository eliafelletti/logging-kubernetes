from playwright.sync_api import Page, expect

def test_dashboard_is_online(page: Page, minikube_url: str):
    """
        Verify that the dashboard is online and accessible via the Minikube URL.
    """
    page.goto(minikube_url)

    # 1. Navbar superiore
    expect(page.get_by_text("Flask Microservice - Control Panel")).to_be_visible()

    # 2. Sezione "Gestione Utenti (Database)"
    expect(page.get_by_text("Gestione Utenti (Database)")).to_be_visible()
    expect(page.get_by_placeholder("Username")).to_be_visible()
    expect(page.get_by_placeholder("Email")).to_be_visible()
    expect(page.get_by_role("button", name="Crea")).to_be_visible()

    # 3. Sezione "Chaos Engineering" e "Ultima Risposta API"
    expect(page.get_by_text("Chaos Engineering")).to_be_visible()
    expect(page.get_by_text("Ultima Risposta API")).to_be_visible()
    expect(page.get_by_text("In attesa di comandi...")).to_be_visible()
