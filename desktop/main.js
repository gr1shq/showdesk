const { app, BrowserWindow, globalShortcut, screen } = require('electron');
const screenshot = require('screenshot-desktop');

let mainWindow;

app.whenReady().then(() => {
  // Create invisible window for capturing
  mainWindow = new BrowserWindow({
    width: 400,
    height: 600,
    webPreferences: {
      nodeIntegration: true
    }
  });

  // Register global hotkey (Cmd+K or Ctrl+K)
  globalShortcut.register('CommandOrControl+K', async () => {
    console.log('Hotkey pressed!');
    
    // Capture screen
    const img = await screenshot();
    const base64 = img.toString('base64');
    
    // Send to your FastAPI backend
    fetch('http://localhost:8000/api/capture-and-analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ screenshot: base64 })
    })
    .then(res => res.json())
    .then(data => {
      // Show notification if issue found
      if (data.issue_detected) {
        mainWindow.webContents.send('show-notification', data);
      }
    });
  });

  mainWindow.loadFile('index.html');
});