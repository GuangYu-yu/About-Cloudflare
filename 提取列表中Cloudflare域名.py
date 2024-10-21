import requests
import yaml
from bs4 import BeautifulSoup
import concurrent.futures
import os
import ipaddress
import threading
import random
import time
import re

# 定义常量
GROUP_1_URL = 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/Global/Global.list'
GROUP_2_URLS = [
    'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/%E5%A4%A7%E9%87%8F%E4%BC%98%E9%80%89%E5%9F%9F%E5%90%8D.txt',
    'https://github.com/Potterli20/file/releases/download/dns-hosts-all/dnshosts-all-domain-whitelist_full.txt'
]
GROUP_3_URL = 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/AdGuard/Advertising/Advertising.txt'
CIDR_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/Clash/Cloudflare.txt'
TEMP_YAML_FILE = 'temp_domains.yaml'
CACHED_CIDR_FILE = 'cached_cidr.txt'

# 初始化锁
file_lock = threading.Lock()

def fetch_group_1():
    print("正在获取第一组域名...")
    response = requests.get(GROUP_1_URL)
    response.raise_for_status()
    domains = {}
    for line in response.text.splitlines():
        if line.startswith("DOMAIN") or line.startswith("DOMAIN-SUFFIX"):
            parts = line.split(',')
            if len(parts) == 2:
                prefix, domain = parts
                if domain not in domains:
                    domains[domain] = {'prefix': prefix, 'ips': []}
    return domains

def fetch_group_2():
    domains = {}
    for url in GROUP_2_URLS:
        print(f"正在获取第二组域名: {url}")
        response = requests.get(url)
        response.raise_for_status()
        for line in response.text.splitlines():
            domain = line.strip()
            if domain and domain not in domains:
                domains[domain] = {'prefix': '', 'ips': []}
    return domains

def fetch_group_3():
    print("正在获取第三组域名...")
    response = requests.get(GROUP_3_URL)
    response.raise_for_status()
    domains = {}
    for line in response.text.splitlines():
        match = re.search(r'\|\|([^\^]+)\^', line)
        if match:
            domain = match.group(1)
            if domain not in domains:
                domains[domain] = {'prefix': '', 'ips': []}
    return domains

def query_ip_info(domain, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(3, 5))  # Delay of 3 to 5 seconds
            query_url = f"https://bgp.he.net/dns/{domain}#_ipinfo"
            response = requests.get(query_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            ip_info_div = soup.find('div', id='ipinfo')
            if ip_info_div:
                ips = [a.get('title') for a in ip_info_div.find_all('a') if a.get('href', '').startswith('/ip/')]
                return list(set(ips))  # 确保返回的IP去重
            return []
        except Exception:
            continue  # 继续重试
    return []  # 返回空列表

def load_cidr_list():
    print("加载 CIDR 列表...")
    response = requests.get(CIDR_URL)
    response.raise_for_status()
    return response.text.splitlines()

def save_temp_yaml(domains):
    """将整个域名和IP数据写入临时YAML文件。"""
    with open(TEMP_YAML_FILE, 'w') as f:
        yaml.dump(domains, f)

def is_ip_in_cidr(ip, cidr_list):
    for cidr in cidr_list:
        if '/' in cidr:
            network = ipaddress.ip_network(cidr.strip())
            if ipaddress.ip_address(ip) in network:
                return True
    return False

def main():
    try:
        print("脚本开始执行...")
        
        # 获取三组域名
        domains_group_1 = fetch_group_1()
        domains_group_2 = fetch_group_2()
        domains_group_3 = fetch_group_3()

        # 合并所有域名
        all_domains = {**domains_group_1, **domains_group_2, **domains_group_3}
        queried_domains = set()  # 记录已查询的域名
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_domain = {executor.submit(query_ip_info, domain): domain for domain in all_domains}
            for future in concurrent.futures.as_completed(future_to_domain):
                domain = future_to_domain[future]
                queried_domains.add(domain)  # 添加到已查询列表
                try:
                    ips = future.result()
                    if ips:
                        all_domains[domain]['ips'].extend(ips)
                        # 实时写入临时 YAML 文件
                        save_temp_yaml(all_domains)
                except Exception:
                    continue  # 忽略查询错误

        # 加载 CIDR 列表
        cidr_list = load_cidr_list()
        with open(CACHED_CIDR_FILE, 'w') as f:
            for cidr in cidr_list:
                f.write(f"{cidr}\n")

        # 保存优选域名和优选域名IP
        with open('优选域名.txt', 'w') as f_domains, open('优选域名ip.txt', 'w') as f_ips:
            for domain, data in all_domains.items():
                for ip in data['ips']:
                    if is_ip_in_cidr(ip, cidr_list):
                        f_domains.write(f"{domain}\n")
                        f_ips.write(f"{ip}\n")
                        break  # 找到一个匹配后跳出循环

        print(f"匹配到的优选域名数量: {len(all_domains)}")

        # 删除临时 YAML 文件和缓存的 CIDR 文件
        if os.path.exists(TEMP_YAML_FILE):
            os.remove(TEMP_YAML_FILE)
        if os.path.exists(CACHED_CIDR_FILE):
            os.remove(CACHED_CIDR_FILE)

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == '__main__':
    main()
