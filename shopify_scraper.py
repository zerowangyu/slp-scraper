#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用 Shopify 商品数据爬虫
支持任意 Shopify 网站的商品采集
"""

import requests
import pandas as pd
import time
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

# 配置
PRODUCTS_PER_PAGE = 250  # Shopify API 每页最大数量
REQUEST_DELAY = 0.5  # 请求间隔（秒），避免被限流

# HTTP请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 全局 session 对象
session = requests.Session()
session.headers.update(HEADERS)


def normalize_url(url: str) -> str:
    """标准化 URL"""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # 移除末尾的斜杠
    url = url.rstrip('/')
    
    # 只保留域名部分
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def is_shopify_site(base_url: str) -> bool:
    """检测是否是 Shopify 网站"""
    try:
        # 尝试访问 products.json
        response = session.get(
            urljoin(base_url, "/products.json?limit=1"),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return "products" in data
    except:
        pass
    
    try:
        # 尝试访问 collections.json
        response = session.get(
            urljoin(base_url, "/collections.json"),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return "collections" in data
    except:
        pass
    
    return False


def fetch_json(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """发送GET请求并返回JSON数据"""
    try:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"请求失败: {url}, 错误: {e}")
        return None


def get_all_collections(base_url: str) -> List[Dict]:
    """获取所有分类信息"""
    print("正在获取分类列表...")
    url = urljoin(base_url, "/collections.json")
    data = fetch_json(url)
    
    if data and "collections" in data:
        collections = data["collections"]
        print(f"共找到 {len(collections)} 个分类")
        return collections
    return []


def get_collection_products(base_url: str, collection_handle: str, collection_title: str) -> List[Dict]:
    """获取指定分类下的所有商品（支持分页）"""
    products = []
    page = 1
    
    while True:
        url = urljoin(base_url, f"/collections/{collection_handle}/products.json")
        params = {"limit": PRODUCTS_PER_PAGE, "page": page}
        
        data = fetch_json(url, params)
        
        if not data or "products" not in data:
            break
            
        page_products = data["products"]
        if not page_products:
            break
            
        for product in page_products:
            product["_category"] = collection_title
            
        products.extend(page_products)
        print(f"  - 分类 [{collection_title}] 第{page}页: 获取 {len(page_products)} 个商品")
        
        if len(page_products) < PRODUCTS_PER_PAGE:
            break
            
        page += 1
        time.sleep(REQUEST_DELAY)
    
    return products


def get_all_products_directly(base_url: str) -> List[Dict]:
    """直接从 /products.json 获取所有商品（包括未分类的商品）"""
    print("\n正在获取所有商品（包括未分类商品）...")
    products = []
    page = 1
    
    while True:
        url = urljoin(base_url, "/products.json")
        params = {"limit": PRODUCTS_PER_PAGE, "page": page}
        
        data = fetch_json(url, params)
        
        if not data or "products" not in data:
            break
            
        page_products = data["products"]
        if not page_products:
            break
        
        for product in page_products:
            product["_category"] = "全部商品"
            
        products.extend(page_products)
        print(f"  - 第{page}页: 获取 {len(page_products)} 个商品")
        
        if len(page_products) < PRODUCTS_PER_PAGE:
            break
            
        page += 1
        time.sleep(REQUEST_DELAY)
    
    print(f"直接获取完成，共 {len(products)} 个商品")
    return products


def extract_product_info(product: Dict, base_url: str) -> List[Dict]:
    """从商品数据中提取所需信息"""
    records = []
    
    product_name = product.get("title", "")
    product_handle = product.get("handle", "")
    product_url = urljoin(base_url, f"/products/{product_handle}")
    category = product.get("_category", "")
    product_id = product.get("id", "")
    vendor = product.get("vendor", "")
    product_type = product.get("product_type", "")
    
    variants = product.get("variants", [])
    
    if not variants:
        records.append({
            "product_id": product_id,
            "product_name": product_name,
            "sku": "",
            "barcode": "",
            "category": category,
            "vendor": vendor,
            "product_type": product_type,
            "price": "",
            "compare_at_price": "",
            "stock_status": "未知",
            "product_url": product_url,
        })
    else:
        for variant in variants:
            sku = variant.get("sku", "") or ""
            barcode = variant.get("barcode", "") or ""
            price = variant.get("price", "") or ""
            compare_at_price = variant.get("compare_at_price", "") or ""
            
            available = variant.get("available", None)
            if available is True:
                stock_status = "有库存"
            elif available is False:
                stock_status = "售罄"
            else:
                stock_status = "未知"
            
            variant_title = variant.get("title", "")
            if variant_title and variant_title != "Default Title":
                full_name = f"{product_name} - {variant_title}"
            else:
                full_name = product_name
            
            records.append({
                "product_id": product_id,
                "product_name": full_name,
                "sku": sku,
                "barcode": barcode,
                "category": category,
                "vendor": vendor,
                "product_type": product_type,
                "price": price,
                "compare_at_price": compare_at_price,
                "stock_status": stock_status,
                "product_url": product_url,
            })
    
    return records


def deduplicate_products(all_records: List[Dict]) -> List[Dict]:
    """去重处理：同一商品可能出现在多个分类中"""
    seen = {}
    
    for record in all_records:
        key = (record["product_id"], record["sku"], record["barcode"])
        
        if key not in seen:
            seen[key] = record.copy()
        else:
            existing_category = seen[key]["category"]
            new_category = record["category"]
            if new_category and new_category not in existing_category:
                seen[key]["category"] = f"{existing_category}; {new_category}"
    
    return list(seen.values())


def get_safe_filename(url: str) -> str:
    """从 URL 生成安全的文件名"""
    parsed = urlparse(url)
    domain = parsed.netloc
    # 移除不安全的字符
    safe_name = re.sub(r'[^\w\-.]', '_', domain)
    return f"{safe_name}_products.csv"


def save_to_csv(records: List[Dict], filename: str):
    """将数据保存为CSV文件"""
    if not records:
        print("没有数据可保存")
        return
    
    df = pd.DataFrame(records)
    
    columns = ["product_name", "sku", "barcode", "category", "vendor", "product_type", 
               "price", "compare_at_price", "stock_status", "product_url"]
    
    # 只保留存在的列
    columns = [c for c in columns if c in df.columns]
    df = df[columns]
    
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n数据已保存到 {filename}")
    print(f"共 {len(df)} 条记录")


def scrape_shopify_site(base_url: str) -> str:
    """爬取指定的 Shopify 网站"""
    print("=" * 60)
    print(f"开始爬取: {base_url}")
    print("=" * 60)
    
    # 检测是否是 Shopify 网站
    print("\n正在检测网站类型...")
    if not is_shopify_site(base_url):
        print("❌ 该网站不是 Shopify 网站，或无法访问其 API")
        return ""
    print("✅ 确认是 Shopify 网站")
    
    # 1. 获取所有分类
    collections = get_all_collections(base_url)
    
    valid_collections = [
        c for c in collections 
        if c.get("products_count", 0) > 0 
        and c.get("handle") != "all"
    ]
    
    if valid_collections:
        print(f"\n有效分类数量: {len(valid_collections)}")
        for c in valid_collections[:10]:  # 只显示前10个
            print(f"  - {c.get('title')}: {c.get('products_count', '?')} 个商品")
        if len(valid_collections) > 10:
            print(f"  ... 还有 {len(valid_collections) - 10} 个分类")
    
    # 2. 遍历每个分类获取商品
    print("\n" + "=" * 60)
    print("开始获取商品数据...")
    print("=" * 60)
    
    all_records = []
    
    for collection in valid_collections:
        handle = collection.get("handle", "")
        title = collection.get("title", "")
        
        if not handle:
            continue
            
        products = get_collection_products(base_url, handle, title)
        
        for product in products:
            records = extract_product_info(product, base_url)
            all_records.extend(records)
        
        time.sleep(REQUEST_DELAY)
    
    print(f"\n从分类获取完成，共 {len(all_records)} 条记录")
    
    # 3. 直接获取所有商品（补充未分类的商品）
    all_products = get_all_products_directly(base_url)
    for product in all_products:
        records = extract_product_info(product, base_url)
        all_records.extend(records)
    
    print(f"\n全部获取完成，共 {len(all_records)} 条原始记录")
    
    # 4. 去重
    print("\n正在去重...")
    unique_records = deduplicate_products(all_records)
    print(f"去重后剩余 {len(unique_records)} 条记录")
    
    # 5. 保存为CSV
    filename = get_safe_filename(base_url)
    print("\n" + "=" * 60)
    save_to_csv(unique_records, filename)
    print("=" * 60)
    
    return filename


def main():
    """主函数"""
    print("=" * 60)
    print("通用 Shopify 商品数据爬虫")
    print("支持任意 Shopify 网站")
    print("=" * 60)
    
    while True:
        print("\n请输入要爬取的网站地址（输入 q 退出）:")
        print("示例: slptrading.com.au 或 https://example.myshopify.com")
        
        url_input = input("\n网址: ").strip()
        
        if url_input.lower() == 'q':
            print("\n感谢使用，再见！")
            break
        
        if not url_input:
            print("❌ 请输入有效的网址")
            continue
        
        base_url = normalize_url(url_input)
        print(f"\n标准化后的网址: {base_url}")
        
        try:
            filename = scrape_shopify_site(base_url)
            if filename:
                print(f"\n✅ 爬取完成！数据已保存到: {filename}")
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断操作")
        except Exception as e:
            print(f"\n❌ 爬取失败: {e}")
        
        print("\n" + "-" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n程序出错: {e}")
    finally:
        print("\n")
        input("按回车键退出...")
