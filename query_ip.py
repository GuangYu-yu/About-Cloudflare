import asyncio
import random
import time
from bs4 import BeautifulSoup
import aiohttp
import sys
import math
import json

async def query_with_rate_limit(func, *args):
    while True:
        try:
            await asyncio.sleep(random.uniform(1, 2))
            return await func(*args)
        except Exception as e:
            print(f"查询失败: {e}")
            await asyncio.sleep(2)

async def query_bgp(session, domain):
    query_url = f"https://bgp.he.net/dns/{domain}#_ipinfo"
    async with session.get(query_url) as response:
        content = await response.text()
    soup = BeautifulSoup(content, 'html.parser')
    ip_info_div = soup.find('div', id='ipinfo')
    if ip_info_div:
        ips = [a.get('title') for a in ip_info_div.find_all('a') if a.get('href', '').startswith('/ip/')]
        return list(set(ips))
    return []

async def query_dns_google(session, domain):
    ipv4_url = f"https://dns.google/resolve?name={domain}&type=A"
    ipv6_url = f"https://dns.google/resolve?name={domain}&type=AAAA"
    return await query_dns_json(session, ipv4_url, ipv6_url)

async def query_dns_quad9(session, domain):
    ipv4_url = f"https://dns10.quad9.net:5053/dns-query?name={domain}&type=A"
    ipv6_url = f"https://dns10.quad9.net:5053/dns-query?name={domain}&type=AAAA"
    return await query_dns_json(session, ipv4_url, ipv6_url)

async def query_dns_twnic(session, domain):
    ipv4_url = f"https://dns.twnic.tw/dns-query?name={domain}&type=A"
    ipv6_url = f"https://dns.twnic.tw/dns-query?name={domain}&type=AAAA"
    return await query_dns_json(session, ipv4_url, ipv6_url)

async def query_dns_json(session, ipv4_url, ipv6_url):
    async def fetch_ip(url):
        async with session.get(url) as response:
            data = await response.json()
            if data.get('Answer'):
                return [answer['data'] for answer in data['Answer'] if answer['type'] in (1, 28)]
            return []

    ipv4 = await fetch_ip(ipv4_url)
    ipv6 = await fetch_ip(ipv6_url)
    return list(set(ipv4 + ipv6))

async def process_domains(domains, query_func, semaphore):
    results = []
    async with aiohttp.ClientSession() as session:
        async def worker(domain):
            async with semaphore:
                ips = await query_with_rate_limit(query_func, session, domain)
                results.extend((domain, ip) for ip in ips)

        tasks = [asyncio.create_task(worker(domain)) for domain in domains]
        await asyncio.gather(*tasks)
    
    return results

async def main(query_method):
    with open('temp_domains.txt', 'r') as f:
        all_domains = f.read().splitlines()

    # 新的查询方法和比例
    query_methods = ['bgp', 'google', 'quad9', 'twnic']
    method_ratios = {'bgp': 4, 'google': 4, 'quad9': 1, 'twnic': 1}
    total_ratio = sum(method_ratios.values())

    total_domains = len(all_domains)
    method_index = query_methods.index(query_method)

    # 计算每个方法应处理的域名数量
    domains_per_ratio = total_domains / total_ratio
    start = 0
    for i in range(method_index):
        start += math.ceil(domains_per_ratio * method_ratios[query_methods[i]])
    
    end = start + math.ceil(domains_per_ratio * method_ratios[query_method])
    end = min(end, total_domains)  # 确保不超过总域名数

    domains = all_domains[start:end]

    print(f"Processing {len(domains)} domains for method: {query_method}")

    semaphore = asyncio.Semaphore(10)  # 限制并发查询数为10

    if query_method == 'bgp':
        results = await process_domains(domains, query_bgp, semaphore)
    elif query_method == 'google':
        results = await process_domains(domains, query_dns_google, semaphore)
    elif query_method == 'quad9':
        results = await process_domains(domains, query_dns_quad9, semaphore)
    elif query_method == 'twnic':
        results = await process_domains(domains, query_dns_twnic, semaphore)
    else:
        print(f"未知的查询方法: {query_method}")
        return

    with open(f'ip_results_{query_method}.txt', 'w') as f:
        for domain, ip in results:
            f.write(f"{domain},{ip}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query_ip.py <query_method>")
        sys.exit(1)
    
    query_method = sys.argv[1]
    asyncio.run(main(query_method))
