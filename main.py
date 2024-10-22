import asyncio
import aiohttp
import ipaddress
import os
from fetch_domains import fetch_domains
from query_ip import query_bgp, query_dns_google

# 定义URL常量
CIDR_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/Clash/Cloudflare.txt'

# 临时文件名
TEMP_DOMAINS_FILE = 'temp_domains.txt'

# 结果文件名
OPTIMIZED_DOMAINS_FILE = '优选域名.txt'
OPTIMIZED_IPS_FILE = '优选域名ip.txt'

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

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

async def main():
    # 获取域名列表
    domains = await fetch_domains()
    
    # 将域名列表按1:2的比例分为两部分
    google_domains = domains[:len(domains) // 3]
    bgp_domains = domains[len(domains) // 3:]

    # 创建两个任务
    semaphore_bgp = asyncio.Semaphore(10)  # BGP查询限制为10个并发
    semaphore_dns = asyncio.Semaphore(5)   # DNS查询限制为5个并发
    task1 = asyncio.create_task(process_domains(google_domains, query_dns_google, semaphore_dns))
    task2 = asyncio.create_task(process_domains(bgp_domains, query_bgp, semaphore_bgp))

    # 等待两个任务完成
    results1, results2 = await asyncio.gather(task1, task2)

    # 合并结果
    all_results = results1 + results2

    # 获取CIDR列表
    async with aiohttp.ClientSession() as session:
        cidr_content = await fetch_url(session, CIDR_URL)
    cidr_list = [ipaddress.ip_network(line.split(',')[1]) for line in cidr_content.splitlines() if line.startswith('IP-CIDR,')]

    # 匹配IP和CIDR
    optimized_domains = set()
    optimized_ips = set()

    for domain, ip in all_results:
        try:
            ip_obj = ipaddress.ip_address(ip)
            if any(ip_obj in cidr for cidr in cidr_list):
                optimized_domains.add(domain)
                optimized_ips.add(ip)
        except ValueError:
            print(f"无效的IP地址: {ip}")

    # 保存结果
    with open(OPTIMIZED_DOMAINS_FILE, 'w') as f:
        f.write('\n'.join(sorted(optimized_domains)))

    with open(OPTIMIZED_IPS_FILE, 'w') as f:
        f.write('\n'.join(sorted(optimized_ips)))

    # 删除临时文件
    os.remove(TEMP_DOMAINS_FILE)

if __name__ == "__main__":
    asyncio.run(main())
