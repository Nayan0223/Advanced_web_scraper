"""Playwright browser stealth scripts to bypass bot detection."""

STEALTH_JS = """
// 1. Pass the Webdriver Test
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// 2. Mock Chrome runtime
if (!window.chrome) {
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
}

// 3. Mock languages and plugins
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {
            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
            description: "Portable Document Format",
            filename: "internal-pdf-viewer",
            length: 1,
            name: "Chrome PDF Plugin"
        },
        {
            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
            description: "Portable Document Format",
            filename: "internal-pdf-viewer",
            length: 1,
            name: "Chrome PDF Viewer"
        }
    ],
});

// 4. Mock permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""


async def apply_stealth(page_or_context) -> None:
    """Inject stealth scripts into a Playwright Page or BrowserContext."""
    await page_or_context.add_init_script(STEALTH_JS)

