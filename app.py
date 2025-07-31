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
    print("\n--- [LOG] ได้รับคำสั่ง !true ---")
    
    # ================================================================
    # เราจะปิดการตรวจสอบช่องนี้ไปก่อนเพื่อทดสอบ
    # allowed_channel_names = ["สอบถาม"]
    #
    # if ctx.channel.name not in allowed_channel_names:
    #     print(f"[LOG] ใช้คำสั่งในช่องที่ผิด: {ctx.channel.name}")
    #     await ctx.send("❌ ไม่สามารถใช้คำสั่งได้\nคำสั่งนี้สามารถใช้ได้เฉพาะในห้องที่กำหนดเท่านั้น")
    #     return
    # ================================================================

    await ctx.send("🔍 กำลังค้นหาข้อมูล กรุณารอสักครู่...")
    embed_loading = discord.Embed(
        title="🔄 กำลังประมวลผล",
        description="1. ✓ รับคำสั่งค้นหา\n2. » กำลังเรียกข้อมูล...\n3. รอการตอบกลับ...",
        color=0xf1c40f
    )
    await ctx.send(embed=embed_loading)

    try:
        if len(args) == 1:
            phone = args[0]
            fname, lname = "", ""
            print(f"[LOG] ค้นหาด้วยเบอร์โทร: {phone}")
        elif len(args) == 2:
            fname, lname = args
            phone = ""
            print(f"[LOG] ค้นหาด้วยชื่อ: {fname} {lname}")
        else:
            print("[LOG] รูปแบบคำสั่งไม่ถูกต้อง")
            await ctx.send("❌ รูปแบบคำสั่งไม่ถูกต้อง\nพิมพ์แค่: `!true <เบอร์โทร>` หรือ `!true <ชื่อ> <นามสกุล>`")
            return

        result = await search_user_info(fname, lname, phone)
        
        print("[LOG] ค้นหาเสร็จสิ้น กำลังสร้างผลลัพธ์")
        embed = create_embed_result(fname, lname, phone, result)

        embed_done = discord.Embed(
            title="✅ ดำเนินการเสร็จสิ้น",
            description="1. ✓ รับคำสั่งค้นหา\n2. ✓ ค้นหาข้อมูลสำเร็จ\n3. ✓ ส่งข้อมูลทาง DM แล้ว",
            color=0x2ecc71
        )
        await ctx.send(embed=embed_done)

        await ctx.author.send(embed=embed)
        print("[LOG] ส่งผลลัพธ์ไปที่ DM ของผู้ใช้แล้ว")

    except Exception as e:
        print(f"--- [ERROR] เกิดข้อผิดพลาดในคำสั่งหลัก: {e} ---")
        await ctx.send(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: `{e}`")


# ====== ค้นหาข้อมูลลูกค้า (เวอร์ชัน Log ภาษาไทย) ======
async def search_user_info(fname, lname, phone):
    print("[LOG] เริ่มการทำงานฟังก์ชัน search_user_info")
    async with async_playwright() as p:
        print("[LOG] เริ่มการทำงาน Playwright")
        browser = await p.chromium.launch(headless=True)
        print("[LOG] เปิดเบราว์เซอร์แล้ว")
        page = await browser.new_page()
        print("[LOG] สร้างหน้าเว็บใหม่แล้ว")

        try:
            # STEP 1: Login
            print("[LOG] ขั้นตอนที่ 1: กำลังไปที่หน้าล็อกอิน...")
            await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4", timeout=60000)
            print("[LOG] โหลดหน้าล็อกอินแล้ว กำลังกรอกข้อมูล...")
            await page.fill('input[name="username"]', DEALER_USERNAME)
            await page.fill('input[name="password"]', DEALER_PASSWORD)
            print("[LOG] กรอกข้อมูลแล้ว กำลังคลิกปุ่มล็อกอิน...")
            await page.click('input[type="submit"]')
            print("[LOG] คลิกปุ่มล็อกอินแล้ว")

            # STEP 2: Smart Search
            print("[LOG] ขั้นตอนที่ 2: กำลังไปที่หน้า SmartSearchPage...")
            await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage", timeout=60000)
            print("[LOG] โหลดหน้า SmartSearchPage แล้ว กำลังรอให้ฟอร์มค้นหาปรากฏ...")
            
            await page.wait_for_selector('input[formcontrolname="firstName"], input[formcontrolname="mobileNumber"]', timeout=60000)
            print("[LOG] ฟอร์มค้นหาปรากฏแล้ว กำลังกรอกข้อมูล...")

            if fname:
                await page.fill('input[formcontrolname="firstName"]', fname)
            if lname:
                await page.fill('input[formcontrolname="lastName"]', lname)
            if phone:
                await page.fill('input[formcontrolname="mobileNumber"]', phone)
            await page.click('button.search-btn')
            print("[LOG] คลิกปุ่มค้นหาแล้ว กำลังรอหน้าผลลัพธ์...")

            await page.wait_for_url("**/LandingPage", timeout=15000)
            print("[LOG] โหลดหน้า LandingPage แล้ว")

            # STEP 3: Asset Profile
            print("[LOG] ขั้นตอนที่ 3: กำลังไปที่หน้า AssetProfilePage...")
            await page.goto("https://crmlite-dealer.truecorp.co.th/AssetProfilePage")
            billing_info = ""
            try:
                print("[LOG] กำลังรอให้ข้อมูลโปรไฟล์ปรากฏ...")
                await page.wait_for_selector("div.asset-info", timeout=10000)
                billing_info = await page.inner_text("div.asset-info")
                print("[LOG] พบข้อมูลโปรไฟล์แล้ว")
            except Exception as e:
                print(f"[LOG] ไม่พบข้อมูลโปรไฟล์: {e}")
                billing_info = "ไม่พบข้อมูลโปรไฟล์"

            await browser.close()
            print("[LOG] ปิดเบราว์เซอร์แล้ว กำลังส่งข้อมูลกลับ")
            return billing_info

        except Exception as e:
            print(f"--- [ERROR] เกิดข้อผิดพลาดภายในฟังก์ชัน search_user_info: {e} ---")
            await browser.close()
            print("[LOG] ปิดเบราว์เซอร์เนื่องจากมีข้อผิดพลาด")
            raise e


# ====== สร้าง Embed แสดงผล ======
def create_embed_result(fname, lname, phone, billing_text):
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
