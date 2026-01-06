# Tauri Updater Setup Guide

This guide explains how to set up automatic updates for Qubes.

## Overview

The updater uses:
- **GitHub Releases** as the update source
- **Ed25519 signatures** to verify update authenticity
- **Tauri's built-in updater plugin** for download and installation

## Step 1: Generate Signing Keys

Run this command to generate a new key pair:

```bash
npx @tauri-apps/cli signer generate -w ~/.tauri/qubes.key
```

This creates:
- `~/.tauri/qubes.key` - Private key (KEEP SECRET!)
- Outputs the public key to console

**IMPORTANT:**
- Save the private key password securely
- Never commit the private key to git
- Back up the private key - you need it for all future updates

## Step 2: Configure the Public Key

1. Copy the public key from the generator output
2. Open `src-tauri/tauri.conf.json`
3. Replace `REPLACE_WITH_YOUR_PUBLIC_KEY` with your public key:

```json
"plugins": {
  "updater": {
    "endpoints": [
      "https://github.com/BitFaced2/Qubes/releases/latest/download/latest.json"
    ],
    "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXkgM0..."
  }
}
```

## Step 3: Build Signed Releases

When building a release, set these environment variables:

```bash
# Windows PowerShell
$env:TAURI_SIGNING_PRIVATE_KEY = Get-Content ~/.tauri/qubes.key
$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = "your-password"

# Or use the key path directly
$env:TAURI_SIGNING_PRIVATE_KEY = "~/.tauri/qubes.key"
```

Then build:

```bash
npm run tauri build
```

This creates:
- The installer (`.msi`, `.exe`, etc.)
- A `.sig` signature file for each installer

## Step 4: Create GitHub Release

1. Create a new release on GitHub
2. Upload all build artifacts:
   - `Qubes_x.x.x_x64-setup.exe`
   - `Qubes_x.x.x_x64-setup.exe.sig`
   - `Qubes_x.x.x_x64_en-US.msi`
   - `Qubes_x.x.x_x64_en-US.msi.sig`

3. Create `latest.json` with this format:

```json
{
  "version": "0.2.0",
  "notes": "Bug fixes and improvements",
  "pub_date": "2025-01-15T12:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "CONTENTS_OF_YOUR_.sig_FILE",
      "url": "https://github.com/BitFaced2/Qubes/releases/download/v0.2.0/Qubes_0.2.0_x64-setup.exe"
    }
  }
}
```

4. Upload `latest.json` to the release

## Step 5: Automate with GitHub Actions (Recommended)

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install dependencies
        run: |
          cd qubes-gui
          npm install

      - name: Build Tauri app
        uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
          TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}
        with:
          projectPath: qubes-gui
          tagName: v__VERSION__
          releaseName: 'Qubes v__VERSION__'
          releaseBody: 'See the assets to download and install this version.'
          releaseDraft: true
          prerelease: false
          includeUpdaterJson: true
```

Add these secrets to your GitHub repository:
- `TAURI_SIGNING_PRIVATE_KEY` - Contents of your private key file
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` - Your key password

## Step 6: Deploy to Production Server (Optional)

For production releases, you may want to host files on your own server instead of GitHub for faster downloads:

### 1. Download GitHub Actions Artifacts

After the build completes, download the release artifacts from GitHub Actions.

### 2. Update latest.json URLs

Change URLs from GitHub to your production server:

```json
{
  "version": "0.2.7",
  "notes": "Qubes v0.2.7 release",
  "pub_date": "2026-01-06T09:14:18Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "CONTENTS_OF_.sig_FILE",
      "url": "https://your-domain.com/releases/v0.2.7/Qubes-Windows-setup.exe"
    },
    "darwin-aarch64": {
      "signature": "CONTENTS_OF_.sig_FILE",
      "url": "https://your-domain.com/releases/v0.2.7/Qubes-macOS-ARM.app.tar.gz"
    },
    "linux-x86_64": {
      "signature": "CONTENTS_OF_.sig_FILE",
      "url": "https://your-domain.com/releases/v0.2.7/Qubes-Linux.AppImage.tar.gz"
    }
  }
}
```

### 3. Upload to Server

Upload the release files to your production server via SCP, SFTP, or your preferred method.

### 4. Update Releases Page

Update your releases page to include the new version.

## Testing

1. Build version 0.1.0 and install it
2. Build version 0.2.0 and create a GitHub release
3. Open Settings in the app and click "Check for Updates"
4. The update should be detected and installable

**Important**: Always test auto-updates on an installed (non-dev) version before announcing the release.

## Troubleshooting

### "Signature verification failed"
- Ensure the public key in `tauri.conf.json` matches your private key
- Verify the `.sig` file was uploaded correctly
- Check that `latest.json` contains the correct signature

### "No update available" when there should be
- Check the version in `tauri.conf.json` is lower than the release version
- Verify `latest.json` is accessible at the endpoint URL
- Check browser console for network errors

### Update downloads but fails to install
- On Windows, ensure the app isn't running from a protected directory
- Check Windows Defender isn't blocking the update
- Try running the app as administrator

### App shows tutorial/onboarding screen after update
This indicates the Python backend is crashing on startup.

**Diagnosis**:
1. Navigate to the installed app directory (e.g., `C:\Program Files\Qubes\`)
2. Run the backend manually: `./qubes-backend.exe check-first-run`
3. Look for import errors or missing modules

**Common Cause**: Missing module in PyInstaller bundle
- If a Python module was added but not included in PyInstaller's hidden imports
- Solution: Use lazy loading for optional modules

```python
# Bad: Top-level import crashes if module missing
import some_optional_module

# Good: Lazy load when actually needed
_module = None
def _get_module():
    global _module
    if _module is None:
        import some_optional_module
        _module = some_optional_module
    return _module
```

**User Data Location**: User data is safe at:
- Windows: `C:\Users\<user>\AppData\Local\Qubes\data\users\`
- The tutorial screen is just the frontend; data is not lost
