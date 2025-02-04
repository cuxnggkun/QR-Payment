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

# Thêm hằng số cho ROLE_ID
CUSTOMER_ROLE_ID = 1334194617322831935

# Thêm hằng số cho LOG_CHANNEL_ID
LOG_CHANNEL_ID = 1336368295363874909


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


@bot.tree.command(name="sendmsg", description="Gửi tin nhắn trực tiếp đến user")
@app_commands.describe(
    user="Người dùng cần gửi tin nhắn",
    message="Nội dung tin nhắn cần gửi"
)
async def send_direct_message(
    interaction: discord.Interaction,
    user: discord.Member,
    message: str
):
    try:
        await interaction.response.defer(ephemeral=True)

        try:
            # Kiểm tra và thêm role cho user
            role_added = await check_and_add_role(user, CUSTOMER_ROLE_ID)
            if not role_added:
                await interaction.followup.send(
                    "❌ Không thể thêm role cho user. Vui lòng kiểm tra lại quyền của bot.",
                    ephemeral=True
                )
                return

            dm_channel = await user.create_dm()

            # Tách chuỗi thành các dòng
            lines = message.split('\n')
            formatted_lines = []

            # Xử lý từng dòng riêng biệt
            for line in lines:
                if line.strip():  # Chỉ xử lý các dòng không trống
                    formatted_lines.append(line.strip())

            # Join các dòng thành text
            accounts_text = '\n'.join(formatted_lines)

            # Kiểm tra số lượng key thực tế
            actual_count = len(formatted_lines)
            if actual_count != len(message.strip().split('\n')):
                await interaction.followup.send(
                    f"⚠️ Cảnh báo: Số lượng key không khớp. Đã xử lý {actual_count} key.",
                    ephemeral=True
                )

            # Tạo embed để gửi cho user
            user_embed = discord.Embed(
                title="🔑 Thông tin tài khoản",
                description=f"Format: `username - password`\nSố lượng: `{len(formatted_lines)} key`\n\n" +
                f"```\n{accounts_text}\n```" if formatted_lines else "",
                color=discord.Color.blue()
            )
            user_embed.set_footer(
                text="Lưu ý: Mỗi dòng là một tài khoản và mật khẩu")

            # Gửi embed cho user
            await dm_channel.send(embed=user_embed)

            # Tạo embed để ghi log
            log_embed = discord.Embed(
                title="📝 Log Gửi Key",
                description="Chi tiết giao dịch:",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            log_embed.add_field(
                name="Người gửi",
                value=f"{interaction.user.mention} (`{interaction.user.name}`)",
                inline=True
            )
            log_embed.add_field(
                name="Người nhận",
                value=f"{user.mention} (`{user.name}`)",
                inline=True
            )
            log_embed.add_field(
                name="Số lượng key",
                value=f"`{len(formatted_lines)} key`",
                inline=True
            )
            log_embed.add_field(
                name="Danh sách key",
                value=f"```\n{accounts_text}\n```",
                inline=False
            )

            # Gửi log vào channel
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=log_embed)
            else:
                print(f"Không tìm thấy channel log với ID {LOG_CHANNEL_ID}")

            await interaction.followup.send(
                f"✅ Đã gửi tin nhắn đến {user.name} và thêm role!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Không thể gửi tin nhắn đến {user.name}. Người dùng có thể đã chặn DM.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error sending DM: {e}")
            await interaction.followup.send(
                "❌ Có lỗi xảy ra khi gửi tin nhắn.",
                ephemeral=True
            )

    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send(
            "❌ Có lỗi xảy ra. Vui lòng thử lại sau.",
            ephemeral=True
        )


@bot.event
async def on_ready():
    print(f'🤖 {bot.user} đã sẵn sàng!')

# Thêm hàm kiểm tra và thêm role


async def check_and_add_role(member: discord.Member, role_id: int):
    """
    Kiểm tra và thêm role cho member nếu chưa có
    """
    try:
        # Lấy role từ ID
        role = member.guild.get_role(role_id)
        if not role:
            print(f"Không tìm thấy role với ID {role_id}")
            return False

        # Kiểm tra xem member đã có role chưa
        if role not in member.roles:
            await member.add_roles(role)
            print(f"Đã thêm role {role.name} cho {member.name}")
            return True
        return True
    except Exception as e:
        print(f"Lỗi khi thêm role: {e}")
        return False

# Run the bot
bot.run(DISCORD_TOKEN)
