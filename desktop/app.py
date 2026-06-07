"""Ad Spy Agent - desktop wrapper.

Opens the live web app in a native desktop window (no browser tab needed).
All scraping + Gemini AI run on the server; this is just the window.
"""
import webview

APP_URL = "https://adspyagent.duckdns.org"


def main():
    webview.create_window(
        "Ad Spy Agent",
        APP_URL,
        width=1280,
        height=850,
        min_size=(900, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
