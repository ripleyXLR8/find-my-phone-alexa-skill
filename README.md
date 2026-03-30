# 📱 Find My Phone - Alexa Skill

[![Unraid Ready](https://img.shields.io/badge/Unraid-Community%20Applications-orange.svg)](https://forums.unraid.net/topic/38582-announcement-community-applications/)
[![Raspberry Pi / ARM64](https://img.shields.io/badge/Raspberry%20Pi-ARM64%20Ready-C51A4A?logo=raspberry-pi&logoColor=white)](#)
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
* **Multi-Architecture Support**: Built for both `x86_64` (Standard PCs/Servers) and `ARM64` (Raspberry Pi, CasaOS, Mac M1/M2).
* **100% Stateless & Automated**: The container automatically downloads tools, creates folders, and customizes your scripts using Environment Variables.
* **Rock-Solid Stability (v1.2)**: Integrated Docker Healthcheck for continuous monitoring in Unraid, and locked the `GoogleFindMyTools` dependency to a specific stable commit (`0003116`) to prevent upstream breaking changes.
* **Secure & Reliable (v1.1)**: Built-in Amazon Signature Verification to reject unauthorized requests, and asynchronous background execution to prevent Alexa 8-second timeouts.
* **Multi-Profile Support**: Easily manage different users (e.g., Richard, Lea) via isolated script execution.
* **Headless Automation**: Pre-configured with `Chromium`, `chromedriver`, and `undetected-chromedriver`.
* **Graceful Shutdown**: Utilizes `tini` for instant and clean container stops on Unraid.

---

## 🔑 Step 1: Get your `secrets.json` & Device ID

Because Google's authentication requires a graphical web browser (Chrome), **you must perform the initial login on your personal computer (Windows/Mac/Linux)** before setting up the Unraid Docker.

**Step-by-step guide:**
1. On your personal computer, download or clone the original [GoogleFindMyTools repository](https://github.com/leonboe1/GoogleFindMyTools).
2. Open a terminal/command prompt in that folder and install the requirements:  
   `pip install -r requirements.txt`
3. Run the main script:  
   `python main.py`
4. A Google Chrome window will open. **Log in to the Google Account** associated with the phone you want to locate.
5. Once logged in, look at your terminal. The script will list all your devices with their corresponding **Canonical IDs** (e.g., `691ee847-0000-2401-ab82-fc41166d2bf9`). **Copy this ID**; this is your `DEVICEID_[USER]`.
6. In the tool's folder on your computer, a new directory named `Auth` has been created, containing a `secrets.json` file.
7. **Open `secrets.json` with a text editor**, copy all the text inside, and keep it ready for the Unraid template (`SECRET_[USER]`).

---

## 🎙️ Step 2: Create the Alexa Skill

You need to create a custom Alexa Skill to receive your voice commands and forward them to your Unraid server.

**Step-by-step guide:**
1. Log in to the [Amazon Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
2. Click **Create Skill**.
   * **Name**: `Find My Phone` (or anything you prefer).
   * **Primary locale**: Choose your language (English or French).
   * **Experience, Model, Hosting**: Select `Other` > `Custom` > `Provision your own`.
   * Click **Next**, then choose **Start from Scratch**.
3. **Copy your Skill ID**: In the console, find your Skill ID (it looks like `amzn1.ask.skill.xxxx...`). **Copy it**, you will need it for the `ALEXA_SKILL_ID` variable in Unraid.
4. **Import the Interaction Model**:
   * In the left menu, go to **Interaction Model > JSON Editor**.
   * Paste the content of the `alexa_speech_assets/US.json` (or the `FR.json` version) provided in this repository.
   * Click **Save Model**.
5. **Customize your names (Crucial!)**:
   * In the left menu, go to **Assets > Slot Types > PHONE_OWNER**.
   * Replace the dummy values (`richard`, `lea`) with the **actual first names** of your family members. This step is mandatory for Alexa to understand the names you speak!
   * Click **Build Skill** (this takes a minute).
6. **Configure the Endpoint**:
   * In the left menu, go to **Endpoint**.
   * Select **HTTPS**.
   * In the Default Region field, enter your public secure URL (e.g., `https://alexa.yourdomain.com` - *see Step 4 below*).
   * In the SSL dropdown, select: *"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"*.
   * Click **Save Endpoints**.

---

## 🚀 Step 3: Installation on Unraid

1.  Open your Unraid WebGUI and go to the **Apps** tab.
2.  Search for `find-my-phone-alexa-skill`.
3.  Click **Install**.
4.  Configure the Environment Variables (see below) using the data you gathered in Step 1 and Step 2.

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ALEXA_SKILL_ID` | **[NEW in v1.1]** Your Alexa Skill ID (`amzn1.ask.skill...`). Required for request signature verification & security. | `None` |
| `USERS` | Comma-separated list of users (e.g., richard,lea). | `richard,lea` |
| `SECRET_[USER]` | The full JSON content of your locally generated `secrets.json` for that user (e.g., `SECRET_RICHARD`). | `None` |
| `DEVICEID_[USER]` | The target Google device ID to ring for that user (e.g., `DEVICEID_RICHARD`). | `None` |
| `TOOLS_VERSION` | Pinned `GoogleFindMyTools` version (Commit SHA) to ensure stability. | `0003116` |
| `DEBUG_MODE` | Set to `true` to enable verbose logging. | `true` |
| `PYTHONUNBUFFERED` | Ensures that Python logs are sent straight to the Docker console in real-time. | `1` |
| `TZ` | Sets the timezone for the container logs. | `Europe/Paris` |

---

## 🌐 Step 4: Network & Connectivity (Cloudflare Tunnel Recommended)

Amazon Alexa **requires** a valid HTTPS endpoint to communicate with your self-hosted skill. 

Instead of opening ports on your router, we strongly recommend using a **Cloudflare Tunnel** (`cloudflared` container on Unraid) to securely route traffic to this container.

**How to set it up:**
1. Install the `cloudflared` container on your Unraid server.
2. Go to your Cloudflare Zero Trust Dashboard.
3. Under **Access > Tunnels**, select your Unraid tunnel and add a new **Public Hostname** (e.g., `alexa.yourdomain.com`).
4. Set the **Service** to route to your container:
   * **Type:** `HTTP`
   * **URL:** `<Your-Unraid-IP>:3000` (e.g., `192.168.1.100:3000`)
5. Make sure this matches the Endpoint URL you pasted in the Alexa Developer Console in Step 2.

*Note: You can also use Nginx Proxy Manager, Traefik, or any other reverse proxy that provides SSL termination.*

---

## 📦 Technical Stack

This project leverages several powerful libraries to ensure reliable communication and device localization:

* **Core**: Python 3.11 with `Flask`, `tini`, and the `flask-ask-sdk` for secure Alexa Skill interaction.
* **Automation**: `selenium` and `undetected-chromedriver` are included to navigate Google services in headless mode.
* **Tools**: `gpsoauth` for Google Play Services authentication and `beautifulsoup4` for web parsing.
* **Advanced**: `frida`, `cryptography`, and `pycryptodomex` for system-level instrumentation and secure data handling.

---

## 🙏 Special Thanks & Credits

A huge thank you to **Leon Böttger** ([@leonboe1](https://github.com/leonboe1)) for his incredible work creating the core [GoogleFindMyTools](https://github.com/leonboe1/GoogleFindMyTools) project. This Alexa Skill middleware wouldn't be possible without his extensive reverse-engineering of the Google Find My Device API. 

---

## 📄 License

This project is distributed under the **MIT License**. See the `LICENSE` file for more details.

---

## 🤖 Vibe Coding & Credits

**This project is a pure "Vibe Coding" experiment.**

It was entirely architected, debugged, and refined through a continuous natural language dialogue with **Google Gemini**. No manual coding was performed; the human acted as the conductor, and the AI as the expert developer.

---

## ☕ Want to support me?

**Enjoying this project?** If this tool saves you from tearing the house apart looking for your phone, consider supporting the updates!  
[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/ripleyxlr8)

<p align="center"><i>Developed for the Unraid community to simplify home automation.</i></p>
