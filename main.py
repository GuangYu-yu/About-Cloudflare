import asyncio
import aiohttp
import ipaddress
import os
from fetch_domains import fetch_domains, TEMP_DOMAINS_FILE

# 定义URL常量
CIDR_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/Clash/Cloudflare.txt'

# 结果文件名
OPTIMIZED_DOMAINS_FILE = '优选域名.txt'
OPTIMIZED_IPS_FILE = '优选域名ip.txt'

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    # 获取并分割域名列表
    await fetch_domains()
    
    query_methods = ['de_fra', 'google', 'quad9', 'twnic', 'uk_lon', 'sb', 'kr_sel', 'sg_sin', 'jp_nrt', 'hk_hkg']
    
    results = []
    for method in query_methods:
        file_path = f'ip-results-{method}/ip_results_{method}.txt'
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                method_results = [line.strip().split(',') for line in f]
                results.extend(method_results)
        else:
            print(f"警告: 文件 {file_path} 不存在")
    
    # 获取CIDR列表
    async with aiohttp.ClientSession() as session:
        cidr_content = await fetch_url(session, CIDR_URL)
    cidr_list = []
    for line in cidr_content.splitlines():
        line = line.strip()
        if line:
            try:
                cidr_list.append(ipaddress.ip_network(line))
            except ValueError as e:
                print(f"无效的CIDR: {line}. 错误: {e}")

    print(f"有效的CIDR数量: {len(cidr_list)}")

    # 匹配IP和CIDR
    optimized_domains = set()
    optimized_ips = set()

    for domain, ip in results:
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

    # 清理临时文件
    if os.path.exists(TEMP_DOMAINS_FILE):
        os.remove(TEMP_DOMAINS_FILE)
    for method in query_methods:
        file_path = f'ip-results-{method}/ip_results_{method}.txt'
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    asyncio.run(main())
