import discord
from discord.ext import commands
from playwright.async_api import async_playwright
import asyncio
import os

# ====== กำหนดค่าหลัก (อ่านจาก Environment Variables) ======
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEALER_USERNAME = os.getenv("DEALER_USERNAME")
DEALER_PASSWORD = os.getenv("DEALER_PASSWORD")

# ====== Discord Bot Setup ======
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== ฟังก์ชันหลักของบอท ======
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")

@bot.command()
async def true(ctx, *args):
    # ไม่มีการตรวจสอบช่อง เพื่อให้แน่ใจว่าคำสั่งทำงาน
    await ctx.send("`[1/8]` ได้รับคำสั่ง! กำลังเริ่มต้น...")
    
    try:
        if len(args) == 1:
            phone = args[0]
            fname, lname = "", ""
        elif len(args) == 2:
            fname, lname = args
            phone = ""
        else:
            await ctx.send("❌ รูปแบบคำสั่งไม่ถูกต้อง\nพิมพ์แค่: `!true <เบอร์โทร>` หรือ `!true <ชื่อ> <นามสกุล>`")
            return

        # ส่ง ctx เข้าไปในฟังก์ชันเพื่อใช้ในการส่ง Log
        result = await search_user_info(ctx, fname, lname, phone)
        
        embed = create_embed_result(fname, lname, phone, result)
        await ctx.author.send(embed=embed)
        await ctx.send("`[8/8]` ✅ ส่งข้อมูลไปที่ DM เรียบร้อย!")

    except Exception as e:
        # การดักจับ error จะเกิดขึ้นใน search_user_info เป็นหลัก
        print(f"Error reached main handler: {e}")


# ====== ค้นหาข้อมูลลูกค้า (เวอร์ชัน Live Debugging) ======
async def search_user_info(ctx, fname, lname, phone):
    page = None
    browser = None
    try:
        await ctx.send("`[2/8]` กำลังเริ่มต้น Playwright...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # STEP 1: Login
            await ctx.send("`[3/8]` กำลังไปที่หน้าล็อกอิน...")
            await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4", timeout=60000)
            await ctx.send("`[4/8]` กำลังกรอกข้อมูลล็อกอิน...")
            await page.fill('input[name="username"]', DEALER_USERNAME)
            await page.fill('input[name="password"]', DEALER_PASSWORD)
            await page.click('input[type="submit"]')
            await ctx.send("`[5/8]` ล็อกอินสำเร็จ! กำลังไปที่หน้าค้นหา...")

            # STEP 2: Smart Search
            await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage", timeout=60000)
            await ctx.send("`[6/8]` อยู่ที่หน้าค้นหาแล้ว กำลังรอฟอร์ม...")
            
            await page.wait_for_selector('input[formcontrolname="firstName"], input[formcontrolname="mobileNumber"]', timeout=60000)
            await ctx.send("`[7/8]` พบฟอร์มแล้ว! กำลังค้นหาข้อมูล...")

            if fname:
                await page.fill('input[formcontrolname="firstName"]', fname)
            if lname:
                await page.fill('input[formcontrolname="lastName"]', lname)
            if phone:
                await page.fill('input[formcontrolname="mobileNumber"]', phone)
            await page.click('button.search-btn')

            await page.wait_for_url("**/LandingPage", timeout=15000)
            await page.goto("https://crmlite-dealer.truecorp.co.th/AssetProfilePage")
            
            billing_info = await page.inner_text("div.asset-info")
            await browser.close()
            return billing_info

    except Exception as e:
        await ctx.send(f"‼️ **เกิดปัญหาที่ขั้นตอนล่าสุด:**\n```\n{e}\n```")
        if page:
            screenshot_path = "error_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            await ctx.send("ภาพหน้าจอของหน้าที่เกิดปัญหา:", file=discord.File(screenshot_path))
        if browser:
            await browser.close()
        raise e

# ====== สร้าง Embed แสดงผล ======
def create_embed_result(fname, lname, phone, billing_text):
    # ... (ส่วนนี้เหมือนเดิม) ...
    embed = discord.Embed(title="📄 ข้อมูลลูกค้า", description="ผลการค้นหา", color=0x00b0f4)
    if fname and lname:
        embed.add_field(name="ค้นหาด้วย", value=f"{fname} {lname}", inline=False)
    if phone:
        embed.add_field(name="เบอร์โทร", value=phone, inline=False)
    if not billing_text.strip() or "ไม่พบข้อมูล" in billing_text:
        embed.add_field(name="ผลลัพธ์", value="❌ ไม่พบข้อมูลในระบบ", inline=False)
    else:
        embed.add_field(name="ข้อมูลที่พบ", value=billing_text, inline=False)
    return embed

# ====== เริ่มทำงาน ======
bot.run(DISCORD_TOKEN)
