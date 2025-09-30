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

async def query_dns_json(session, ipv4_url, ipv6_url):
    async def fetch_ip(url):
        headers = {
            'accept': 'application/dns-json'
        }
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    if data.get('Answer'):
                        return [answer['data'] for answer in data['Answer'] if answer['type'] in (1, 28)]
                except aiohttp.ContentTypeError:
                    print(f"解析JSON失败: {url}")
            else:
                print(f"查询失败: {url} 返回状态码 {response.status}")
            return []

    ipv4 = await fetch_ip(ipv4_url)
    ipv6 = await fetch_ip(ipv6_url)
    return list(set(ipv4 + ipv6))

async def query_dns_google(session, domain):
    return await query_dns_json(session, 
        f"https://dns.google/resolve?name={domain}&type=A",
        f"https://dns.google/resolve?name={domain}&type=AAAA")

async def query_dns_quad9(session, domain):
    return await query_dns_json(session, 
        f"https://dns10.quad9.net:5053/dns-query?name={domain}&type=A",
        f"https://dns10.quad9.net:5053/dns-query?name={domain}&type=AAAA")

async def query_dns_twnic(session, domain):
    return await query_dns_json(session, 
        f"https://dns.twnic.tw/dns-query?name={domain}&type=A",
        f"https://dns.twnic.tw/dns-query?name={domain}&type=AAAA")

async def query_dns_sb(session, domain):
    return await query_dns_json(session, 
        f"https://doh.sb/dns-query?name={domain}&type=A",
        f"https://doh.sb/dns-query?name={domain}&type=AAAA")

async def query_dns_kr_sel(session, domain):
    return await query_dns_json(session, 
        f"https://kr-sel.doh.sb/dns-query?name={domain}&type=A",
        f"https://kr-sel.doh.sb/dns-query?name={domain}&type=AAAA")

async def query_dns_sg_sin(session, domain):
    return await query_dns_json(session, 
        f"https://sg-sin.doh.sb/dns-query?name={domain}&type=A",
        f"https://sg-sin.doh.sb/dns-query?name={domain}&type=AAAA")

async def query_dns_jp_nrt(session, domain):
    return await query_dns_json(session, 
        f"https://jp-nrt.doh.sb/dns-query?name={domain}&type=A",
        f"https://jp-nrt.doh.sb/dns-query?name={domain}&type=AAAA")

async def query_dns_hk_hkg(session, domain):
    return await query_dns_json(session, 
        f"https://hk-hkg.doh.sb/dns-query?name={domain}&type=A",
        f"https://hk-hkg.doh.sb/dns-query?name={domain}&type=AAAA")

async def query_dns_uk_lon(session, domain):
    return await query_dns_json(session, 
        f"https://uk-lon.doh.sb/dns-query?name={domain}&type=A",
        f"https://uk-lon.doh.sb/dns-query?name={domain}&type=AAAA")

async def query_dns_de_fra(session, domain):
    return await query_dns_json(session, 
        f"https://de-fra.doh.sb/dns-query?name={domain}&type=A",
        f"https://de-fra.doh.sb/dns-query?name={domain}&type=AAAA")

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
    query_methods = ['de_fra', 'google', 'quad9', 'twnic', 'uk_lon', 'sb', 'kr_sel', 'sg_sin', 'jp_nrt', 'hk_hkg']
    method_ratios = {'de_fra': 60, 'google': 71, 'quad9': 71, 'twnic': 58, 'uk_lon': 62, 'sb': 68, 'kr_sel': 62, 'sg_sin': 38, 'jp_nrt': 51, 'hk_hkg': 45}
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

    query_functions = {
        'de_fra': query_dns_de_fra,
        'google': query_dns_google,
        'quad9': query_dns_quad9,
        'twnic': query_dns_twnic,
        'uk_lon': query_dns_uk_lon,
        'sb': query_dns_sb,
        'kr_sel': query_dns_kr_sel,
        'sg_sin': query_dns_sg_sin,
        'jp_nrt': query_dns_jp_nrt,
        'hk_hkg': query_dns_hk_hkg
    }

    if query_method in query_functions:
        try:
            results = await process_domains(domains, query_functions[query_method], semaphore)
        except Exception as e:
            print(f"处理 {query_method} 时发生错误: {e}")
            return
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
