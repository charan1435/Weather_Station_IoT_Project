"# IoT weather station project"

# 🌦️ IoT Weather Station Project

This is a MicroPython-based IoT weather monitoring system using a **Raspberry Pi Pico W** and **BME280** sensor. It logs real-time environmental data (temperature and pressure), displays it on a local web server, and pushes it to a **Google Sheet** using an Apps Script endpoint. The system also supports **offline data storage** and **automatic recovery/upload** once Wi-Fi is restored.

---

## 📦 Features

- 📶 **Wi-Fi Connectivity** with retry and status indication using onboard LED
- 🌡️ **Real-time Temperature and Pressure** readings via BME280
- 📊 **Google Sheets Integration** using HTTP requests via `urequests`
- 🌐 **Local Web Server** with live HTML dashboard (auto-refresh every 10 seconds)
- 📂 **Offline Storage** of readings when Wi-Fi is not available
- 🔁 **Automatic Upload** of offline readings once reconnected
- 🧠 **Time Syncing** via [timeapi.io](https://timeapi.io/)
- 📉 **Status Display & Logging** in shell output for debugging

---

## 🛠️ Hardware Requirements

- 🧠 Raspberry Pi Pico W
- 🌡️ BME280 Sensor (Temperature & Pressure)
- 🔌 Breadboard and jumper wires
- 💻 Wi-Fi Network

---

## 🧰 Software Requirements

- MicroPython firmware for Pico W
- [Thonny IDE](https://thonny.org/) or any MicroPython uploader
- GitHub / Google Account (for repository and Google Sheets integration)

---
