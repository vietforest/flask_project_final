import re
from playwright.sync_api import Page, expect

# Start the app first with:  flask run
# Demo account from `flask seed-demo`: demo / demo1234


def test_login_page(page: Page):
    page.goto("http://127.0.0.1:5000/auth/login")
    expect(page).to_have_title(re.compile("Log in"))


def test_login(page: Page) -> None:
    page.goto("http://127.0.0.1:5000/auth/login")
    page.get_by_role("textbox", name="Username").fill("demo")
    page.get_by_role("textbox", name="Password").fill("demo1234")
    page.get_by_role("button", name="Log in").click()
    expect(page.get_by_text("Spent this month")).to_be_visible()


def test_wrong_password(page: Page) -> None:
    page.goto("http://127.0.0.1:5000/auth/login")
    page.get_by_role("textbox", name="Username").fill("demo")
    page.get_by_role("textbox", name="Password").fill("demo")
    page.get_by_role("button", name="Log in").click()
    expect(page.get_by_role("alert")).to_contain_text("Wrong username or password")

def test_dashboard_requires_login(page: Page) -> None:
    page.goto("http://127.0.0.1:5000/dashboard")
    expect(page).to_have_url("http://127.0.0.1/auth/login")
    pass