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

# ====== ค้นหาข้อมูลลูกค้า (เวอร์ชันสุดท้าย) ======
async def search_user_info(ctx, fname, lname, phone):
    page = None
    browser = None
    try:
        # async with async_playwright() as p: # Comment this line out if playwright is managed outside
        p = await async_playwright().start() # Use this line if playwright is managed outside
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
            
        # STEP 1: Login
        await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4", timeout=60000)
        await page.fill('input[name="username"]', DEALER_USERNAME)
        await page.fill('input[name="password"]', DEALER_PASSWORD)
        await page.click('input[type="submit"]')

        # STEP 2: Smart Search
        await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage", timeout=60000)
            
        # จัดการ Pop-up (ถ้ามี)
        try:
            await page.locator('button:has-text("OK")').click(timeout=5000)
        except Exception:
            pass # ถ้าไม่เจอ Pop-up ก็ไม่เป็นไร

        # รอ, กรอกข้อมูล, และกด Enter
        search_box_selector = "#SearchInput"
        await page.wait_for_selector(search_box_selector, timeout=60000)
            
        search_value = phone if phone else f"{fname} {lname}"
        await page.fill(search_box_selector, search_value)
        
        # --- [การแก้ไข] ---
        # กด Enter แทนการคลิกปุ่ม
        await page.press(search_box_selector, 'Enter')
        
        # รอผลลัพธ์และดึงข้อมูล
        await page.wait_for_url("**/LandingPage", timeout=30000)
        await page.goto("https://crmlite-dealer.truecorp.co.th/AssetProfilePage")
            
        await page.wait_for_selector("div.asset-info", timeout=10000) # เพิ่มการรอข้อมูล
        billing_info = await page.inner_text("div.asset-info")
        await browser.close()
        await p.stop() # Use this line if playwright is managed outside
        return billing_info

    except Exception as e:
        await ctx.send(f"‼️ **เกิดปัญหาขึ้น:**\n```\n{e}\n```")
        if page:
            await page.screenshot(path="final_error.png", full_page=True)
            await ctx.send("ภาพหน้าจอของหน้าที่เกิดปัญหาล่าสุด:", file=discord.File("final_error.png"))
        if browser:
            await browser.close()
        # await p.stop() # Use this line if playwright is managed outside
        raise e

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
