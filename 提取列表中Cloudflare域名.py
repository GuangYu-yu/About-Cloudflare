import requests
import concurrent.futures
import os
import re
import ipaddress
import uuid

# 定义文件路径
URLS_WITH_PREFIX = [
    'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/Global/Global.list',
]

URLS_NORMAL_DOMAINS = [
    'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/%E5%A4%A7%E9%87%8F%E4%BC%98%E9%80%89%E5%9F%9F%E5%90%8D.txt',
    'https://github.com/Potterli20/file/releases/download/dns-hosts-all/dnshosts-all-domain-whitelist_full.txt',
]

URLS_ADS = [
    'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/AdGuard/Advertising/Advertising.txt',
]

def fetch_domains_with_prefix(url):
    """获取带前缀的域名列表"""
    response = requests.get(url)
    response.raise_for_status()
    domains = set()
    for line in response.text.splitlines():
        if line.startswith('DOMAIN-SUFFIX,') or line.startswith('DOMAIN,'):
            domain = line.split(',')[1].strip()
            domains.add(domain)
    return domains

def fetch_normal_domains(url):
    """获取正常域名列表"""
    response = requests.get(url)
    response.raise_for_status()
    domains = set()
    for line in response.text.splitlines():
        domains.add(line.strip())
    return domains

def fetch_ads_domains(url):
    """获取广告域名列表"""
    response = requests.get(url)
    response.raise_for_status()
    domains = set()
    for line in response.text.splitlines():
        if '||' in line and '^' in line:
            domain = line.split('||')[1].split('^')[0].strip()
            domains.add(domain)
    return domains

def cache_page(url):
    """缓存网页内容到本地文件"""
    response = requests.get(url)
    response.raise_for_status()
    cache_file = f'cache_{uuid.uuid4()}.html'
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    return cache_file

def clear_cache(cache_file):
    """删除缓存文件"""
    if os.path.exists(cache_file):
        os.remove(cache_file)

def check_cloudflare_ip_via_bgp(domain):
    """通过 bgp.he.net 查询 Cloudflare IP"""
    try:
        url = f'https://bgp.he.net/dns/{domain}#_ipinfo'
        cache_file = cache_page(url)
        with open(cache_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'Cloudflare' in content:
                ip_matches = re.findall(r'<a href="/ip/([\d\.a-fA-F:]+)" title="[\d\.a-fA-F:]+">', content)
                clear_cache(cache_file)
                return domain, set(ip_matches)
    except Exception as e:
        print(f"通过bgp.he.net检查 {domain} 时出错: {e}")
    clear_cache(cache_file)
    return None

def process_domain(domain):
    """处理每个域名，查询其 Cloudflare IP"""
    return check_cloudflare_ip_via_bgp(domain)

def main():
    """主函数，执行查询和结果保存"""
    all_domains = set()

    # 从带前缀的域名获取
    for url in URLS_WITH_PREFIX:
        all_domains.update(fetch_domains_with_prefix(url))

    # 从正常域名获取
    for url in URLS_NORMAL_DOMAINS:
        all_domains.update(fetch_normal_domains(url))

    # 从广告域名获取
    for url in URLS_ADS:
        all_domains.update(fetch_ads_domains(url))

    all_cloudflare_ips = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_domain, domain): domain for domain in all_domains}
        for future in concurrent.futures.as_completed(futures):
            domain = futures[future]
            try:
                result = future.result()
                if result:
                    all_cloudflare_ips.update(result[1])
            except Exception as e:
                print(f"处理域名 {domain} 时出错: {e}")

    # 分离IPv4和IPv6地址
    ipv4_addresses = set()
    ipv6_addresses = set()

    for ip in all_cloudflare_ips:
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.version == 4:
                ipv4_addresses.add(ip)
            else:
                ipv6_addresses.add(ip.lower())
        except ValueError:
            print(f"无效的IP地址: {ip}")

    # 分别排序IPv4和IPv6地址
    sorted_ipv4 = sorted(ipv4_addresses, key=lambda ip: ipaddress.IPv4Address(ip))
    sorted_ipv6 = sorted(ipv6_addresses, key=lambda ip: ipaddress.IPv6Address(ip))

    # 保存优选域名（不带前缀）到文件
    with open('优选域名.txt', 'w', encoding='utf-8') as f:
        for domain in sorted(all_domains):
            f.write(f"{domain}\n")

# 获取 Cloudflare CIDR 列表并转换为 ip_network 对象
cloudflare_cidrs_url = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/Clash/Cloudflare.txt'
response = requests.get(cloudflare_cidrs_url)
cloudflare_cidrs = [ipaddress.ip_network(cidr.strip()) for cidr in response.text.splitlines() if cidr.strip()]

# 检查 IP 是否在 Cloudflare CIDR 范围内
def is_ip_in_cloudflare(ip):
    ip_obj = ipaddress.ip_address(ip)
    return any(ip_obj in cidr for cidr in cloudflare_cidrs)

# 保存匹配的 IP 到文件
with open('优选域名ip.txt', 'w', encoding='utf-8') as f:
    # 过滤并保存匹配的 IPv4 地址
    for ip in sorted_ipv4:
        if is_ip_in_cloudflare(ip):
            f.write(f"{ip}\n")
    
    # 过滤并保存匹配的 IPv6 地址
    for ip in sorted_ipv6:
        if is_ip_in_cloudflare(ip):
            f.write(f"{ip}\n")

    print(f"优选域名已保存到 优选域名.txt 文件中，共 {len(all_domains)} 个。")
    print(f"提取的 Cloudflare IP 已保存到 优选域名ip.txt 文件中，共 {len(sorted_ipv4) + len(sorted_ipv6)} 个。")
    print(f"其中 IPv4 地址 {len(sorted_ipv4)} 个，IPv6 地址 {len(sorted_ipv6)} 个。")

if __name__ == '__main__':
    main()
