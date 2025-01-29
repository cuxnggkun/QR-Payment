import discord
from discord import app_commands
import os
from dotenv import load_dotenv
from urllib.parse import quote

# Load environment variables
load_dotenv()

# Configuration from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BANK_ID = os.getenv('BANK_ID', '970436')
ACCOUNT_NO = os.getenv('ACCOUNT_NO')
ACCOUNT_NAME = os.getenv('ACCOUNT_NAME')

def generate_vietqr_content(amount: float, message: str = ""):
    """
    Generate VietQR content with proper URL encoding
    """
    # Ensure all components are properly encoded
    encoded_account_name = quote(ACCOUNT_NAME)
    encoded_message = quote(message)
    
    # Format according to VietQR standard
    qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact.png"
    qr_url += f"?amount={int(amount)}"
    if message:
        qr_url += f"&addInfo={encoded_message}"
    qr_url += f"&accountName={encoded_account_name}"
    
    print(f"Generated QR URL: {qr_url}")  # For debugging
    return qr_url

class QRPaymentBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        try:
            print("Synchronizing commands...")
            await self.tree.sync()
            print("Command synchronization successful!")
        except Exception as e:
            print(f"Error synchronizing commands: {e}")

bot = QRPaymentBot()

@bot.tree.command(name="thanhtoan", description="Tạo mã QR thanh toán ngân hàng")
@app_commands.describe(
    amount="Số lượng key cần thanh toán",
)
async def generate_qr(
    interaction: discord.Interaction,
    amount: int,
):
    try:
        # Validate key amount
        if amount < 5:
            await interaction.response.send_message("❌ Số lượng key phải lớn hơn hoặc bằng 5!")
            return

        # Calculate price based on quantity
        total_price = 250000 * amount if amount >= 10 else 275000 * amount

        await interaction.response.defer()

        # Generate VietQR URL with encoded parameters
        message = f"{interaction.user.name}"
        qr_url = generate_vietqr_content(total_price, message)

        # Create embed with payment information
        embed = discord.Embed(
            title="💳 Thông tin thanh toán",
            description=f"**Số lượng key:** {amount} key\n**Đơn giá:** {250000 if amount >= 10 else 275000:,} VNĐ/key",
            color=0x00ff00  # Màu xanh lá cây tươi sáng
        )

        # Thông tin ngân hàng
        embed.add_field(
            name="🏦 Thông tin tài khoản",
            value=f"```\nNgân hàng: BIDV\nChủ TK: {ACCOUNT_NAME}\nSố TK: {ACCOUNT_NO}\n```",
            inline=False
        )

        # Thông tin thanh toán
        embed.add_field(
            name="💰 Chi tiết thanh toán",
            value=f"```\nTổng tiền: {total_price:,} VNĐ\nNội dung CK: {message}\n```",
            inline=False
        )
        
        # Set the encoded QR URL
        try:
            embed.set_image(url=qr_url)
        except Exception as e:
            print(f"Error setting image URL: {e}")
            await interaction.followup.send("❌ Không thể tạo mã QR. Vui lòng thử lại sau.")
            return

        embed.set_footer(text=f"Yêu cầu bởi: {interaction.user.name}")

        await interaction.followup.send(embed=embed)

    except ValueError:
        await interaction.followup.send('❌ Vui lòng nhập một số hợp lệ.')
    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send('❌ Có lỗi xảy ra. Vui lòng thử lại sau.')

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} đã sẵn sàng!')

# Run the bot
bot.run(DISCORD_TOKEN)