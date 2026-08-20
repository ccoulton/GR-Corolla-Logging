import wifi

#Wi-Fi
ssid = "CAN-CAM-grcorolla-"
password = "12345678"

def scan_for_wifi():
    networks = []
    for network in wifi.radio.start_scanning_networks():
        networks.append(network)
    wifi.radio.stop_scanning_networks()
    networks = sorted(networks, key=lambda net: net.rssi, reverse=False)
    for network in networks:
        print("ssid: ", network.ssid, "rssi: ", network.rssi)
        if network.ssid is ssid:
            print("Dashcam AP found.")
            return True

def connect_to_wifi():
    try:
        print("Attempting Wi-Fi connection to ", ssid)
        wifi.radio.connect(ssid, password)
    except Exception as e:
        print("Connection failed: ", e)
        
while True:
    if not wifi.radio.connected and scan_for_wifi():
        connect_to_wifi()
    else:
        print(wifi.radio.ipv4_gateway) 
