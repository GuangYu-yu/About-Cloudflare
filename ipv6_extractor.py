import requests
from bs4 import BeautifulSoup
import ipaddress

def get_prefix_from_address(address):
    """转换/48前缀"""
    try:
        # 清理地址
        clean_addr = address.strip()
        
        # 如果是CIDR格式，获取网络的第一个IP
        if '/' in clean_addr:
            network = ipaddress.IPv6Network(clean_addr)
            ip = network[0]
        else:
            # 如果是普通IP地址
            ip = ipaddress.IPv6Address(clean_addr)
        
        # 获取完整展开的IP地址（八组，每组四个字符）
        full_ip = format(int(ip), '032x')
        # 取前三组（每组四个字符）
        prefix = ':'.join([full_ip[i:i+4] for i in range(0, 12, 4)])
        # 创建/48网络，ipaddress会自动进行压缩
        network = ipaddress.IPv6Network(f"{prefix}::/48")
        return str(network)
    except Exception as e:
        print(f"处理地址时出错 {clean_addr}: {e}")
        return None

def get_ipv6_prefixes():
    try:
        # 获取现有的前缀列表
        prefixes = set()
        
        # 定义URL
        source_url = 'https://www.182682.xyz/page/cloudflare/address_v6.html'
        existing_url = 'https://raw.githubusercontent.com/GuangYu-yu/About-Cloudflare/refs/heads/main/ipv6_prefixes.txt'
        
        # 从现有URL获取前缀
        try:
            existing_response = requests.get(existing_url)
            existing_response.raise_for_status()
            for line in existing_response.text.splitlines():
                line = line.strip()
                if line:
                    prefix = get_prefix_from_address(line)
                    if prefix:
                        prefixes.add(prefix)
                        print(f"从现有文件添加前缀: {prefix}")
        except requests.exceptions.RequestException as e:
            print(f"获取现有内容时发生错误: {e}")

        # 获取新的前缀
        response = requests.get(source_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有包含IPv6地址的td标签
        for td in soup.find_all('td'):
            if td.string:  # 只处理直接文本内容
                text = td.string.strip()
                if ':' in text:  # 只处理包含冒号的文本（可能是IPv6地址）
                    prefix = get_prefix_from_address(text)
                    if prefix:
                        prefixes.add(prefix)
                        print(f"从网页提取前缀: {prefix}")
        
        if not prefixes:
            print("警告：没有找到任何IPv6地址")
            return
        
        # 转换为IPv6Network对象进行排序
        sorted_prefixes = sorted(
            prefixes,
            key=lambda x: ipaddress.IPv6Network(x)
        )
        
        # 将结果写入文件，每行一个前缀
        with open('ipv6_prefixes.txt', 'w') as f:
            for prefix in sorted_prefixes:
                f.write(prefix + '\n')
        
        print(f"成功提取了 {len(prefixes)} 个IPv6前缀并保存到 ipv6_prefixes.txt")
        print("提取的前缀：")
        for prefix in sorted_prefixes:
            print(prefix)
        
    except requests.exceptions.RequestException as e:
        print(f"获取网页时发生错误: {e}")
    except Exception as e:
        print(f"处理数据时发生错误: {e}")

if __name__ == "__main__":
    get_ipv6_prefixes()
