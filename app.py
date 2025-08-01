import discord
from discord.ext import commands
from playwright.async_api import async_playwright
import asyncio
import os
from dotenv import load_dotenv

# ==============================================================================
#  โหลดและกำหนดค่าเริ่มต้น (Setup and Configuration)
# ==============================================================================
load_dotenv()

# --- อ่านค่าจาก Environment Variables ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEALER_USERNAME = os.getenv("DEALER_USERNAME")
DEALER_PASSWORD = os.getenv("DEALER_PASSWORD")

# --- ตั้งค่า Discord Bot ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ==============================================================================
#  ฟังก์ชันหลักของ Discord Bot (Core Bot Commands)
# ==============================================================================
@bot.event
async def on_ready():
    """
    ฟังก์ชันที่จะทำงานเมื่อบอทออนไลน์สำเร็จ
    """
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    print("---------------------------------")


@bot.command(name="true")
async def true_command(ctx, *args):
    """
    คำสั่งหลักในการค้นหาข้อมูลลูกค้า
    รับ Input เป็นเบอร์โทร หรือ ชื่อ-นามสกุล
    """
    # --- ตรวจสอบ Input ---
    phone, fname, lname = "", "", ""
    if len(args) == 1:
        phone = args[0]
    elif len(args) == 2:
        fname, lname = args
    else:
        await ctx.send("❌ **รูปแบบคำสั่งไม่ถูกต้อง**\n> พิมพ์: `!true <เบอร์โทร>` หรือ `!true <ชื่อ> <นามสกุล>`")
        return

    # --- เรียกใช้ฟังก์ชันค้นหา ---
    result_data = await search_user_info(ctx, fname, lname, phone)

    # --- ส่งผลลัพธ์ ---
    if result_data:
        embed = create_embed_result(fname, lname, phone, result_data)
        try:
            await ctx.author.send(embed=embed)
            await ctx.send(f"`✅` ส่งข้อมูลของ `{phone or f'{fname} {lname}'}` ไปที่ DM เรียบร้อย!", delete_after=10)
        except discord.Forbidden:
            await ctx.send("❌ **ไม่สามารถส่ง DM**\n> กรุณาตรวจสอบว่าคุณได้เปิดรับข้อความจากสมาชิกเซิร์ฟเวอร์นี้หรือไม่")
    
    # ลบข้อความคำสั่งที่ผู้ใช้พิมพ์
    await asyncio.sleep(1)
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass # ไม่สามารถลบข้อความของคนอื่นได้ ไม่เป็นไร


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_command(ctx, amount: int = 5):
    """
    คำสั่งลบข้อความในช่อง
    """
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ ลบไป {len(deleted) - 1} ข้อความเรียบร้อยแล้ว", delete_after=5)


@clear_command.error
async def clear_error(ctx, error):
    """
    จัดการ Error สำหรับคำสั่ง clear
    """
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 คุณไม่มีสิทธิ์ในการลบข้อความ", delete_after=10)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ โปรดระบุจำนวนเป็นตัวเลข เช่น `!clear 10`", delete_after=10)


# ==============================================================================
#  ฟังก์ชันหลักในการค้นหาข้อมูล (Web Scraping Logic)
# ==============================================================================
async def search_user_info(ctx, fname, lname, phone):
    """
    ฟังก์ชันที่เชื่อมต่อกับ Playwright เพื่อค้นหาข้อมูลลูกค้า
    """
    p = None
    browser = None
    page = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # STEP 1: Login และตรวจสอบผลลัพธ์
        await ctx.send("`[1/7]` กำลังเข้าสู่ระบบ...", delete_after=15)
        await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4", timeout=60000)
        await page.fill('input[name="username"]', DEALER_USERNAME)
        await page.fill('input[name="password"]', DEALER_PASSWORD)
        await page.click('input[type="submit"]')
        
        try:
            await page.wait_for_url(lambda url: "/auth/" not in url, timeout=15000)
            await ctx.send("`[2/7]` เข้าสู่ระบบสำเร็จ!", delete_after=15)
        except Exception:
            await ctx.send("‼️ **Login ไม่สำเร็จ!**\n> กรุณาตรวจสอบ `DEALER_USERNAME` และ `DEALER_PASSWORD` ในไฟล์ `.env` ของคุณอีกครั้ง")
            await page.screenshot(path="login_error.png", full_page=True)
            await ctx.send(file=discord.File("login_error.png"))
            return None

        # STEP 2: ไปยังหน้าค้นหาและกรอกข้อมูล
        await ctx.send("`[3/7]` กำลังไปยังหน้าค้นหา...", delete_after=15)
        await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage", timeout=60000)
        try:
            await page.locator('button:has-text("OK")').click(timeout=5000)
        except Exception: pass
        
        search_value = phone if phone else f"{fname} {lname}"
        await ctx.send(f"`[4/7]` กำลังค้นหา '{search_value}'...", delete_after=15)
        await page.fill("#SearchInput", search_value)
        await page.press("#SearchInput", 'Enter')
        
        # STEP 3: คลิกที่การ์ดโปรไฟล์ลูกค้า
        await ctx.send(f"`[5/7]` กำลังเลือกโปรไฟล์ลูกค้า...", delete_after=15)
        customer_card_selector = f'button.MuiCardActionArea-root:has-text("{search_value}")'
        await page.wait_for_selector(customer_card_selector, timeout=20000)
        await page.locator(customer_card_selector).first.click()
        
        # STEP 4: คลิกที่บริการ TrueOnline
        await ctx.send("`[6/7]` กำลังเลือกบริการ...", delete_after=15)
        service_container_selector = 'div:has-text("TrueOnline"), div:has-text("TrueMove H")' # รองรับทั้ง 2 บริการ
        await page.wait_for_selector(service_container_selector, timeout=20000)
        await page.locator(service_container_selector).locator("button.MuiCardActionArea-root").first.click()

        # STEP 5: ดึงข้อมูล Subscriber และ Billing
        await ctx.send("`[7/7]` กำลังดึงข้อมูลโปรไฟล์...", delete_after=15)
        
        subscriber_text = "ไม่พบข้อมูล Subscriber Profile"
        try:
            subscriber_container = page.locator('div:has-text("Subscriber Profile")').last
            await subscriber_container.wait_for(timeout=5000)
            subscriber_text = await subscriber_container.inner_text()
        except Exception: pass
            
        billing_text = "ไม่พบข้อมูล Billing Profile"
        try:
            billing_container = page.locator('div:has-text("Billing Profile")').last
            await billing_container.wait_for(timeout=5000)
            billing_text = await billing_container.inner_text()
        except Exception: pass
            
        return {'subscriber': subscriber_text, 'billing': billing_text}

    except Exception as e:
        error_message = f"‼️ **เกิดปัญหาขึ้นระหว่างการทำงาน:**\n```\n{type(e).__name__}: {e}\n```"
        print(error_message) 
        if "Target closed" not in str(e):
             await ctx.send(error_message)
        if page and not page.is_closed():
            screenshot_path = "error_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            await ctx.send(file=discord.File(screenshot_path))
        return None

    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()
        print("Playwright browser and instance closed.")


