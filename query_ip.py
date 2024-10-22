import asyncio
import random
import time
from bs4 import BeautifulSoup
import aiohttp
import sys
import dns.resolver

async def query_with_rate_limit(func, *args):
    while True:
        try:
            await asyncio.sleep(random.uniform(1, 3))
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
    
    async def fetch_ip(url):
        async with session.get(url) as response:
            data = await response.json()
            if data.get('Answer'):
                return [answer['data'] for answer in data['Answer'] if answer['type'] in (1, 28)]
            return []

    ipv4 = await fetch_ip(ipv4_url)
    ipv6 = await fetch_ip(ipv6_url)
    return list(set(ipv4 + ipv6))

async def query_dns(domain, nameserver):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    try:
        ipv4 = [str(ip) for ip in resolver.resolve(domain, 'A')]
        ipv6 = [str(ip) for ip in resolver.resolve(domain, 'AAAA')]
        return list(set(ipv4 + ipv6))
    except:
        return []

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

    # 根据查询方法选择域名子集
    query_methods = ['bgp', 'cloudflare', 'google', 'quad9', 'opendns', 'twnic']
    method_index = query_methods.index(query_method)
    total_domains = len(all_domains)
    domains_per_method = total_domains // len(query_methods)
    remainder = total_domains % len(query_methods)

    start = method_index * domains_per_method + min(method_index, remainder)
    if method_index < remainder:
        end = start + domains_per_method + 1
    else:
        end = start + domains_per_method

    domains = all_domains[start:end]

    print(f"Processing {len(domains)} domains for method: {query_method}")

    semaphore = asyncio.Semaphore(10)  # 限制并发查询数为10

    if query_method == 'bgp':
        results = await process_domains(domains, query_bgp, semaphore)
    elif query_method == 'google':
        results = await process_domains(domains, query_dns_google, semaphore)
    elif query_method in ['twnic', 'quad9', 'opendns', 'cloudflare']:
        nameservers = {
            'twnic': '101.101.101.101',
            'quad9': '9.9.9.10',
            'opendns': '208.67.222.222',
            'cloudflare': '1.1.1.1'
        }
        results = await process_domains(domains, lambda s, d: query_dns(d, nameservers[query_method]), semaphore)
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
