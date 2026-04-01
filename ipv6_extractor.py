import requests
from bs4 import BeautifulSoup
import ipaddress

def get_prefix_from_address(address, ip_version='IPv6'):
    """转换前缀：IPv6 转 /48，IPv4 转 /24"""
    try:
        clean_addr = address.strip()
        
        if '/' in clean_addr:
            network = ipaddress.ip_network(clean_addr, strict=False)
        else:
            if ip_version == 'IPv6':
                ip = ipaddress.IPv6Address(clean_addr)
                full_ip = format(int(ip), '032x')
                prefix = ':'.join([full_ip[i:i+4] for i in range(0, 12, 4)])
                network = ipaddress.IPv6Network(f"{prefix}::/48")
            else:  # IPv4
                octets = clean_addr.split('.')
                prefix = f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
                network = ipaddress.IPv4Network(prefix, strict=False)
        
        return str(network)
    except Exception as e:
        print(f"处理地址时出错 {clean_addr}: {e}")
        return None

def get_ipv6_prefixes():
    try:
        prefixes = set()
        
        # IPv6 existing_url
        existing_url_v6 = 'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/ipv6_prefixes.txt'
        try:
            resp = requests.get(existing_url_v6)
            resp.raise_for_status()
            for line in resp.text.splitlines():
                line = line.strip()
                if line:
                    prefix = get_prefix_from_address(line, 'IPv6')
                    if prefix:
                        prefixes.add(prefix)
                        print(f"从现有文件添加 (IPv6): {prefix}")
        except requests.exceptions.RequestException as e:
            print(f"获取现有IPv6前缀时发生错误: {e}")

        # IPv6 网页源
        source_url_v6 = 'https://www.wetest.vip/page/cloudflare/address_v6.html'
        response = requests.get(source_url_v6)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for td in soup.find_all('td'):
            if td.string:
                text = td.string.strip()
                if ':' in text:
                    prefix = get_prefix_from_address(text, 'IPv6')
                    if prefix:
                        prefixes.add(prefix)
                        print(f"从网页提取 (IPv6): {prefix}")

        sorted_prefixes = sorted(prefixes, key=lambda x: ipaddress.ip_network(x))
        with open('ipv6_prefixes.txt', 'w') as f:
            for prefix in sorted_prefixes:
                f.write(prefix + '\n')

        print(f"成功提取 {len(prefixes)} 个IPv6前缀并保存到 ipv6_prefixes.txt")

    except Exception as e:
        print(f"处理IPv6时发生错误: {e}")

def get_ipv4_prefixes():
    try:
        prefixes = set()
        
        # IPv4 existing_url
        existing_url_v4 = 'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/ipv4_prefixes.txt'
        try:
            resp = requests.get(existing_url_v4)
            resp.raise_for_status()
            for line in resp.text.splitlines():
                line = line.strip()
                if line:
                    prefix = get_prefix_from_address(line, 'IPv4')
                    if prefix:
                        prefixes.add(prefix)
                        print(f"从现有文件添加 (IPv4): {prefix}")
        except requests.exceptions.RequestException as e:
            print(f"获取现有IPv4前缀时发生错误: {e}")

        # IPv4 网页源
        source_url_v4 = 'https://www.wetest.vip/page/cloudflare/address_v4.html'
        response = requests.get(source_url_v4)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for td in soup.find_all('td'):
            if td.string:
                text = td.string.strip()
                if '.' in text:
                    prefix = get_prefix_from_address(text, 'IPv4')
                    if prefix:
                        prefixes.add(prefix)
                        print(f"从网页提取 (IPv4): {prefix}")

        sorted_prefixes = sorted(prefixes, key=lambda x: ipaddress.ip_network(x))
        with open('ipv4_prefixes.txt', 'w') as f:
            for prefix in sorted_prefixes:
                f.write(prefix + '\n')

        print(f"成功提取 {len(prefixes)} 个IPv4前缀并保存到 ipv4_prefixes.txt")

    except Exception as e:
        print(f"处理IPv4时发生错误: {e}")

if __name__ == "__main__":
    get_ipv6_prefixes()
    get_ipv4_prefixes()
