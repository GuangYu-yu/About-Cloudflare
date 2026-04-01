import aiohttp
import asyncio

from bs4 import BeautifulSoup
import os
import ipaddress
import random
import re

from collections import defaultdict

# 定义常量
GROUP_1_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/matching_domains.list'
GROUP_2_URLS = [
    'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/%E5%A4%A7%E9%87%8F%E4%BC%98%E9%80%89%E5%9F%9F%E5%90%8D.txt',
    'https://github.com/Potterli20/file/releases/download/dns-hosts-all/dnshosts-all-domain-whitelist_full.txt'
]
GROUP_3_URL = 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/AdGuard/Advertising/Advertising.txt'
CIDR_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/Clash/Cloudflare.txt'
CACHED_CIDR_FILE = 'cached_cidr.txt'

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_group_1(session):
    print("正在获取第一组域名...")
    text = await fetch(session, GROUP_1_URL)
    domains = {}
    for line in text.splitlines():
        if line.startswith("DOMAIN") or line.startswith("DOMAIN-SUFFIX"):
            parts = line.split(',')
            if len(parts) == 2:
                prefix, domain = parts
                if domain not in domains:
                    domains[domain] = {'prefix': prefix, 'ips': set()}
    return domains

async def fetch_group_2(session):
    domains = {}
    for url in GROUP_2_URLS:
        print(f"正在获取第二组域名: {url}")
        text = await fetch(session, url)
        for line in text.splitlines():
            domain = line.strip()
            if domain and domain not in domains:
                domains[domain] = {'prefix': '', 'ips': set()}
    return domains

async def fetch_group_3(session):
    print("正在获取第三组域名...")
    text = await fetch(session, GROUP_3_URL)
    domains = {}
    for line in text.splitlines():
        match = re.search(r'\|\|([^\^]+)\^', line)
        if match:
            domain = match.group(1)
            if domain not in domains:
                domains[domain] = {'prefix': '', 'ips': set()}
    return domains

async def query_ip_info(session, domain):
    await asyncio.sleep(random.uniform(1, 3))  # 减少延迟时间
    query_url = f"https://bgp.he.net/dns/{domain}#_ipinfo"
    async with session.get(query_url) as response:
        text = await response.text()
    soup = BeautifulSoup(text, 'html.parser')
    ip_info_div = soup.find('div', id='ipinfo')
    if ip_info_div:
        return {a.get('title') for a in ip_info_div.find_all('a') if a.get('href', '').startswith('/ip/')}
    return set()

async def load_and_cache_cidr_list(session):
    print("下载并缓存 CIDR 列表...")
    text = await fetch(session, CIDR_URL)
    cidr_list = text.splitlines()
    
    with open(CACHED_CIDR_FILE, 'w') as f:
        for cidr in cidr_list:
            f.write(f"{cidr}\n")
    
    return cidr_list

def load_cached_cidr_list():
    print("从缓存加载 CIDR 列表...")
    with open(CACHED_CIDR_FILE, 'r') as f:
        return f.read().splitlines()

def is_ip_in_cidr(ip, cidr_list):
    ip_obj = ipaddress.ip_address(ip)
    return any(ip_obj in ipaddress.ip_network(cidr.strip(), strict=False) for cidr in cidr_list if '/' in cidr)

async def main():
    try:
        print("脚本开始执行...")
        
        async with aiohttp.ClientSession() as session:
            # 下载并缓存 CIDR 列表
            await load_and_cache_cidr_list(session)

            # 获取三组域名
            domains_group_1 = await fetch_group_1(session)
            domains_group_2 = await fetch_group_2(session)
            domains_group_3 = await fetch_group_3(session)

            # 合并所有域名
            all_domains = {**domains_group_1, **domains_group_2, **domains_group_3}
            
            # 异步查询 IP 信息
            tasks = [query_ip_info(session, domain) for domain in all_domains]
            results = await asyncio.gather(*tasks)
            
            for domain, ips in zip(all_domains, results):
                all_domains[domain]['ips'] = ips

            # 添加日志记录
            print(f"总域名数量: {len(all_domains)}")
            print(f"查询到IP的域名数量: {sum(1 for domain in all_domains.values() if domain['ips'])}")

            # 从缓存加载 CIDR 列表
            cidr_list = load_cached_cidr_list()

            # 保存优选域名和优选域名IP
            优选域名 = set()
            ipv4_set = set()
            ipv6_set = set()

            for domain, data in all_domains.items():
                for ip in data['ips']:
                    if is_ip_in_cidr(ip, cidr_list):
                        优选域名.add(domain)
                        if ':' in ip:  # IPv6
                            ipv6_set.add(ip)
                        else:  # IPv4
                            ipv4_set.add(ip)
                        break  # 找到一个匹配后跳出循环

            # 写入优选域名
            with open('优选域名.txt', 'w') as f_domains:
                for domain in sorted(优选域名):
                    f_domains.write(f"{domain}\n")

            # 写入优选域名IP
            with open('优选域名ip.txt', 'w') as f_ips:
                for ip in sorted(ipv4_set):
                    f_ips.write(f"{ip}\n")
                for ip in sorted(ipv6_set):
                    f_ips.write(f"{ip}\n")

            print(f"匹配到的优选域名数量: {len(优选域名)}")
            print(f"优选IPv4地址数量: {len(ipv4_set)}")
            print(f"优选IPv6地址数量: {len(ipv6_set)}")

            # 添加结果验证
            total_ips = len(ipv4_set) + len(ipv6_set)
            if len(优选域名) == 0 or total_ips == 0:
                print("警告：没有找到优选域名或IP地址，请检查处理逻辑")

    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 删除缓存的 CIDR 文件
        if os.path.exists(CACHED_CIDR_FILE):
            os.remove(CACHED_CIDR_FILE)
            print("已删除缓存的 CIDR 文件")

if __name__ == '__main__':
    asyncio.run(main())
