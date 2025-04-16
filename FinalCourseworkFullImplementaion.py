import machine
from time import sleep, time
import network
import socket
import urequests
import json
import gc
import random
from machine import Pin, I2C, RTC
import bme280

# --- Hardware Setup ---
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
bme = bme280.BMP280(i2c=i2c)  

# Initialize RTC
rtc = RTC()

# LED for status indication
board_led = machine.Pin("LED", machine.Pin.OUT)

# Wi-Fi credentials
ssid = 'Pixel_5132'
password = 'sui77@H'

# URLs for time API and Google Sheets
TIME_URL = "https://timeapi.io/api/time/current/zone?timeZone=Asia%2FColombo"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwVBohFQOSkWi25wYV89nTdNW4EpS9W6TD7RWRrb0QgHNyZoLrHTLbbLKLXS5F9ods4/exec"

# File to store readings when offline
OFFLINE_READINGS_FILE = "offline_readings.txt"

def scan_wifi_networks():
    """Scan and show available Wi-Fi networks"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    
    print("Available Wi-Fi networks:")
    for i, network_info in enumerate(networks):
        ssid = network_info[0].decode('utf-8') if isinstance(network_info[0], bytes) else network_info[0]
        rssi = network_info[3]
        print(f"{i+1}. SSID: {ssid}, Signal strength: {rssi}dBm")
    
    return wlan

def connect_to_network():
    """Connect to Wi-Fi network using predefined credentials"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    # Set a timeout for connection
    max_wait = 10
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print('Waiting for connection...')
        sleep(1)
        board_led.toggle()  # Blink LED while connecting
    
    if wlan.isconnected():
        board_led.on()  # Solid LED when connected
        ip = wlan.ifconfig()[0]
        print(f'Connected on {ip}')
        return ip, wlan
    else:
        board_led.off()  # LED off when failed
        print('Failed to connect to WiFi. Operating in offline mode.')
        return None, wlan

def get_time():
    """Get current time from timeapi.io"""
    try:
        res = urequests.get(url=TIME_URL)
        time_data = json.loads(res.text)["dateTime"]
        res.close()
        return time_data
    except Exception as e:
        print(f"Error getting time: {e}")
        return "Time unavailable"

def get_formatted_time():
    """Get time from RTC in formatted string"""
    datetime = rtc.datetime()
    return f"{datetime[4]:02d}:{datetime[5]:02d}:{datetime[6]:02d}"

def save_offline_reading(timestamp, temp, pressure):
    """Save a reading to the offline storage file"""
    try:
        with open(OFFLINE_READINGS_FILE, "a") as file:
            file.write(f"{timestamp},{temp:.2f},{pressure:.2f}\n")
        print(f"Saved offline reading: {timestamp}, {temp:.2f}°C, {pressure:.2f}hPa")
        return True
    except Exception as e:
        print(f"Error saving offline reading: {e}")
        return False

