import ipaddress
import asyncio
import aiohttp

CIDR_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/Clash/Cloudflare.txt'
OPTIMIZED_DOMAINS_FILE = '优选域名.txt'
OPTIMIZED_IPS_FILE = '优选域名ip.txt'

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    # 读取所有查询结果
    all_results = []
    for method in ['bgp', 'dns_google', 'cloudflare']:
        with open(f'ip_results_{method}.txt', 'r') as f:
            all_results.extend([line.strip().split(',') for line in f])

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

if __name__ == "__main__":
    asyncio.run(main())
