import json
import asyncio
from pyppeteer import launch
from datetime import datetime, timedelta
import aiofiles
import random
import requests
import os
import sys
# --- 导入 stealth ---
from pyppeteer_stealth import stealth

# 从环境变量中获取 Telegram Bot Token 和 Chat ID
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def format_to_iso(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')

async def delay_time(ms):
    await asyncio.sleep(ms / 1000)

# 全局浏览器实例
browser = None
# 标记是否有任何一次登录失败
any_login_failed = False

async def login(username, password, panel):
    global browser
    global any_login_failed

    page = None  # 确保 page 在任何情况下都被定义
    serviceName = 'ct8' if 'ct8' in panel else 'serv00'
    error_screenshot_path = f'error_{username}_{serviceName}.png'

    try:
        if not browser:
            print("正在启动新的浏览器实例...")
            browser = await launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage', # 优化在 Docker/Actions 中的内存使用
                    '--disable-gpu', # 禁用 GPU
                ]
            )
            print("浏览器实例已启动。")

        page = await browser.newPage()
        
        await stealth(page)
        print("Stealth 补丁已应用。")

        await page.setViewport({'width': 1280, 'height': 1024})
        
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8'
        })
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
        
        url = f'https://{panel}/login/?next=/'
        print(f"正在导航到: {url}")
        await page.goto(url, {'timeout': 30000}) # 30秒超时
        
        await delay_time(2000)

        page_content = await page.content()
        if '<body></body>' in page_content.replace(" ", ""):
            print("检测到空白页面，反爬虫系统可能已激活。")
            raise Exception("空白页面，被反爬虫系统拦截")

        print("等待用户名输入框...")
        username_input_selector = 'input[name="username"]'
        await page.waitForSelector(username_input_selector, {'timeout': 30000, 'visible': True})

        print("等待密码输入框...")
        password_input_selector = 'input[name="password"]'
        await page.waitForSelector(password_input_selector, {'timeout': 30000, 'visible': True})
        
        print("等待登录按钮 (双语)...")
        login_button_xpath = "//button[span[normalize-space()='Zaloguj się'] or span[normalize-space()='Sign in']]"
        await page.waitForXPath(login_button_xpath, {'timeout': 30000, 'visible': True})
        
        print("元素已全部加载。")
        await delay_time(500) 

        print("输入用户名...")
        await page.focus(username_input_selector)
        await page.keyboard.type(username, {'delay': 50})
        
        await delay_time(500)
        
        print("输入密码...")
        await page.focus(password_input_selector)
        await page.keyboard.type(password, {'delay': 50})
        
        await delay_time(1000) 

        print("正在获取登录按钮句柄...")
        login_button_elements = await page.xpath(login_button_xpath)
        if not login_button_elements:
            raise Exception("无法通过 XPath 找到登录按钮句柄")
        
        login_button = login_button_elements[0]

        print("模拟鼠标悬停在按钮上...")
        await login_button.hover()
        await delay_time(500) 

        print("点击登录按钮...")
        await login_button.click()
        
        print("等待导航...")
        await page.waitForNavigation({'timeout': 30000})

        # --- 新增: 登录后硬等待5秒，让页面(包括iframe)开始加载 ---
        print("登录跳转完成，等待 5 秒让页面资源加载...")
        await delay_time(5000)
        # --- 结束新增 ---

        is_logged_in = await page.evaluate('''() => {
            const logoutButton = document.querySelector('a[href="/logout/"]');
            return logoutButton !== null;
        }''')

        if not is_logged_in:
            print("登录失败，未找到登出按钮。")
            return (False, None)

        # --- 关键修改: 移除所有详情提取代码 ---
        print("登录成功！")
        return (True, None) # 登录成功，不提取详情

    except Exception as e:
        print(f"{serviceName}账号 {username} 登录时出现错误: {e}")
        any_login_failed = True # 标记失败
        
        try:
            print("捕获到异常，等待5秒后截图...")
            await delay_time(5000) # 等待5秒
            
            page_content = await page.content()
            print("--- 页面HTML内容 (前500字符) ---")
            print(page_content[:500])
            print("---------------------------------")

            print(f"正在截取错误页面: {error_screenshot_path}")
            await page.screenshot({'path': error_screenshot_path})
            print(f"已截取错误页面: {error_screenshot_path}")
        except Exception as se:
            print(f"截图时发生额外错误: {se}")
            
        return (False, None) 

    finally:
        if page:
            await page.close()
            print("页面已关闭。")

async def shutdown_browser():
    global browser
    if browser:
        print("正在关闭浏览器实例...")
        await browser.close()
        browser = None
        print("浏览器实例已关闭。")

async def main():
    global message
    global any_login_failed

    message = "" # 重置消息

    try:
        async with aiofiles.open('accounts.json', mode='r', encoding='utf-8') as f:
            accounts_json = await f.read()
        accounts = json.loads(accounts_json)
    except Exception as e:
        print(f'读取 accounts.json 文件时出错: {e}')
        message += f"❌读取 accounts.json 文件时出错: {e}\n\n"
        any_login_failed = True
        accounts = [] 

    if not accounts:
        print("未找到任何账户信息。")
        message += "❌未在 accounts.json 中找到任何账户。\n\n"
        any_login_failed = True

    for account in accounts:
        username = account.get('username')
        password = account.get('password')
        panel = account.get('panel')

        if not all([username, password, panel]):
            print("账户信息不完整，跳过此账户。")
            message += "❌发现一个账户信息不完整，已跳过。\n\n"
            any_login_failed = True
            continue

        serviceName = 'ct8' if 'ct8' in panel else 'serv00'
        login_success, extracted_data = await login(username, password, panel)

        now_beijing = format_to_iso(datetime.utcnow() + timedelta(hours=8))
        
        # --- 关键修改: 简化成功消息 ---
        if login_success:
            message += f"✅*{serviceName}*账号 *{username}* 于北京时间 {now_beijing}登录面板成功！\n\n"
            print(f"{serviceName}账号 {username} 于北京时间 {now_beijing}登录面板成功！")
        else:
            message += f"❌*{serviceName}*账号 *{username}* 登录失败，请检查账号和密码是否正确。\n\n"
        
        delay = random.randint(3000, 10000)
        print(f"随机延迟 {delay} 毫秒...")
        await delay_time(delay)
        
    print("所有账号登录尝试完成！")
    message += f"🔚脚本结束。"
    
    try:
        await send_telegram_message(message)
        print("成功发送消息到Telegram。")
    except Exception as e:
        print(f"发送Telegram消息时出错: {e}")
        
    await shutdown_browser()
    
    if any_login_failed:
        print("检测到登录失败，脚本将以退出代码 1 退出，以触发 GitHub Actions 失败。")
        sys.exit(1) 
    else:
        print("所有登录均成功。")
        sys.exit(0) 

async def send_telegram_message(message_content):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("错误：未设置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 环境变量。")
        return

    formatted_message = f"""
*🎯 serv00&ct8自动化保号脚本运行报告*

*北京时间*: {format_to_iso(datetime.utcnow() + timedelta(hours=8))}

*UTC时间*: {format_to_iso(datetime.utcnow())}

*📝 任务报告*:

{message_content}
    """

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': formatted_message,
        'parse_mode': 'Markdown',
    }
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"发送消息到Telegram失败: {response.text}")
        else:
            print("Telegram 消息已发送。")
    except Exception as e:
        print(f"发送消息到Telegram时出错: {e}")

if __name__ == '__main__':
    asyncio.run(main())
