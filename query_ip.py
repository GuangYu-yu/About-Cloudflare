import asyncio
import random
import time
from bs4 import BeautifulSoup
import aiohttp
import sys

async def query_bgp(session, domain):
    while True:
        try:
            await asyncio.sleep(random.uniform(3, 5))
            query_url = f"https://bgp.he.net/dns/{domain}#_ipinfo"
            async with session.get(query_url) as response:
                content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            ip_info_div = soup.find('div', id='ipinfo')
            if ip_info_div:
                ips = [a.get('title') for a in ip_info_div.find_all('a') if a.get('href', '').startswith('/ip/')]
                return list(set(ips))
            return []
        except Exception as e:
            print(f"查询域名失败：{domain}，错误信息: {e}")
            continue

async def query_dns_google(session, domain):
    ipv4_url = f"https://dns.google/resolve?name={domain}&type=A"
    ipv6_url = f"https://dns.google/resolve?name={domain}&type=AAAA"
    
    async def fetch_ip(url):
        async with session.get(url) as response:
            data = await response.json()
            if data.get('Answer'):
                return [answer['data'] for answer in data['Answer'] if answer['type'] in (1, 28)]
            return []

    ipv4 = await fetch_ip(ipv4_url)
    ipv6 = await fetch_ip(ipv6_url)
    return list(set(ipv4 + ipv6))

async def query_cloudflare(session, domain):
    ipv4_url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=A"
    ipv6_url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=AAAA"
    
    async def fetch_ip(url):
        headers = {'accept': 'application/dns-json'}
        async with session.get(url, headers=headers) as response:
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
                ips = await query_func(session, domain)
                results.extend((domain, ip) for ip in ips)

        tasks = [asyncio.create_task(worker(domain)) for domain in domains]
        await asyncio.gather(*tasks)
    
    return results

async def main(query_method):
    with open('temp_domains.txt', 'r') as f:
        domains = f.read().splitlines()

    if query_method == 'bgp':
        semaphore = asyncio.Semaphore(10)
        results = await process_domains(domains, query_bgp, semaphore)
    elif query_method == 'dns_google':
        semaphore = asyncio.Semaphore(5)
        results = await process_domains(domains, query_dns_google, semaphore)
    elif query_method == 'cloudflare':
        semaphore = asyncio.Semaphore(5)
        results = await process_domains(domains, query_cloudflare, semaphore)
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