# ==============================================================================
#  ฟังก์ชันเสริมและจัดรูปแบบการแสดงผล (Helpers and Formatting)
# ==============================================================================
def parse_profile_data(text: str) -> dict:
    """
    ฟังก์ชันนี้จะรับข้อความดิบจากโปรไฟล์ และแปลงเป็น Dictionary
    """
    if not text: return {}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    data = {}
    for i, line in enumerate(lines):
        if line.endswith(':') and i + 1 < len(lines):
            key = line[:-1].strip()
            value = lines[i+1].strip()
            data[key] = value
    return data


def create_embed_result(fname: str, lname: str, phone: str, result_data: dict) -> discord.Embed:
    """
    สร้าง Embed สำหรับแสดงผลข้อมูลลูกค้าอย่างสวยงาม
    """
    embed = discord.Embed(title="📄 ข้อมูลลูกค้า", description="ผลการค้นหาจากระบบ", color=0xE60000) # สีแดงทรู
    embed.set_footer(text=f"ค้นหาเมื่อ: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    search_query = phone if phone else f"{fname} {lname}"
    embed.add_field(name="ข้อมูลที่ใช้ค้นหา", value=search_query, inline=False)
    
    # --- ประมวลผลและแสดง Subscriber Profile ---
    subscriber_raw_text = result_data.get('subscriber', '')
    subscriber_data = parse_profile_data(subscriber_raw_text)
    
    sub_name = subscriber_data.get('Subscriber Name', 'N/A')
    sub_addr = subscriber_data.get('Installation Address', 'N/A')
    
    subscriber_display_text = (
        f"**ชื่อ-นามสกุล:** {sub_name}\n"
        f"**ที่อยู่ติดตั้ง:** {sub_addr}"
    )
    embed.add_field(name="👤 Subscriber Profile", value=subscriber_display_text, inline=False)
    
    # --- ประมวลผลและแสดง Billing Profile ---
    billing_raw_text = result_data.get('billing', '')
    billing_data = parse_profile_data(billing_raw_text)
    
    bill_name = billing_data.get('Billing Name', 'N/A')
    bill_addr = billing_data.get('Billing Address', 'N/A')
    tax_id = billing_data.get('Tax ID', 'N/A')

    billing_display_text = (
        f"**ชื่อ-นามสกุล:** {bill_name}\n"
        f"**ที่อยู่ใบแจ้งหนี้:** {bill_addr}\n"
        f"**เลขประจำตัวผู้เสียภาษี:** {tax_id}"
    )
    embed.add_field(name="💳 Billing Profile", value=billing_display_text, inline=False)

    return embed


# ==============================================================================
#  ส่วนเริ่มต้นการทำงานของบอท (Bot Execution)
# ==============================================================================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ไม่พบ DISCORD_TOKEN ใน .env ไฟล์")
    elif not DEALER_USERNAME or not DEALER_PASSWORD:
        print("❌ ไม่พบ DEALER_USERNAME หรือ DEALER_PASSWORD ใน .env ไฟล์")
    else:
        print("📡 กำลังเริ่มบอท...")
        bot.run(DISCORD_TOKEN)
