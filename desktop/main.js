// Ad Spy Agent - Electron desktop wrapper.
// Opens the live web app in a native window across Win/Mac/Linux.
const { app, BrowserWindow, shell } = require('electron')

const APP_URL = 'https://adspyagent.duckdns.org'

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 850,
    minWidth: 900,
    minHeight: 600,
    title: 'Ad Spy Agent',
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true },
  })
  win.loadURL(APP_URL)
  // Open external links (e.g. downloads) in the system browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
