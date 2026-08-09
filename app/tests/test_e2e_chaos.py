import re
import uuid
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

""" Chaos Engineering Tests """    

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
    
    # this test will take at least 5 seconds to complete, so we set a longer timeout for the expectation
    expect(response_box).to_contain_text("Status: 200", timeout=10000)

"""  CRUD User Tests """

def test_user_lifecycle_create_edit_delete(page: Page, minikube_url: str):
    """
    Verify the full lifecycle of a user: creation, editing, and deletion, 
    ensuring that each step is reflected in the UI and the underlying data.
    """
    # Handle the JavaScript confirm dialog that appears when deleting a user by automatically accepting it
    page.on("dialog", lambda dialog: dialog.accept())

    page.goto(minikube_url)

    # Use UUID to generate unique data for each test run to avoid DB constraint errors
    unique_suffix = uuid.uuid4().hex[:8]
    username = f"e2e_usr_{unique_suffix}"
    email = f"u_{unique_suffix}@test.com"
    updated_username = f"test_e2e_user_updated_{unique_suffix}"

    # User creation: fill the form and submit
    page.fill("#username", username)
    page.fill("#email", email)
    page.click("#createUserForm button[type='submit']")

    # Wait for the API response to be displayed and verify that it contains the expected success message
    expect(page.locator("#api-response")).to_contain_text("Utente creato con successo!")

    # Verify that the new user appears in the users table
    user_row = page.locator("#usersTableBody tr", has_text=username)
    expect(user_row).to_be_visible()

    # Update the user
    user_row.locator("button:has-text('✏️')").click()
    
    # Verify that the edit modal is visible, fill in the updated username, and submit the form
    expect(page.locator("#editUserModal")).to_be_visible()
    page.fill("#editUsername", updated_username)
    page.click("#editUserForm button[type='submit']")

    # Verify that the table reflects the updated username
    expect(page.locator("#usersTableBody")).to_contain_text(updated_username)

    # User delete
    updated_row = page.locator("#usersTableBody tr", has_text=updated_username)
    updated_row.locator("button:has-text('🗑️')").click()

    # If backedn fails, the testwill fail and the SQL error will be logged in the API response box. 
    expect(page.locator("#api-response")).to_contain_text("User deleted successfully", timeout=3000)

    # Verify that the user is no longer present in the users table after deletion
    # Using 'not_to_contain_text' is safer than checking for visibility of the row
    expect(page.locator("#usersTableBody")).not_to_contain_text(updated_username)

def test_user_search(page: Page, minikube_url: str):
    """
        Verify the user search functionality by ID (both positive and negative outcomes),
        and clean up the created user at the end to maintain test isolation.
    """
    # Accept dialogs automatically (needed for the cleanup phase at the end)
    page.on("dialog", lambda dialog: dialog.accept())

    page.goto(minikube_url)
    
    # 1. SETUP: Create a dummy user with UNIQUE data
    unique_suffix = uuid.uuid4().hex[:8]
    unique_username = f"search_user_{unique_suffix}"
    unique_email = f"search_{unique_suffix}@test.com"
    
    page.fill("#username", unique_username)
    page.fill("#email", unique_email)
    page.click("#createUserForm button[type='submit']")
    expect(page.locator("#api-response")).to_contain_text("Utente creato con successo!")
    
    # Locate the row and get the ID
    user_row = page.locator("#usersTableBody tr", has_text=unique_username)
    expect(user_row).to_be_visible()
    created_user_id = user_row.locator("td").first.inner_text()
    
    # 2. TEST: Search for the newly created user
    page.fill("#searchId", created_user_id)
    page.click("#searchUserForm button[type='submit']")
    expect(page.locator("#usersTableBody tr.table-info")).to_be_visible()
    expect(page.locator("#api-response")).to_contain_text("✅ Utente trovato")
    
    # 3. TEST: Search for a non-existent ID
    page.fill("#searchId", "9999999")
    page.click("#searchUserForm button[type='submit']")
    expect(page.locator("#usersTableBody")).to_contain_text("Utente non trovato (404)")
    
    # 4. TEARDOWN / CLEANUP: Delete the test user
    # Click the "✖️" button (using its title) to reset the table view and see all users again
    page.locator("button[title='Reset vista']").click()
    
    # Find the row of our test user again and click the delete button (🗑️)
    user_row_to_delete = page.locator("#usersTableBody tr", has_text=unique_username)
    user_row_to_delete.locator("button:has-text('🗑️')").click()

    expect(page.locator("#api-response")).to_contain_text("User deleted successfully", timeout=3000)
    
    # Verify the cleanup was successful
    expect(page.locator("#usersTableBody")).not_to_contain_text(unique_username)