# 📱 Find My Phone - Alexa Skill

[![Unraid Ready](https://img.shields.io/badge/Unraid-Community%20Applications-orange.svg)](https://forums.unraid.net/topic/38582-announcement-community-applications/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat&logo=flask&logoColor=white)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=flat)
![Vibe Coding](https://img.shields.io/badge/Built%20with-Google%20Gemini-8E75B2)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-orange?logo=buymeacoffee&logoColor=white)](https://buymeacoffee.com/ripleyxlr8)

A self-hosted **Alexa Skill middleware** designed specifically for the **Unraid** ecosystem. This tool bridges Alexa voice commands to local Python scripts to locate your devices (Android/Google) using a robust, headless automation environment.

---

## ✨ Features

* **One-Click Install**: Fully compatible with Unraid's Community Applications (CA).
* **Headless Automation**: Pre-configured with `Chromium`, `chromedriver`, and `undetected-chromedriver` to handle complex Google logins.
* **Multi-Profile Support**: Easily manage different users (e.g., Richard, Lea) via isolated script execution.
* **100% Stateless & Automated**: The container automatically downloads tools, creates folders, and customizes your scripts using Environment Variables.
* **Real-time Logging**: Optimized for Unraid's Docker logs with unbuffered Python output.

---

## 🚀 Installation on Unraid

### 1. Prerequisites
* An **Alexa Skill** created on the [Amazon Developer Console](https://developer.amazon.com/alexa/console/ask).
* An HTTPS endpoint (using **Nginx Proxy Manager**, **Cloudflare Tunnels**, or similar) pointing to your Unraid server on port `3000`.

### 2. Deployment
1.  Open your Unraid WebGUI and go to the **Apps** tab.
2.  Search for `find-my-phone-alexa-skill`.
3.  Click **Install**.
4.  Configure the Environment Variables (see below) and verify the **AppData** mapping (default: `/mnt/user/appdata/alexa-findmyphone`).

---

## ⚙️ Configuration

### Environment Variables

The following environment variables can be configured within the Unraid Docker settings to customize the behavior of the middleware:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `USERS` | Comma-separated list of users (e.g., richard,lea). | `richard,lea` |
| `SECRET_[USER]` | The full JSON content of your locally generated `secrets.json` for that user (e.g., `SECRET_RICHARD`). | `None` |
| `DEVICEID_[USER]` | The target Google device ID to ring for that user (e.g., `DEVICEID_RICHARD`). | `None` |
| `TOOLS_VERSION` | `GoogleFindMyTools` version to clone (branch, tag, or SHA). | `main` |
| `DEBUG_MODE` | Set to `true` to enable verbose logging for the Alexa Skill and Flask server. | `true` |
| `PYTHONUNBUFFERED` | Ensures that Python logs are sent straight to the Docker console in real-time. | `1` |
| `TZ` | Sets the timezone for the container logs (e.g., `Europe/Paris`). | `Europe/Paris` |
| `BASE_DIR` | The internal path used for script discovery. **Note:** This is mapped to `/config` by default. | `/config` |

### Network & Connectivity

* **Port**: The Flask server listens on port **3000**.
* **Access**: To communicate with Amazon Alexa, this port must be accessible via an HTTPS endpoint (e.g., via Nginx Proxy Manager or a similar reverse proxy).
* **Unraid Network**: While the default is `bridge`, you can assign a dedicated IP using the `br0` network if preferred.

---

## 📦 Technical Stack

This project leverages several powerful libraries to ensure reliable communication and device localization:

* **Core**: Python 3.11 with `Flask` and the `ask-sdk-core` / `ask-sdk-model` for Alexa Skill interaction.
* **Automation**: `selenium` and `undetected-chromedriver` are included to navigate Google services in headless mode.
* **Tools**: `gpsoauth` for Google Play Services authentication and `beautifulsoup4` for web parsing.
* **Advanced**: `frida`, `cryptography`, and `pycryptodomex` for system-level instrumentation and secure data handling.

---

## 🤝 Contributing

Contributions are welcome! If you have suggestions for improvements or new features:

1.  **Fork** the project.
2.  Create your **Feature Branch** (`git checkout -b feature/AmazingFeature`).
3.  **Commit** your changes (`git commit -m 'Add some AmazingFeature'`).
4.  **Push** to the branch (`git push origin feature/AmazingFeature`).
5.  Open a **Pull Request**.

---

## 📄 License

This project is distributed under the **MIT License**. See the `LICENSE` file for more details.

---
*Developed for the Unraid community to simplify home automation.*
