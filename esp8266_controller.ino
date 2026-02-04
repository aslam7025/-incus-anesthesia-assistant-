import requests

# --- CONFIGURATION ---
esp_ip = "192.168.1.15"  # REPLACE with your ESP8266 IP address
# ---------------------

def send_command(value):
    url = f"http://{esp_ip}/{value}"
    try:
        print(f"Sending value: {value} to {url}...")
        response = requests.get(url, timeout=2) # Send the HTTP GET request
        
        if response.status_code == 200:
            print("Success! Board received the command.")
        else:
            print(f"Board replied with status: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the board. Check IP and WiFi.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Main loop to keep asking for input
if __name__ == "__main__":
    print(f"--- ESP8266 Controller ({esp_ip}) ---")
    print("Type '1' to turn ON, '2' to turn OFF, 'q' to quit.")
    
    while True:
        user_input = input("\nEnter value: ")
        
        if user_input.lower() == 'q':
            break
            
        # Ensure we only send numbers
        if user_input.isdigit():
            send_command(user_input)
        else:
            print("Please enter a valid number.")
