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
    allowed_channel_names = ["สอบถาม"]  # <- ชื่อห้องที่อนุญาตให้ใช้คำสั่ง

    if ctx.channel.name not in allowed_channel_names:
        await ctx.send("❌ ไม่สามารถใช้คำสั่งได้\nคำสั่งนี้สามารถใช้ได้เฉพาะในห้องที่กำหนดเท่านั้น")
        return

    await ctx.send("🔍 กำลังค้นหาข้อมูล กรุณารอสักครู่...")

    embed_loading = discord.Embed(
        title="🔄 กำลังประมวลผล",
        description="1. ✓ รับคำสั่งค้นหา\n2. » กำลังเรียกข้อมูลจาก API...\n3. รอการตอบกลับ...",
        color=0xf1c40f
    )
    await ctx.send(embed=embed_loading)

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

        result = await search_user_info(fname, lname, phone)
        embed = create_embed_result(fname, lname, phone, result)

        embed_done = discord.Embed(
            title="✅ ดำเนินการเสร็จสิ้น",
            description="1. ✓ รับคำสั่งค้นหา\n2. ✓ ค้นหาข้อมูลสำเร็จ\n3. ✓ ส่งข้อมูลทาง DM แล้ว",
            color=0x2ecc71
        )
        await ctx.send(embed=embed_done)

        await ctx.author.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {str(e)}")

# ====== ค้นหาข้อมูลลูกค้า ======
async def search_user_info(fname, lname, phone):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # STEP 1: Login
        await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4")
        await page.fill('input[name="username"]', DEALER_USERNAME)
        await page.fill('input[name="password"]', DEALER_PASSWORD)
        await page.click('input[type="submit"]')

        # STEP 2: Smart Search
        await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage")
        print("--- DEBUG: Page Content ---")
        print(await page.content())
        print("--- END DEBUG ---")
        if fname:
            await page.fill('input[formcontrolname="firstName"]', fname)
        if lname:
            await page.fill('input[formcontrolname="lastName"]', lname)
        if phone:
            await page.fill('input[formcontrolname="mobileNumber"]', phone)
        await page.click('button.search-btn')

        await page.wait_for_url("**/LandingPage", timeout=15000)

        # STEP 3: Asset Profile
        await page.goto("https://crmlite-dealer.truecorp.co.th/AssetProfilePage")
        try:
            await page.wait_for_selector("div.asset-info", timeout=10000)
            billing_info = await page.inner_text("div.asset-info")
        except:
            billing_info = ""  # ไม่พบข้อมูล

        await browser.close()
        return billing_info

# ====== สร้าง Embed แสดงผล ======
def create_embed_result(fname, lname, phone, billing_text):
    embed = discord.Embed(
        title="📄 ข้อมูลลูกค้า",
        description="ผลการค้นหา",
        color=0x00b0f4
    )

    if fname and lname:
        embed.add_field(name="ค้นหาด้วย", value=f"{fname} {lname}", inline=False)
    if phone:
        embed.add_field(name="เบอร์โทร", value=phone, inline=False)

    if not billing_text.strip():
        embed.add_field(name="ผลลัพธ์", value="❌ ไม่พบข้อมูลในระบบ", inline=False)
        return embed

    lines = billing_text.split("\n")
    for line in lines:
        if "เลขประจำตัว" in line:
            embed.add_field(name="เลขประจำตัว", value=line.strip(), inline=False)
        elif "ที่อยู่" in line:
            embed.add_field(name="ที่อยู่", value=line.strip(), inline=False)

    return embed

# ====== เริ่มทำงาน ======
bot.run(DISCORD_TOKEN)
