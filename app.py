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
    # --- ตรวจสอบ Input ---
    phone, fname, lname = "", "", ""
    if len(args) == 1:
        phone = args[0]
    elif len(args) == 2:
        fname, lname = args
    else:
        await ctx.send("❌ รูปแบบคำสั่งไม่ถูกต้อง\nพิมพ์แค่: `!true <เบอร์โทร>` หรือ `!true <ชื่อ> <นามสกุล>`")
        return

    # --- เรียกใช้ฟังก์ชันค้นหา ---
    result_data = await search_user_info(ctx, fname, lname, phone)

    # --- ส่งผลลัพธ์ ---
    if result_data: 
        embed = create_embed_result(fname, lname, phone, result_data)
        try:
            await ctx.author.send(embed=embed)
            await ctx.send("`[8/8]` ✅ ส่งข้อมูลไปที่ DM เรียบร้อย!")
        except discord.Forbidden:
            await ctx.send("❌ ไม่สามารถส่ง DM หากรุณาตรวจสอบว่าคุณได้เปิดรับข้อความจากสมาชิกเซิร์ฟเวอร์นี้หรือไม่")

# =========== คำสั่ง !clear (คงเดิม) ===============#
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """ลบข้อความในช่องตามจำนวนที่ระบุ (ค่าเริ่มต้น 5)"""
    if ctx.channel.name != "สอบถาม":
        await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในช่อง #สอบถาม เท่านั้น", delete_after=10)
        await asyncio.sleep(1)
        await ctx.message.delete()
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ ลบไป {len(deleted) - 1} ข้อความเรียบร้อยแล้ว", delete_after=5)

@clear.error
async def clear_error(ctx, error):
    """จัดการ Error สำหรับคำสั่ง clear"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 คุณไม่มีสิทธิ์ในการลบข้อความ", delete_after=10)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ โปรดระบุจำนวนเป็นตัวเลข เช่น `!clear 10`", delete_after=10)
    
    await asyncio.sleep(1)
    await ctx.message.delete()


# ====== [แก้ไข] ค้นหาข้อมูลลูกค้า (ปรับปรุง Logic การคลิก) ======
async def search_user_info(ctx, fname, lname, phone):
    p = None
    browser = None
    page = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # STEP 1: Login และตรวจสอบผลลัพธ์
        await ctx.send("`[1/7]` กำลังเข้าสู่ระบบ...")
        await page.goto("https://wzzo.truecorp.co.th/auth/realms/Dealer-Internet/protocol/openid-connect/auth?client_id=crmlite-prod-dealer&response_type=code&scope=openid%20profile&redirect_uri=https://crmlite-dealer.truecorp.co.th/&state=xyz&nonce=abc&response_mode=query&code_challenge_method=S256&code_challenge=AzRSFK3CdlHMiDq1DsuRGEY-p6EzTxexaIRyLphE9o4", timeout=60000)
        await page.fill('input[name="username"]', DEALER_USERNAME)
        await page.fill('input[name="password"]', DEALER_PASSWORD)
        await page.click('input[type="submit"]')
        
        try:
            await page.wait_for_url(lambda url: "/auth/" not in url, timeout=15000)
            await ctx.send("`[2/7]` เข้าสู่ระบบสำเร็จ!")
        except Exception:
            await ctx.send("‼️ **Login ไม่สำเร็จ!**\nกรุณาตรวจสอบ `DEALER_USERNAME` และ `DEALER_PASSWORD` ในไฟล์ `.env` ของคุณอีกครั้ง")
            await page.screenshot(path="login_error.png", full_page=True)
            await ctx.send("ภาพหน้าจอของหน้าที่เกิดปัญหา:", file=discord.File("login_error.png"))
            return None

        # STEP 2: ไปยังหน้าค้นหาและกรอกข้อมูล
        await ctx.send("`[3/7]` กำลังไปยังหน้าค้นหา...")
        await page.goto("https://crmlite-dealer.truecorp.co.th/SmartSearchPage", timeout=60000)
        try:
            await page.locator('button:has-text("OK")').click(timeout=5000)
        except Exception: pass
        
        search_value = phone if phone else f"{fname} {lname}"
        await ctx.send(f"`[4/7]` กำลังค้นหา '{search_value}'...")
        await page.fill("#SearchInput", search_value)
        await page.press("#SearchInput", 'Enter')
        
        # STEP 3: [ใหม่] คลิกที่การ์ดโปรไฟล์ลูกค้า
        await ctx.send(f"`[5/7]` กำลังเลือกโปรไฟล์ลูกค้า...")
        # มองหาปุ่ม MuiCardActionArea-root ที่มีชื่อลูกค้าอยู่ข้างใน
        customer_card_selector = f'button.MuiCardActionArea-root:has-text("{search_value}")'
        await page.wait_for_selector(customer_card_selector, timeout=20000)
        await page.locator(customer_card_selector).first.click()
        
        # STEP 4: [ใหม่] คลิกที่บริการ TrueOnline
        await ctx.send("`[6/7]` กำลังเลือกบริการ TrueOnline...")
        # มองหา div ที่มีคำว่า TrueOnline จากนั้นหาปุ่มลูกศรที่อยู่ใน div นั้น
        service_container_selector = 'div:has-text("TrueOnline")'
        await page.wait_for_selector(service_container_selector, timeout=20000)
        await page.locator(service_container_selector).locator("button.MuiCardActionArea-root").first.click()

        # STEP 5: ดึงข้อมูล Subscriber และ Billing
        await ctx.send("`[7/7]` กำลังดึงข้อมูลโปรไฟล์...")
        
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
            await ctx.send("ภาพหน้าจอของหน้าที่เกิดปัญหาล่าสุด:", file=discord.File(screenshot_path))
        return None

    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()
        print("Playwright browser and instance closed.")

# ====== สร้าง Embed แสดงผล (คงเดิม) ======
def create_embed_result(fname, lname, phone, result_data: dict):
    embed = discord.Embed(title="📄 ข้อมูลลูกค้า", description="ผลการค้นหาจากระบบ", color=0x00b0f4)
    embed.set_footer(text=f"ค้นหาเมื่อ: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    search_query = phone if phone else f"{fname} {lname}"
    embed.add_field(name="ข้อมูลที่ใช้ค้นหา", value=search_query, inline=False)
    
    subscriber_info = result_data.get('subscriber', 'ไม่พบข้อมูล')
    subscriber_info = subscriber_info.replace("Subscriber Profile", "").strip()
    embed.add_field(name="👤 Subscriber Profile", value=f"```\n{subscriber_info}\n```", inline=False)
    
    billing_info = result_data.get('billing', 'ไม่พบข้อมูล')
    billing_info = billing_info.replace("Billing Profile", "").strip()
    embed.add_field(name="💳 Billing Profile", value=f"```\n{billing_info}\n```", inline=False)

    return embed

# ====== เริ่มทำงาน ======
if not DISCORD_TOKEN:
    print("❌ ไม่พบ DISCORD_TOKEN ใน .env ไฟล์")
elif not DEALER_USERNAME or not DEALER_PASSWORD:
    print("❌ ไม่พบ DEALER_USERNAME หรือ DEALER_PASSWORD ใน .env ไฟล์")
else:
    print("📡 กำลังเริ่มบอท...")
    bot.run(DISCORD_TOKEN)
