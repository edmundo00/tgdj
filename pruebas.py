from scapy.layers.inet import IP
from scapy.layers.l2 import ARP
from scapy.sendrecv import sr1

def scan_network():
    devices = []
    for i in range(1, 255):  # Rango de IPs de 192.168.1.1 a 192.168.1.254
        ip = f"192.168.1.{i}"
        arp_request = ARP(pdst=ip)
        try:
            response = sr1(arp_request, timeout=0.5, verbose=0)  # Enviar paquete ARP
            if response:  # Si hay respuesta, agregar el dispositivo
                devices.append({
                    "IP Address": response.psrc,
                    "MAC Address": response.hwsrc
                })
        except Exception as e:
            print(f"Error al escanear {ip}: {e}")

    return devices

# Ejecutar el script
if __name__ == "__main__":
    devices = scan_network()
    print("Devices found:")
    for device in devices:
        print(f"IP: {device['IP Address']}, MAC: {device['MAC Address']}")
