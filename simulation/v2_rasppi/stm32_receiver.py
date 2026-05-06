import socket
import time

# --- CONFIGURATION ---
# Replace this with the MAC address of your STM32's Bluetooth module
TARGET_MAC = "00:06:66:6E:10:B8" 
PORT = 1  # 1 is the standard RFCOMM port for serial Bluetooth modules

def receive_bluetooth_data():
    print(f"🔌 Attempting to connect to {TARGET_MAC} on port {PORT}...")
    
    # Initialize the Bluetooth socket
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        # Connect to the STM32
        sock.connect((TARGET_MAC, PORT))
        print("Connected successfully! Listening for data...\n")

        while True:
            # Receive up to 1024 bytes of data
            data = sock.recv(1024)
            
            if not data:
                print("No data received. Connection might be lost.")
                break
            
            # Assuming the STM32 is sending standard strings via UART
            # .strip() removes any trailing newlines or carriage returns
            try:
                decoded_data = data.decode('utf-8').strip()
                if decoded_data:
                    print(f"STM32 says: {decoded_data}")
            except UnicodeDecodeError:
                # If you are sending raw bytes/hex instead of text, handle it here
                print(f"Raw bytes received: {data.hex()}")

    except ConnectionRefusedError:
        print("Connection refused. Make sure the STM32 is powered on and paired.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()
        print("Socket closed.")

if __name__ == "__main__":
    while True:
        receive_bluetooth_data()
        time.sleep(5)