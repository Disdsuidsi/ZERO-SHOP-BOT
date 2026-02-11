import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select
import json
import os
from datetime import datetime

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 데이터 파일
INVENTORY_FILE = 'inventory_data.json'
ADMIN_ROLE = "관리자"  # 관리자 역할 이름

# 재고 데이터 로드
def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 재고 데이터 저장
def save_inventory(data):
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 관리자 체크
def is_admin(user):
    if user.guild_permissions.administrator:
        return True
    for role in user.roles:
        if role.name == ADMIN_ROLE:
            return True
    return False

# 메인 메뉴 View
class MainMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📦 재고 확인", style=discord.ButtonStyle.primary, custom_id="check_inventory")
    async def check_inventory_button(self, interaction: discord.Interaction, button: Button):
        inventory = load_inventory()
        
        if not inventory:
            await interaction.response.send_message("📦 현재 등록된 재고가 없습니다.", ephemeral=True)
            return
        
        # 카테고리 선택 뷰 생성
        view = CategorySelectView()
        
        embed = discord.Embed(
            title="🏪 ZERO SHOP",
            description="원하시는 카테고리를 선택해주세요!",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        categories = list(inventory.keys())
        for i, category in enumerate(categories, 1):
            item_count = len(inventory[category])
            embed.add_field(
                name=f"{i}. {category}",
                value=f"총 {item_count}개 상품",
                inline=True
            )
        
        embed.set_footer(text="재고 관리 시스템")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# 카테고리 선택 View
class CategorySelectView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_category_buttons()
    
    def add_category_buttons(self):
        inventory = load_inventory()
        categories = list(inventory.keys())
        
        for category in categories[:25]:  # 디스코드 버튼 제한 25개
            button = Button(
                label=category,
                style=discord.ButtonStyle.secondary,
                custom_id=f"category_{category}"
            )
            button.callback = self.create_category_callback(category)
            self.add_item(button)
    
    def create_category_callback(self, category):
        async def callback(interaction: discord.Interaction):
            inventory = load_inventory()
            items = inventory.get(category, {})
            
            if not items:
                await interaction.response.send_message(f"❌ '{category}' 카테고리에 상품이 없습니다.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📦 {category}",
                description="원하시는 상품을 선택해주세요!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            for item_id, item in items.items():
                stock_status = "✅ 재고 있음" if item['quantity'] > 0 else "❌ 품절"
                if item['quantity'] <= item.get('minStock', 5) and item['quantity'] > 0:
                    stock_status = "⚠️ 재고 부족"
                
                embed.add_field(
                    name=f"{item['name']}",
                    value=f"💰 가격: {item['price']:,}원\n📦 재고: {item['quantity']}개\n{stock_status}",
                    inline=True
                )
            
            embed.set_footer(text="ZERO SHOP - 재고 관리 시스템")
            
            # 아이템 선택 뷰
            view = ItemSelectView(category, items)
            await interaction.response.edit_message(embed=embed, view=view)
        
        return callback

# 아이템 선택 View
class ItemSelectView(View):
    def __init__(self, category, items):
        super().__init__(timeout=180)
        self.category = category
        self.items = items
        self.add_item_select()
        
        # 뒤로가기 버튼
        back_button = Button(label="⬅️ 뒤로가기", style=discord.ButtonStyle.danger)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def add_item_select(self):
        options = []
        for item_id, item in list(self.items.items())[:25]:  # 최대 25개
            options.append(
                discord.SelectOption(
                    label=item['name'],
                    description=f"{item['price']:,}원 | 재고: {item['quantity']}개",
                    value=item_id,
                    emoji="🛒"
                )
            )
        
        if options:
            select = Select(
                placeholder="상품을 선택하세요...",
                options=options,
                custom_id="item_select"
            )
            select.callback = self.item_callback
            self.add_item(select)
    
    async def item_callback(self, interaction: discord.Interaction):
        item_id = interaction.data['values'][0]
        item = self.items[item_id]
        
        embed = discord.Embed(
            title=f"🛒 {item['name']}",
            description=item.get('description', '상품 정보'),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="💰 가격", value=f"{item['price']:,}원", inline=True)
        embed.add_field(name="📦 재고", value=f"{item['quantity']}개", inline=True)
        embed.add_field(name="📁 카테고리", value=self.category, inline=True)
        
        if item['quantity'] > 0:
            embed.add_field(
                name="✅ 구매 가능",
                value="관리자에게 문의해주세요!",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ 품절",
                value="재고가 모두 소진되었습니다.",
                inline=False
            )
        
        embed.set_footer(text="ZERO SHOP - 재고 관리 시스템")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def back_callback(self, interaction: discord.Interaction):
        view = CategorySelectView()
        
        embed = discord.Embed(
            title="🏪 ZERO SHOP",
            description="원하시는 카테고리를 선택해주세요!",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        inventory = load_inventory()
        categories = list(inventory.keys())
        for i, category in enumerate(categories, 1):
            item_count = len(inventory[category])
            embed.add_field(
                name=f"{i}. {category}",
                value=f"총 {item_count}개 상품",
                inline=True
            )
        
        embed.set_footer(text="재고 관리 시스템")
        
        await interaction.response.edit_message(embed=embed, view=view)

# 봇 시작
@bot.event
async def on_ready():
    print(f'{bot.user} 봇이 준비되었습니다!')
    
    # Persistent View 등록
    bot.add_view(MainMenuView())
    
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'명령어 동기화 오류: {e}')

# 자판기 메뉴 생성 (관리자만)
@bot.tree.command(name="자판기설치", description="[관리자] 재고 확인 자판기를 설치합니다")
async def setup_vending_machine(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏪 ZERO SHOP",
        description="**재고 관리 시스템에 오신 것을 환영합니다!**\n\n아래 버튼을 눌러 원하는 서비스를 이용하세요.",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📦 재고 확인",
        value="현재 판매 중인 상품과 재고를 확인할 수 있습니다.",
        inline=False
    )
    
    embed.set_footer(text="ZERO SHOP - 재고 관리 시스템")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3081/3081559.png")
    
    view = MainMenuView()
    
    await interaction.response.send_message(embed=embed, view=view)

# 재고 추가 (관리자만)
@bot.tree.command(name="재고추가", description="[관리자] 새 재고를 추가합니다")
async def add_inventory(
    interaction: discord.Interaction,
    카테고리: str,
    아이템명: str,
    수량: int,
    가격: int,
    설명: str = ""
):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    inventory = load_inventory()
    
    if 카테고리 not in inventory:
        inventory[카테고리] = {}
    
    item_id = str(len(inventory[카테고리]) + 1)
    inventory[카테고리][item_id] = {
        "name": 아이템명,
        "quantity": 수량,
        "price": 가격,
        "description": 설명,
        "minStock": 5,
        "addedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    save_inventory(inventory)
    
    # 공개 알림
    embed = discord.Embed(
        title="✅ 재고 추가 완료!",
        description=f"새로운 상품이 등록되었습니다!",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="카테고리", value=카테고리, inline=True)
    embed.add_field(name="아이템", value=아이템명, inline=True)
    embed.add_field(name="수량", value=f"{수량}개", inline=True)
    embed.add_field(name="가격", value=f"{가격:,}원", inline=True)
    
    await interaction.response.send_message(embed=embed)

# 재고 수정 (관리자만)
@bot.tree.command(name="재고수정", description="[관리자] 재고 수량을 수정합니다")
async def update_inventory(
    interaction: discord.Interaction,
    카테고리: str,
    아이템명: str,
    수량변경: int
):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    inventory = load_inventory()
    
    if 카테고리 not in inventory:
        await interaction.response.send_message(f"❌ '{카테고리}' 카테고리를 찾을 수 없습니다.", ephemeral=True)
        return
    
    # 아이템 찾기
    found = False
    for item_id, item in inventory[카테고리].items():
        if item['name'] == 아이템명:
            old_quantity = item['quantity']
            item['quantity'] += 수량변경
            
            if item['quantity'] < 0:
                await interaction.response.send_message("❌ 재고가 음수가 될 수 없습니다.", ephemeral=True)
                return
            
            save_inventory(inventory)
            
            # 공개 알림
            embed = discord.Embed(
                title="📦 재고 충전 완료!",
                description=f"재고가 업데이트되었습니다!",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="아이템", value=아이템명, inline=True)
            embed.add_field(name="이전 수량", value=f"{old_quantity}개", inline=True)
            embed.add_field(name="현재 수량", value=f"{item['quantity']}개", inline=True)
            
            await interaction.response.send_message(embed=embed)
            found = True
            break
    
    if not found:
        await interaction.response.send_message(f"❌ '{아이템명}' 아이템을 찾을 수 없습니다.", ephemeral=True)

# 재고 삭제 (관리자만)
@bot.tree.command(name="재고삭제", description="[관리자] 재고를 삭제합니다")
async def delete_inventory(interaction: discord.Interaction, 카테고리: str, 아이템명: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    inventory = load_inventory()
    
    if 카테고리 not in inventory:
        await interaction.response.send_message(f"❌ '{카테고리}' 카테고리를 찾을 수 없습니다.", ephemeral=True)
        return
    
    # 아이템 찾기 및 삭제
    found = False
    for item_id, item in list(inventory[카테고리].items()):
        if item['name'] == 아이템명:
            del inventory[카테고리][item_id]
            
            # 카테고리가 비었으면 삭제
            if not inventory[카테고리]:
                del inventory[카테고리]
            
            save_inventory(inventory)
            
            await interaction.response.send_message(f"✅ '{아이템명}' 재고가 삭제되었습니다.")
            found = True
            break
    
    if not found:
        await interaction.response.send_message(f"❌ '{아이템명}' 아이템을 찾을 수 없습니다.", ephemeral=True)

# 재고 부족 알림
@bot.tree.command(name="재고부족", description="재고가 부족한 아이템을 확인합니다")
async def low_stock(interaction: discord.Interaction):
    inventory = load_inventory()
    low_items = []
    
    for category, items in inventory.items():
        for item_id, item in items.items():
            if item['quantity'] <= item.get('minStock', 5):
                low_items.append({
                    'category': category,
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'minStock': item.get('minStock', 5)
                })
    
    if not low_items:
        await interaction.response.send_message("✅ 모든 재고가 충분합니다!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚠️ 재고 부족 알림",
        description=f"총 {len(low_items)}개의 아이템이 재고 부족 상태입니다.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    for item in low_items:
        embed.add_field(
            name=f"{item['category']} - {item['name']}",
            value=f"현재: {item['quantity']}개 / 최소: {item['minStock']}개",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 도움말
@bot.tree.command(name="도움말", description="봇 사용법을 확인합니다")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 ZERO SHOP 사용법",
        description="재고를 효율적으로 관리하는 봇입니다.",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🔧 관리자 명령어",
        value="`/자판기설치` - 재고 확인 UI 생성\n`/재고추가` - 재고 추가 (모든 사람에게 알림)\n`/재고수정` - 재고 수량 수정 (모든 사람에게 알림)\n`/재고삭제` - 재고 삭제\n`/재고부족` - 재고 부족 확인",
        inline=False
    )
    
    embed.add_field(
        name="🛒 일반 사용자",
        value="자판기 UI에서 버튼을 눌러 재고를 확인하세요!",
        inline=False
    )
    
    embed.set_footer(text="ZERO SHOP - 재고 관리 시스템")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 봇 실행
if __name__ == "__main__":
    TOKEN = "MTQ3MDY5NjI0Mjg4MjI4MTUxMg.GFIxhm.LzOkqHESZ9eswXJ3SrWRNN9exUHt1zixMV15Zw"  # 봇 토큰 입력
    bot.run(TOKEN)
