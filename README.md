# ⚡ Riot Link

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-0078D6.svg?style=for-the-badge)
![Safety](https://img.shields.io/badge/Vanguard%20Safe-100%25-brightgreen.svg?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-purple.svg?style=for-the-badge)

**The 1-click Riot Games account switcher for League of Legends, VALORANT, and TFT.**  
*Switch accounts in under 3 seconds without typing passwords or re-entering 2FA codes.*

</div>

---

## ✨ Features

* **⚡ 1-Click Instant Switching**: Click `SWITCH & PLAY` on any account and your game starts up already logged in.
* **🛡️ 100% Safe (0% Ban Risk)**: Works without hacking, injecting, or touching game memory. Riot Vanguard treats it completely normally.
* **🔒 Zero Plaintext Passwords**: Your passwords are never asked for, transmitted, or stored.
* **📲 2FA Persistent**: Authenticate Two-Factor Authentication once—Riot remembers your PC and bypasses 2FA on subsequent switches.
* **🎯 Direct Game Shortcuts**: Dedicated `LoL` and `VAL` buttons to jump straight into League of Legends or VALORANT.
* **🔄 Intelligent Logout Detection**: If an account gets signed out in Riot Client, Riot Link detects it, alerts you, and provides a 1-click re-linking flow.
* **🎮 Profile Customization**: Organize accounts with tags (`Main`, `Smurf`, `Ranked`, `Casual`) and custom accent colors.
* **💻 Standalone Executable**: Portable single `.exe` with zero installation required.

---

## 📥 Download & Install

### Option A: Standalone Executable (Recommended)
1. Go to the [**Releases**](https://github.com/marweneb/riot-account-switcher/releases) page on GitHub.
2. Download **`RiotLink.exe`** (or `RiotLink-v1.0.0-windows-x64.zip`).
3. Run `RiotLink.exe`! No installation needed.

### Option B: Run from Source
```powershell
# Clone the repository
git clone https://github.com/marweneb/riot-account-switcher.git
cd riot-account-switcher

# Install dependencies
pip install -r requirements.txt

# Launch
python main.py
# Or double-click run.bat
```

---

## 📖 Quick Start Guide (1-Minute Setup)

### 1️⃣ Save Your First Account
1. Open your regular **Riot Client**.
2. Type your username and password, **make sure "Stay signed in" is checked**, and log in.
3. Open **Riot Link** and click **`+ SAVE CURRENT ACCOUNT`** at the top.
4. Give it a nickname (e.g. `Main`), choose a tag and color, and click **Save Profile**.

### 2️⃣ Add Your Other Accounts
1. In Riot Link, click **`🔑 LOG IN ANOTHER ACCOUNT`** at the top.
   *(This safely closes Riot Client and opens a clean login screen without disconnecting your first account).*
2. Enter your **second account's** username and password, ensure **"Stay signed in"** is checked, and log in.
3. Once logged in, click **`+ SAVE CURRENT ACCOUNT`** in Riot Link!

### 3️⃣ Switch and Play Anytime!
* Click **`SWITCH & PLAY`** on any saved account card to switch and launch your game.
* Or click the **`LoL`** or **`VAL`** buttons on the card to launch straight into League of Legends or VALORANT!

---

## ❓ Frequently Asked Questions

#### Will Riot Vanguard ban me for using this?
**No, 100% safe.** Cheats inject code into game memory. Riot Link does not touch game memory, does not modify game files, and does not run during your matches. It only manages Riot's own official "Stay signed in" local configuration files while the client is closed.

#### What happens if I have 2FA (Two-Factor Authentication)?
You only enter your 2FA code **once** when saving the account with "Stay signed in" checked. Riot's servers remember that your computer is authorized, so switching accounts skips the 2FA prompt automatically!

#### Can I click "Sign Out" inside Riot Client?
⚠️ **Avoid clicking "Sign Out" in Riot Client.** Clicking "Sign Out" tells Riot's authentication servers to destroy that session token. Always switch accounts directly from Riot Link or click **`🔑 LOG IN ANOTHER ACCOUNT`** instead!

#### What if an account shows `⚠️ LOGGED OUT`?
If you accidentally clicked "Sign Out" in Riot Client:
1. Riot Link automatically detects the revoked session and tags the card as **`⚠️ LOGGED OUT`**.
2. Open Riot Client and sign into that account normally (with "Stay signed in" checked).
3. In Riot Link, click the highlighted **🔄 (Refresh)** button on that card. Your session is immediately re-linked!

---

## 🔨 Building from Source (PyInstaller)

To build a standalone single-file `dist/RiotLink.exe` on Windows:

```powershell
# Run the automated build script
.\build.bat

# Or using PyInstaller directly:
pyinstaller --clean -y RiotLink.spec
```

The compiled standalone executable will be in `dist/RiotLink.exe`.

---

## 🤖 Continuous Integration & GitHub Releases

This project includes a production-ready GitHub Actions workflow ([`.github/workflows/release.yml`](.github/workflows/release.yml)):
- Automatically triggered on version tags (`v*`, e.g. `git tag v1.0.0 && git push origin v1.0.0`).
- Can also be triggered manually via **GitHub Actions → Run workflow**.
- Builds the standalone Windows x64 binary, computes SHA256 checksums, and publishes a GitHub Release with downloadable artifacts.

---

## 📄 License
Distributed under the MIT License.
