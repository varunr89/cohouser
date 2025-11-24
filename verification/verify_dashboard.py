from playwright.sync_api import sync_playwright
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PageError: {err}"))

        # Open the file directly
        cwd = os.getcwd()
        file_path = f"file://{cwd}/financial_dashboard.html"
        print(f"Opening: {file_path}")

        page.goto(file_path)

        try:
            page.wait_for_selector('.stat-card', timeout=5000)
            output_path = "verification/dashboard_screenshot.png"
            page.screenshot(path=output_path, full_page=True)
            print(f"Screenshot saved to {output_path}")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error_screenshot_2.png")

        finally:
            browser.close()

if __name__ == "__main__":
    run()
