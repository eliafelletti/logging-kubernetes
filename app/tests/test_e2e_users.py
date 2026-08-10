import uuid
from playwright.sync_api import Page, expect

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
    
    # Search for the newly created user
    page.fill("#searchId", created_user_id)
    page.click("#searchUserForm button[type='submit']")
    expect(page.locator("#usersTableBody tr.table-info")).to_be_visible()
    expect(page.locator("#api-response")).to_contain_text("✅ Utente trovato")
    
    # Search for a non-existent ID
    page.fill("#searchId", "9999999")
    page.click("#searchUserForm button[type='submit']")
    expect(page.locator("#usersTableBody")).to_contain_text("Utente non trovato (404)")
    
    # 4. TEARDOWN: Delete the test user
    page.locator("button[title='Reset vista']").click()
    
    # Find the row of our test user again and click the delete button (🗑️)
    user_row_to_delete = page.locator("#usersTableBody tr", has_text=unique_username)
    user_row_to_delete.locator("button:has-text('🗑️')").click()

    expect(page.locator("#api-response")).to_contain_text("User deleted successfully", timeout=3000)
    
    # Verify the cleanup was successful
    expect(page.locator("#usersTableBody")).not_to_contain_text(unique_username)

def test_users_load_with_delay(page: Page, minikube_url: str):
    """
    Verify that selecting a latency delay displays the loading state 
    and successfully completes after the delay.
    """
    page.goto(minikube_url)
    
    # Select 1 second delay from the dropdown
    page.select_option("#delaySelect", "1")
    page.get_by_role("button", name="🔄 Aggiorna Lista").click()
    
    # Check for the temporary loading message
    response_box = page.locator("#api-response")
    expect(response_box).to_contain_text("⏳ Caricamento utenti in corso con ritardo di 1 secondi")
    
    # Check for the final success message (timeout slightly increased to account for the 1s delay)
    expect(response_box).to_contain_text("✅ Utenti caricati", timeout=3000)


def test_user_duplicate_creation_error(page: Page, minikube_url: str):
    """
    Verify that creating a user with already existing credentials 
    results in an appropriate error message, then clean up.
    """
    # Accept dialogs automatically for the cleanup phase
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(minikube_url)
    
    # Create a unique user
    unique_suffix = uuid.uuid4().hex[:8]
    username = f"dup_{unique_suffix}"
    email = f"d_{unique_suffix}@test.com"
    
    page.fill("#username", username)
    page.fill("#email", email)
    page.click("#createUserForm button[type='submit']")
    expect(page.locator("#api-response")).to_contain_text("Utente creato con successo!")
    
    # Try to create the exact same user again
    page.fill("#username", username)
    page.fill("#email", email)
    page.click("#createUserForm button[type='submit']")
    
    # Verify the backend rejects the duplicate
    expect(page.locator("#api-response")).to_contain_text("❌ Errore: Username or email already exists (or DB error)")
    
    # TEARDOWN: Delete the user to maintain isolation
    user_row = page.locator("#usersTableBody tr", has_text=username)
    user_row.locator("button:has-text('🗑️')").click()
    
    expect(page.locator("#api-response")).to_contain_text("User deleted successfully", timeout=3000)
    expect(page.locator("#usersTableBody")).not_to_contain_text(username)


def test_user_creation_empty_form_validation(page: Page, minikube_url: str):
    """
    Verify that submitting an empty form is prevented by the browser 
    and does not trigger an API call.
    """
    page.goto(minikube_url)
    
    # Ensure fields are empty
    page.fill("#username", "")
    page.fill("#email", "")
    
    # Try to submit the form
    page.click("#createUserForm button[type='submit']")
    
    # Verify the API response box remains in its default state (no HTTP request was sent)
    expect(page.locator("#api-response")).to_contain_text("In attesa di comandi...")