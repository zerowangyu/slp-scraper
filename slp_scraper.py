#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLP Trading 商品数据爬虫
从 slptrading.com.au 获取所有商品信息并保存为CSV文件
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

# 配置
BASE_URL = "https://slptrading.com.au"
PRODUCTS_PER_PAGE = 250  # Shopify API 每页最大数量
REQUEST_DELAY = 0.5  # 请求间隔（秒），避免被限流

# HTTP请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_json(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """发送GET请求并返回JSON数据"""
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"请求失败: {url}, 错误: {e}")
        return None


def get_all_collections() -> List[Dict]:
    """获取所有分类信息"""
    print("正在获取分类列表...")
    url = urljoin(BASE_URL, "/collections.json")
    data = fetch_json(url)
    
    if data and "collections" in data:
        collections = data["collections"]
        print(f"共找到 {len(collections)} 个分类")
        return collections
    return []


def get_collection_products(collection_handle: str, collection_title: str) -> List[Dict]:
    """获取指定分类下的所有商品（支持分页）"""
    products = []
    page = 1
    
    while True:
        url = urljoin(BASE_URL, f"/collections/{collection_handle}/products.json")
        params = {"limit": PRODUCTS_PER_PAGE, "page": page}
        
        data = fetch_json(url, params)
        
        if not data or "products" not in data:
            break
            
        page_products = data["products"]
        if not page_products:
            break
            
        # 为每个商品添加分类信息
        for product in page_products:
            product["_category"] = collection_title
            
        products.extend(page_products)
        print(f"  - 分类 [{collection_title}] 第{page}页: 获取 {len(page_products)} 个商品")
        
        # 如果返回数量小于limit，说明已经是最后一页
        if len(page_products) < PRODUCTS_PER_PAGE:
            break
            
        page += 1
        time.sleep(REQUEST_DELAY)
    
    return products


def extract_product_info(product: Dict) -> List[Dict]:
    """
    从商品数据中提取所需信息
    一个商品可能有多个variants（规格），每个variant作为一条记录
    """
    records = []
    
    product_name = product.get("title", "")
    product_handle = product.get("handle", "")
    product_url = urljoin(BASE_URL, f"/products/{product_handle}")
    category = product.get("_category", "")
    product_id = product.get("id", "")
    
    variants = product.get("variants", [])
    
    if not variants:
        # 如果没有variants，创建一条基本记录
        records.append({
            "product_id": product_id,
            "product_name": product_name,
            "sku": "",
            "category": category,
            "price": "",
            "compare_at_price": "",
            "product_url": product_url,
        })
    else:
        for variant in variants:
            sku = variant.get("sku", "") or ""
            price = variant.get("price", "") or ""
            compare_at_price = variant.get("compare_at_price", "") or ""
            
            # 如果variant有自己的标题且不是默认标题，添加到商品名称
            variant_title = variant.get("title", "")
            if variant_title and variant_title != "Default Title":
                full_name = f"{product_name} - {variant_title}"
            else:
                full_name = product_name
            
            records.append({
                "product_id": product_id,
                "product_name": full_name,
                "sku": sku,
                "category": category,
                "price": price,
                "compare_at_price": compare_at_price,
                "product_url": product_url,
            })
    
    return records


def deduplicate_products(all_records: List[Dict]) -> List[Dict]:
    """
    去重处理：同一商品可能出现在多个分类中
    保留第一次出现的记录，但合并分类信息
    """
    # 使用 (product_id, sku) 作为唯一标识
    seen = {}
    
    for record in all_records:
        key = (record["product_id"], record["sku"])
        
        if key not in seen:
            seen[key] = record.copy()
        else:
            # 合并分类信息
            existing_category = seen[key]["category"]
            new_category = record["category"]
            if new_category and new_category not in existing_category:
                seen[key]["category"] = f"{existing_category}; {new_category}"
    
    return list(seen.values())


def save_to_csv(records: List[Dict], filename: str = "slp_products.csv"):
    """将数据保存为CSV文件"""
    if not records:
        print("没有数据可保存")
        return
    
    df = pd.DataFrame(records)
    
    # 选择并排序输出列
    columns = ["product_name", "sku", "category", "price", "compare_at_price", "product_url"]
    df = df[columns]
    
    # 保存为CSV
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n数据已保存到 {filename}")
    print(f"共 {len(df)} 条记录")


def main():
    """主函数"""
    print("=" * 60)
    print("SLP Trading 商品数据爬虫")
    print("=" * 60)
    
    # 1. 获取所有分类
    collections = get_all_collections()
    
    if not collections:
        print("无法获取分类信息，程序退出")
        return
    
    # 过滤掉空分类和特殊分类
    valid_collections = [
        c for c in collections 
        if c.get("products_count", 0) > 0 
        and c.get("handle") != "all"  # 排除"全部商品"分类，避免重复
    ]
    
    print(f"\n有效分类数量: {len(valid_collections)}")
    for c in valid_collections:
        print(f"  - {c.get('title')}: {c.get('products_count')} 个商品")
    
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
            
        products = get_collection_products(handle, title)
        
        for product in products:
            records = extract_product_info(product)
            all_records.extend(records)
        
        time.sleep(REQUEST_DELAY)
    
    print(f"\n获取完成，共 {len(all_records)} 条原始记录")
    
    # 3. 去重
    print("\n正在去重...")
    unique_records = deduplicate_products(all_records)
    print(f"去重后剩余 {len(unique_records)} 条记录")
    
    # 4. 保存为CSV
    print("\n" + "=" * 60)
    save_to_csv(unique_records)
    print("=" * 60)
    print("爬虫任务完成！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n程序出错: {e}")
    finally:
        # 等待用户按键后退出，防止窗口立即关闭
        print("\n")
        input("按回车键退出...")
