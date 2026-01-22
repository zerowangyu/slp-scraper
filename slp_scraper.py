#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLP Trading 商品数据爬虫
从 slptrading.com.au 获取所有商品信息并保存为CSV文件
"""

import requests
import pandas as pd
import time
import json
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

# 配置
BASE_URL = "https://slptrading.com.au"
PRODUCTS_PER_PAGE = 250  # Shopify API 每页最大数量
REQUEST_DELAY = 0.5  # 请求间隔（秒），避免被限流

# 登录账号配置
LOGIN_EMAIL = "jimmy@umall.com.au"
LOGIN_PASSWORD = "Umall20201101"
ENABLE_LOGIN = False  # 设为 True 启用浏览器登录功能（需要手动完成验证码）
COOKIES_FILE = "cookies.json"  # Cookies 文件路径（从浏览器导出）

# HTTP请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 全局 session 对象
session = requests.Session()
session.headers.update(HEADERS)


def load_cookies_from_file() -> bool:
    """从文件加载 Cookies（从浏览器导出的）"""
    if not os.path.exists(COOKIES_FILE):
        return False
    
    print(f"正在从 {COOKIES_FILE} 加载 Cookies...")
    
    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
        
        # 支持多种格式的 cookies 文件
        if isinstance(cookies_data, list):
            # EditThisCookie 导出格式 或 Playwright 格式
            for cookie in cookies_data:
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                domain = cookie.get('domain', '.slptrading.com.au')
                if name and value:
                    session.cookies.set(name, value, domain=domain)
        elif isinstance(cookies_data, dict):
            # 简单的 {name: value} 格式
            for name, value in cookies_data.items():
                session.cookies.set(name, value, domain='.slptrading.com.au')
        
        print(f"  已加载 {len(session.cookies)} 个 Cookies")
        
        # 验证登录状态
        test_url = urljoin(BASE_URL, "/account")
        response = session.get(test_url, timeout=30, allow_redirects=False)
        
        if response.status_code == 200 or "/account" in response.headers.get('location', ''):
            print("  Cookies 有效，已登录！")
            return True
        else:
            print("  Cookies 无效或已过期")
            return False
            
    except Exception as e:
        print(f"  加载 Cookies 失败: {e}")
        return False


def export_cookies_to_file():
    """将当前 session 的 cookies 导出到文件"""
    cookies_list = []
    for cookie in session.cookies:
        cookies_list.append({
            'name': cookie.name,
            'value': cookie.value,
            'domain': cookie.domain,
            'path': cookie.path,
        })
    
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies_list, f, ensure_ascii=False, indent=2)
    
    print(f"  Cookies 已保存到 {COOKIES_FILE}")


def login() -> bool:
    """使用 Playwright 模拟浏览器登录，获取 cookies 后传递给 requests session"""
    print("正在使用浏览器登录...")
    print("注意：网站可能需要验证码，将打开浏览器窗口让您手动完成验证")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("错误：未安装 Playwright，请运行: pip install playwright && playwright install chromium")
        return False
    
    login_url = urljoin(BASE_URL, "/account/login")
    
    try:
        with sync_playwright() as p:
            # 启动可见浏览器（方便用户处理验证码）
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="zh-CN"
            )
            page = context.new_page()
            
            # 访问登录页面
            print("  正在访问登录页面...")
            page.goto(login_url, wait_until="networkidle")
            
            # 填写登录表单
            print("  正在填写登录信息...")
            email_input = page.locator('input[name="customer[email]"]')
            password_input = page.locator('input[name="customer[password]"]')
            
            # 等待登录表单加载
            email_input.wait_for(state="visible", timeout=10000)
            
            # 填写表单
            email_input.fill(LOGIN_EMAIL)
            password_input.fill(LOGIN_PASSWORD)
            
            # 点击登录按钮
            print("  正在提交登录...")
            time.sleep(1)
            
            # 使用 JavaScript 提交表单
            page.evaluate('''
                const forms = document.querySelectorAll('form');
                for (const form of forms) {
                    if (form.querySelector('input[name="customer[email]"]')) {
                        form.submit();
                        break;
                    }
                }
            ''')
            
            # 等待并检查是否有验证码
            print("  等待页面响应...")
            time.sleep(3)
            
            # 检查是否有验证码弹窗
            page_content = page.content()
            if "captcha" in page_content.lower() or "验证" in page_content or "找出" in page_content:
                print("\n" + "=" * 50)
                print("检测到验证码！请在浏览器窗口中完成验证...")
                print("完成后请等待页面跳转...")
                print("=" * 50 + "\n")
                
                # 等待用户完成验证码（最多等待60秒）
                max_wait = 60
                for i in range(max_wait):
                    time.sleep(1)
                    current_url = page.url
                    if "/login" not in current_url:
                        break
                    if i == max_wait - 1:
                        print("  等待超时，请重新运行程序")
            
            # 等待页面稳定
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass
            time.sleep(2)
            
            # 检查是否登录成功
            current_url = page.url
            print(f"  当前页面: {current_url}")
            
            if "/login" not in current_url:
                print(f"  登录成功！账号: {LOGIN_EMAIL}")
                
                # 获取 cookies 并传递给 requests session
                cookies = context.cookies()
                for cookie in cookies:
                    session.cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie.get("domain", ""),
                        path=cookie.get("path", "/")
                    )
                
                print(f"  已获取 {len(cookies)} 个 cookies")
                
                # 保存 cookies 到文件，下次可以直接使用
                export_cookies_to_file()
                
                browser.close()
                return True
            else:
                print("  登录失败，请检查账号密码是否正确")
                browser.close()
                return False
                
    except Exception as e:
        print(f"  登录过程出错: {e}")
        return False


def fetch_json(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """发送GET请求并返回JSON数据（使用登录后的session）"""
    try:
        response = session.get(url, params=params, timeout=30)
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


def get_all_products_directly() -> List[Dict]:
    """直接从 /products.json 获取所有商品（包括未分类的商品）"""
    print("\n正在获取所有商品（包括未分类商品）...")
    products = []
    page = 1
    
    while True:
        url = urljoin(BASE_URL, "/products.json")
        params = {"limit": PRODUCTS_PER_PAGE, "page": page}
        
        data = fetch_json(url, params)
        
        if not data or "products" not in data:
            break
            
        page_products = data["products"]
        if not page_products:
            break
        
        # 标记为"全部商品"分类
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
            "stock_status": "未知",
            "product_url": product_url,
        })
    else:
        for variant in variants:
            sku = variant.get("sku", "") or ""
            price = variant.get("price", "") or ""
            compare_at_price = variant.get("compare_at_price", "") or ""
            
            # 获取库存状态
            available = variant.get("available", None)
            if available is True:
                stock_status = "有库存"
            elif available is False:
                stock_status = "售罄"
            else:
                stock_status = "未知"
            
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
                "stock_status": stock_status,
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
    columns = ["product_name", "sku", "category", "price", "compare_at_price", "stock_status", "product_url"]
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
    
    # 0. 尝试登录
    logged_in = False
    
    # 首先尝试从 cookies 文件加载
    if os.path.exists(COOKIES_FILE):
        logged_in = load_cookies_from_file()
    
    # 如果没有有效的 cookies，且启用了登录功能，则尝试浏览器登录
    if not logged_in and ENABLE_LOGIN and LOGIN_EMAIL and LOGIN_PASSWORD:
        logged_in = login()
        if not logged_in:
            print("警告：登录失败，将以游客身份继续获取数据")
    
    if not logged_in:
        print("以游客身份获取数据")
        print("提示：如需登录，请按以下步骤操作：")
        print("  1. 用 Chrome 浏览器访问 https://slptrading.com.au/account/login")
        print("  2. 手动登录成功后，安装 'EditThisCookie' 浏览器扩展")
        print("  3. 点击扩展图标，选择'导出Cookies'，保存为 cookies.json")
        print("  4. 将 cookies.json 放到爬虫目录下，重新运行程序")
    
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
    
    print(f"\n从分类获取完成，共 {len(all_records)} 条记录")
    
    # 2.5 直接获取所有商品（补充未分类的商品）
    all_products = get_all_products_directly()
    for product in all_products:
        records = extract_product_info(product)
        all_records.extend(records)
    
    print(f"\n全部获取完成，共 {len(all_records)} 条原始记录")
    
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