def get_offline_readings():
    """Get all stored offline readings and return as a list"""
    readings = []
    try:
        with open(OFFLINE_READINGS_FILE, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    timestamp, temp, pressure = line.split(",")
                    readings.append((timestamp, float(temp), float(pressure)))
        return readings
    except OSError:  # File doesn't exist yet
        return []
    except Exception as e:
        print(f"Error reading offline readings: {e}")
        return []

def clear_offline_readings():
    """Clear the offline readings file"""
    try:
        with open(OFFLINE_READINGS_FILE, "w") as file:
            pass  # Just open and close to clear the file
        print("Cleared offline readings file")
        return True
    except Exception as e:
        print(f"Error clearing offline readings: {e}")
        return False

def upload_offline_readings(wlan):
    """Upload all stored offline readings to the spreadsheet"""
    if not wlan.isconnected():
        print("Cannot upload offline readings: WiFi not connected")
        return False
    
    readings = get_offline_readings()
    if not readings:
        print("No offline readings to upload")
        return True
    
    print(f"Uploading {len(readings)} offline readings...")
    
    success_count = 0
    for timestamp, temp, pressure in readings:
        if send_to_spreadsheet(timestamp, temp, pressure):
            success_count += 1
            sleep(0.5)  # Small delay between uploads to avoid overwhelming the server
    
    if success_count == len(readings):
        clear_offline_readings()
        print(f"Successfully uploaded all {success_count} offline readings")
        return True
    else:
        print(f"Uploaded {success_count} of {len(readings)} offline readings")
        
        # Keep only the failed readings
        remaining_readings = readings[success_count:]
        clear_offline_readings()
        for timestamp, temp, pressure in remaining_readings:
            save_offline_reading(timestamp, temp, pressure)
        
        return False

def open_socket(ip):
    """Open a socket for the web server"""
    if ip is None:
        return None
        
    address = (ip, 80)
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.bind(address)
    connection.listen(5)
    connection.settimeout(0.5)  # Non-blocking accept
    print(f"Listening on {ip}:80")
    return connection

def webpage(temp, pressure, wifi_status="Connected", offline_count=0):
    """Generate the HTML webpage with sensor data"""
    current_time = get_formatted_time()
    
    # Using  status additions
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Weather Station</title>
      <meta http-equiv="refresh" content="10">
      <style>
        :root {{
          --primary-color: #4361ee;
          --secondary-color: #3f37c9;
          --accent-color: #4cc9f0;
          --background-color: #f8f9fa;
          --card-bg: #ffffff;
          --text-primary: #212529;
          --text-secondary: #6c757d;
          --success-color: #72efdd;
          --warning-color: #f72585;
          --shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          --border-radius: 12px;
        }}
        
        * {{
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }}
        
        body {{
          font-family: 'Arial', sans-serif;
          background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
          color: var(--text-primary);
          min-height: 100vh;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 20px;
        }}
        
        .container {{
          max-width: 480px;
          width: 100%;
        }}
        
        .header {{
          text-align: center;
          margin-bottom: 24px;
        }}
        
        .header h1 {{
          color: var(--primary-color);
          font-size: 2rem;
          margin-bottom: 8px;
        }}
        
        .header p {{
          color: var(--text-secondary);
          font-size: 1rem;
        }}
        
        .cards {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 20px;
        }}
        
        .card {{
          background: var(--card-bg);
          border-radius: var(--border-radius);
          box-shadow: var(--shadow);
          padding: 20px;
          text-align: center;
          transition: transform 0.3s ease;
        }}
        
        .card:hover {{
          transform: translateY(-5px);
        }}
        
        .card-icon {{
          font-size: 2.5rem;
          margin-bottom: 12px;
          color: var(--primary-color);
        }}
        
        .card-temp .card-icon {{
          color: #f72585;
        }}
        
        .card-pressure .card-icon {{
          color: #4cc9f0;
        }}
        
        .card-value {{
          font-size: 2rem;
          font-weight: bold;
          margin-bottom: 8px;
          color: var(--primary-color);
        }}
        
        .card-label {{
          color: var(--text-secondary);
          font-size: 0.9rem;
        }}
        
        .card-temp .card-value {{
          color: #f72585;
        }}
        
        .card-pressure .card-value {{
          color: #4cc9f0;
        }}
        
        .status-bar {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: var(--card-bg);
          border-radius: var(--border-radius);
          box-shadow: var(--shadow);
          padding: 12px 20px;
          margin-bottom: 16px;
        }}
        
        .wifi-status {{
          display: flex;
          align-items: center;
        }}
        
        .wifi-status.online {{
          color: #28a745;
        }}
        
        .wifi-status.offline {{
          color: #dc3545;
        }}
        
        .status-icon {{
          margin-right: 8px;
        }}
        
        .pending-uploads {{
          background: #f8d7da;
          color: #721c24;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.8rem;
          display: {{"inline-block" if offline_count > 0 else "none"}};
        }}
        
        .last-updated {{
          text-align: center;
          margin-bottom: 16px;
          padding: 12px;
          color: var(--text-secondary);
          font-size: 0.9rem;
          background: var(--card-bg);
          border-radius: var(--border-radius);
          box-shadow: var(--shadow);
        }}
        
        .last-updated span {{
          font-weight: bold;
          color: var(--primary-color);
        }}
        
        .footer {{
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(10px);
          border-radius: var(--border-radius);
          padding: 16px;
          text-align: center;
          box-shadow: var(--shadow);
        }}
        
        .footer p {{
          color: var(--text-secondary);
          font-size: 0.9rem;
        }}
        
        @media (max-width: 480px) {{
          .cards {{
            grid-template-columns: 1fr;
          }}
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Weather Station</h1>
          <p>Real-time environmental monitoring</p>
        </div>
        
        <div class="status-bar">
          <div class="wifi-status {{"online" if wifi_status == "Connected" else "offline"}}">
            <span class="status-icon">{"📶" if wifi_status == "Connected" else "📴"}</span>
            <span>{wifi_status}</span>
          </div>
          <div class="pending-uploads">
            {offline_count} pending uploads
          </div>
        </div>
        
        <div class="cards">
          <div class="card card-temp">
            <div class="card-icon">🌡️</div>
            <div class="card-value">{temp:.1f} °C</div>
            <div class="card-label">Temperature</div>
          </div>
          
          <div class="card card-pressure">
            <div class="card-icon">📊</div>
            <div class="card-value">{pressure:.1f}</div>
            <div class="card-label">Pressure (hPa)</div>
          </div>
        </div>
        
        <div class="last-updated">
          Last updated: <span>{current_time}</span>
        </div>
        
        <div class="footer">
          <p>IoT Coursework Project by Saicharan Gnanapiragasam</p>
        </div>
      </div>
    </body>
    </html>
    """
    return html

def send_to_spreadsheet(timestamp, temp, pressure):
    """Send data to Google Spreadsheet via Apps Script"""
    try:
        url = f"{SCRIPT_URL}?time={timestamp}&sensor1={temp}&pressure={pressure}"
        print(f"Sending data to spreadsheet: {url}")
        
        res = urequests.get(url=url)
        res.close()
        gc.collect()  # Garbage collection
        
        print("Data sent to spreadsheet successfully")
        return True
    except Exception as e:
        print(f"Error sending data to spreadsheet: {e}")
        return False

def serve(connection, wlan):
    """
    Handle web server connections and periodically update all outputs:
    - Shell display
    - Web server
    - Spreadsheet
    - Store offline readings when disconnected
    """
    # Initialize counters
    epoch_counter = 0  # Start from 0
    log_interval = 2  # seconds
    spreadsheet_interval = 5  # seconds
    reconnect_interval = 30  # seconds
    last_log_time = time()
    last_spreadsheet_time = time()
    last_reconnect_time = time()
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    
    print("Weather station running. Press Ctrl+C to stop.")
    print(f"Epoch {epoch_counter}")  # Print initial epoch to ensure we see epoch 0
    
    while True:
        client = None
        
        try:
            # Read sensor data
            temperature = bme.temperature
            pressure = bme.pressure
            
            # Current network status
            is_connected = wlan.isconnected()
            wifi_status = "Connected" if is_connected else "Disconnected"
            
            # Get count of offline readings
            offline_readings = get_offline_readings()
            offline_count = len(offline_readings)
            
            # Increment epoch counter
            epoch_counter += 1
            current_time = time()
            
            # 1. Log to shell periodically
            if current_time - last_log_time >= log_interval:
                print(f"Epoch {epoch_counter}")
                print(f"Temperature: {temperature:.2f}°C, Pressure: {pressure:.2f}hPa")
                print(f"WiFi Status: {wifi_status}, Pending Uploads: {offline_count}")
                last_log_time = current_time
            
            # 2. Send to spreadsheet or store offline periodically
            if current_time - last_spreadsheet_time >= spreadsheet_interval:
                timestamp = get_formatted_time()
                
                if is_connected:
                    # First try to upload any offline readings
                    if offline_count > 0:
                        upload_offline_readings(wlan)
                    
                    # Then send current reading
                    send_to_spreadsheet(timestamp, temperature, pressure)
                else:
                    # Store reading offline
                    save_offline_reading(timestamp, temperature, pressure)
                    
                last_spreadsheet_time = current_time
            
            # 3. Try to reconnect if disconnected
            if not is_connected and current_time - last_reconnect_time >= reconnect_interval:
                if reconnect_attempts < max_reconnect_attempts:
                    print(f"Attempting to reconnect to WiFi (attempt {reconnect_attempts + 1}/{max_reconnect_attempts})...")
                    wlan.connect(ssid, password)
                    
                    # Wait for connection
                    for _ in range(10):
                        if wlan.isconnected():
                            print("Successfully reconnected to WiFi")
                            board_led.on()  # Solid LED when connected
                            
                            # Update connection and try to upload offline readings
                            is_connected = True
                            wifi_status = "Connected"
                            
                            # Try to upload offline readings immediately
                            if offline_count > 0:
                                upload_offline_readings(wlan)
                            
                            reconnect_attempts = 0  # Reset counter on successful reconnection
                            break
                        sleep(1)
                        board_led.toggle()  # Blink during reconnection
                    
                    if not wlan.isconnected():
                        reconnect_attempts += 1
                        board_led.off()  # Turn off LED when disconnected
                        print(f"Failed to reconnect. Will try again in {reconnect_interval} seconds")
                else:
                    # After max attempts, wait longer before trying again
                    print("Max reconnection attempts reached. Waiting for 5 minutes before trying again.")
                    reconnect_attempts = 0
                    sleep(300)  # Wait 5 minutes
                
                last_reconnect_time = current_time
            
            # 4. Handle web server (non-blocking) if we have a connection
            if connection:
                try:
                    # Accept client connection with timeout
                    client, addr = connection.accept()
                    print(f"Client connected from {addr}")
                    
                    request = client.recv(1024)
                    request = str(request)
                    
                    # Serve webpage with current readings and status
                    html = webpage(temperature, pressure, wifi_status, offline_count)
                    client.send("HTTP/1.1 200 OK\r\n")
                    client.send("Content-Type: text/html\r\n")
                    client.send("Connection: close\r\n\r\n")
                    client.sendall(html.encode())
                    
                    print(f"[WEB] Served webpage with Temperature: {temperature:.2f}°C, Pressure: {pressure:.2f}hPa")
                except OSError:
                    # No client connected within timeout, continue
                    pass
            
            # Short sleep to prevent CPU maxing
            sleep(0.1)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if client:
                client.close()

# Main entry point
try:
    # First scan for available networks
    scan_wifi_networks()
    
    # Connect to Wi-Fi
    ip, wlan = connect_to_network()
    
    # Get time to validate connection
    if ip:
        print(f"Current time: {get_time()}")
        # Set up web server
        connection = open_socket(ip)
    else:
        print("Running in offline mode")
        connection = None
    
    # Start serving (this function runs indefinitely)
    serve(connection, wlan)
except KeyboardInterrupt:
    print("Server interrupted. Restarting...")
    machine.reset()