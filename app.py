import discord
from discord.ext import commands
from playwright.async_api import async_playwright
import asyncio
import os
from dotenv import load_dotenv

# ====== โหลด ENV (.env) ======
load_dotenv()

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

        result = await search_user_info(ctx, fname, lname, phone)
        embed = create_embed_result(fname, lname, phone, result)
        await ctx.author.send(embed=embed)
        await ctx.send("`[8/8]` ✅ ส่งข้อมูลไปที่ DM เรียบร้อย!")

    except Exception as e:
        print(f"Error reached main handler: {e}")
# =========== สิ้นสุดการทำงานหลักของบอท ============= #

# =========== คำสั่ง !clear ===============#

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """ลบข้อความในช่องตามจำนวนที่ระบุ (ค่าเริ่มต้น 5)"""
    
    # ตรวจสอบว่าใช้ในช่อง "สอบถาม" เท่านั้น
    if ctx.channel.name != "สอบถาม":
        await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในช่อง #สอบถาม เท่านั้น", delete_after=10)
        # ลบข้อความคำสั่ง !clear ที่ผู้ใช้พิมพ์ผิดช่อง
        await asyncio.sleep(1)
        await ctx.message.delete()
        return

    # ลบข้อความ (จำนวนที่ต้องการ + ข้อความคำสั่ง !clear)
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ ลบไป {len(deleted) - 1} ข้อความเรียบร้อยแล้ว", delete_after=5)

@clear.error
async def clear_error(ctx, error):
    """จัดการ Error สำหรับคำสั่ง clear"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 คุณไม่มีสิทธิ์ในการลบข้อความ", delete_after=10)
        await asyncio.sleep(1)
        await ctx.message.delete()
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ โปรดระบุจำนวนเป็นตัวเลข เช่น `!clear 10`", delete_after=10)
        await asyncio.sleep(1)
        await ctx.message.delete()

# =========== สิ้นสุดคำสั่ง !Clear ==========!

# ====== ค้นหาข้อมูลลูกค้า (เวอร์ชันสมบูรณ์ รองรับเบอร์เติมเงิน) ======
async def search_user_info(ctx, fname, lname, phone):
    p = None
    browser = None
    page = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # STEP 1: Login
        await ctx.send("`[1/7]` กำลังเข้าสู่ระบบ...")
        await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4", timeout=60000)
        await page.fill('input[name="username"]', DEALER_USERNAME)
        await page.fill('input[name="password"]', DEALER_PASSWORD)
        await page.click('input[type="submit"]')
        await page.wait_for_load_state('domcontentloaded', timeout=30000)
        await ctx.send("`[2/7]` เข้าสู่ระบบสำเร็จ!")

        # STEP 2: Smart Search
        await ctx.send("`[3/7]` กำลังไปยังหน้าค้นหา...")
        await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage", timeout=60000)
        
        try:
            await page.locator('button:has-text("OK")').click(timeout=5000)
        except Exception:
            pass 

        # STEP 3: กรอกข้อมูลและค้นหา
        search_value = phone if phone else f"{fname} {lname}"
        await ctx.send(f"`[4/7]` กำลังค้นหา '{search_value}'...")
        search_box_selector = "#SearchInput"
        await page.wait_for_selector(search_box_selector, timeout=60000)
        
        await page.fill(search_box_selector, search_value)
        await page.press(search_box_selector, 'Enter')

        # STEP 4: เลือกผู้ใช้งาน
        await ctx.send(f"`[5/7]` กำลังเลือกผู้ใช้...")
        user_selector = f'div:has-text("{search_value}")'
        await page.wait_for_selector(user_selector, timeout=20000)
        await page.locator(user_selector).filter(has_text="คุณลูกค้า").first.click()

        # STEP 5: เลือกบริการที่ Active
        await ctx.send("`[6/7]` กำลังเลือกบริการที่สถานะ Active...")
        service_selector = f'div:has-text("{search_value}"):has-text("ACTIVE")'
        await page.wait_for_selector(service_selector, timeout=20000)
        await page.locator(service_selector).locator('svg.MuiSvgIcon-colorSecondary').first.click()

        # STEP 6: ดึงข้อมูล Billing (ถ้ามี)
        await ctx.send("`[7/7]` กำลังตรวจสอบข้อมูล Billing...")
        
        # กำหนดค่าเริ่มต้นไว้ ในกรณีที่ไม่เจอข้อมูล
        billing_info = "ไม่พบข้อมูล Billing Address (อาจเป็นเบอร์ประเภทเติมเงิน)"
        try:
            # พยายามรอ container ของ Billing แค่ 5 วินาที
            billing_info_container_selector = 'div.MuiGrid-container:has(p:text("Billing Name:"))'
            await page.wait_for_selector(billing_info_container_selector, timeout=5000) # ลดเวลาลง
            
            # ถ้าเจอ ก็ดึงข้อมูลออกมา
            billing_container = page.locator(billing_info_container_selector).last
            billing_info = await billing_container.inner_text()
            
        except Exception:
            # ถ้าไม่เจอ (เกิด Timeout) ก็ไม่เป็นไร ให้ข้ามไป
            # บอทจะใช้ข้อความที่กำหนดไว้ด้านบนแทน
            await ctx.send("`[!]` ไม่พบข้อมูล Billing/ที่อยู่ จึงแสดงข้อมูลเท่าที่มี")
            pass

        return billing_info

    except Exception as e:
        error_message = f"‼️ **เกิดปัญหาขึ้นระหว่างการทำงาน:**\n```\n{type(e).__name__}: {e}\n```"
        print(error_message) 
        await ctx.send(error_message)
        if page:
            screenshot_path = "error_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            await ctx.send("ภาพหน้าจอของหน้าที่เกิดปัญหาล่าสุด:", file=discord.File(screenshot_path))
        return None

    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()
        print("Playwright browser and instance closed.")

# ====== สร้าง Embed แสดงผล (เวอร์ชันแก้ไข) ======
def create_embed_result(fname, lname, phone, billing_text):
    embed = discord.Embed(title="📄 ข้อมูลลูกค้า", description="ผลการค้นหา", color=0x00b0f4)

    if fname and lname:
        embed.add_field(name="ค้นหาด้วย", value=f"{fname} {lname}", inline=False)
    if phone:
        embed.add_field(name="เบอร์โทร", value=phone, inline=False)

    if not billing_text or not billing_text.strip():
        embed.add_field(name="ผลลัพธ์", value="❌ ไม่พบข้อมูลในระบบ", inline=False)
        return embed

    found_specific_fields = False
    lines = billing_text.split("\n")
    for line in lines:
        if "เลขประจำตัว" in line:
            embed.add_field(name="เลขประจำตัว", value=line.strip(), inline=False)
            found_specific_fields = True
        elif "ที่อยู่" in line:
            embed.add_field(name="ที่อยู่", value=line.strip(), inline=False)
            found_specific_fields = True
            
    if not found_specific_fields:
        embed.add_field(name="ข้อมูลที่พบ", value=f"```\n{billing_text}\n```", inline=False)

    return embed

# ====== เริ่มทำงาน ======
if not DISCORD_TOKEN:
    print("❌ ไม่พบ DISCORD_TOKEN")
else:
    print("📡 กำลังเริ่มบอท...")
    bot.run(DISCORD_TOKEN)
