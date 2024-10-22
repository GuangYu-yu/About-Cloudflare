import asyncio
import aiohttp

# 定义URL常量
GROUP_1_URL = 'https://raw.githubusercontent.com/GuangYu-yu/ACL4SSR/refs/heads/main/matching_domains.list'
GROUP_2_URLS = [
    'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/%E5%A4%A7%E9%87%8F%E4%BC%98%E9%80%89%E5%9F%9F%E5%90%8D.txt',
    'https://github.com/Potterli20/file/releases/download/dns-hosts-all/dnshosts-all-domain-whitelist_full.txt'
]
GROUP_3_URL = 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/AdGuard/Advertising/Advertising.txt'

# 临时文件名
TEMP_DOMAINS_FILE = 'temp_domains.txt'

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_domains():
    async with aiohttp.ClientSession() as session:
        # 获取第一组域名
        group1_content = await fetch_url(session, GROUP_1_URL)
        group1_domains = [line.split(',')[1] for line in group1_content.splitlines() if line.startswith(('DOMAIN,', 'DOMAIN-SUFFIX,'))]

        # 获取第二组域名
        group2_domains = []
        for url in GROUP_2_URLS:
            content = await fetch_url(session, url)
            group2_domains.extend(content.splitlines())

        # 获取第三组域名
        group3_content = await fetch_url(session, GROUP_3_URL)
        group3_domains = [line.strip('|^') for line in group3_content.splitlines() if line.startswith('||') and line.endswith('^')]

        # 合并去重
        all_domains = list(set(group1_domains + group2_domains + group3_domains))

        # 将域名列表分割成多个部分
        query_methods = ['bgp', 'cloudflare', 'google', 'quad9', 'opendns', 'twnic']
        domains_per_method = len(all_domains) // len(query_methods)
        
        for i, method in enumerate(query_methods):
            start = i * domains_per_method
            end = start + domains_per_method if i < len(query_methods) - 1 else len(all_domains)
            method_domains = all_domains[start:end]
            
            with open(f'domains_{method}.txt', 'w') as f:
                f.write('\n'.join(method_domains))

        return all_domains

if __name__ == "__main__":
    asyncio.run(fetch_domains())
