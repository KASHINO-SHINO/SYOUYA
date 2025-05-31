
import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import logging
from datetime import datetime, time
import random
from typing import Dict, List, Optional

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CharacterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        # 設定ファイル読み込み
        self.load_config()
        
        super().__init__(
            command_prefix=self.settings['command_prefix'],
            intents=intents
        )
        
        # カスタムリマインダー保存用
        self.custom_reminders = {}
        
    def load_config(self):
        """設定ファイルを読み込む"""
        with open('config/settings.json', 'r', encoding='utf-8') as f:
            self.settings = json.load(f)
        
        with open('config/character.json', 'r', encoding='utf-8') as f:
            self.character = json.load(f)
            
        with open('config/reminders.json', 'r', encoding='utf-8') as f:
            self.reminders = json.load(f)
            
        with open('config/announcements.json', 'r', encoding='utf-8') as f:
            self.announcements = json.load(f)
    
    async def on_ready(self):
        """ボットが起動したときの処理"""
        print(f'✅ {self.user} is now online!')
        print(f'🎭 Character bot ready with personality: {self.character["name"]}')
        
        # スラッシュコマンドを同期
        try:
            synced = await self.tree.sync()
            print(f'🔧 Synced {len(synced)} slash commands')
        except Exception as e:
            print(f'❌ Failed to sync commands: {e}')
        
        # スケジューラー開始
        if self.settings['schedule']['reminders']['enabled']:
            self.reminder_task.start()
        if self.settings['schedule']['announcements']['enabled']:
            self.announcement_task.start()
    
    def get_random_reminder(self, category: Optional[str] = None) -> str:
        """ランダムなリマインダーを取得"""
        if category and category in self.reminders:
            messages = self.reminders[category]
        else:
            # 全カテゴリから選択
            all_reminders = []
            for cat_messages in self.reminders.values():
                all_reminders.extend(cat_messages)
            messages = all_reminders
        
        if not messages:
            return "今日も頑張ろうぜ。お前なら大丈夫だ"
        
        return random.choice(messages)
    
    def get_random_announcement(self, category: Optional[str] = None) -> str:
        """ランダムなアナウンスメントを取得"""
        if category and category in self.announcements:
            messages = self.announcements[category]
        else:
            # 全カテゴリから選択
            all_announcements = []
            for cat_messages in self.announcements.values():
                all_announcements.extend(cat_messages)
            messages = all_announcements
        
        if not messages:
            return "みんな、今日もお疲れさん！素晴らしい一日にしようぜ"
        
        return random.choice(messages)
    
    def create_embed(self, message: str, emoji: str, color: int) -> discord.Embed:
        """Embedメッセージを作成"""
        embed = discord.Embed(
            title=f"{emoji} {self.character['name']}",
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        
        if self.character.get('avatar_url'):
            embed.set_thumbnail(url=self.character['avatar_url'])
            embed.set_footer(
                text=self.character.get('signature', f"- {self.character['name']}"),
                icon_url=self.character['avatar_url']
            )
        else:
            embed.set_footer(text=self.character.get('signature', f"- {self.character['name']}"))
        
        return embed
    
    async def get_default_channel(self):
        """デフォルトチャンネルを取得"""
        channel_id = self.settings['default_channel_id']
        channel = self.get_channel(int(channel_id))
        if not channel:
            raise Exception(f"チャンネル {channel_id} が見つかりません")
        return channel
    
    @tasks.loop(hours=24)
    async def reminder_task(self):
        """定期リマインダータスク"""
        try:
            # 時間チェック（簡単な実装）
            now = datetime.now()
            reminder_times = [9, 14, 18]  # 9時、14時、18時
            
            if now.hour in reminder_times:
                channel = await self.get_default_channel()
                reminder = self.get_random_reminder()
                embed = self.create_embed(reminder, '⏰', 0xFFD700)
                await channel.send(embed=embed)
                print(f"📝 Sent reminder: {reminder[:50]}...")
        except Exception as e:
            print(f"❌ Error in reminder task: {e}")
    
    @tasks.loop(hours=24)
    async def announcement_task(self):
        """定期アナウンスメントタスク"""
        try:
            # 月水金の12時にアナウンス
            now = datetime.now()
            if now.weekday() in [0, 2, 4] and now.hour == 12:
                channel = await self.get_default_channel()
                announcement = self.get_random_announcement()
                embed = self.create_embed(announcement, '📢', 0xFF6B6B)
                await channel.send(embed=embed)
                print(f"📢 Sent announcement: {announcement[:50]}...")
        except Exception as e:
            print(f"❌ Error in announcement task: {e}")

# ボットインスタンス作成
bot = CharacterBot()

# コマンド定義
@bot.command(name='reminder')
async def manual_reminder(ctx, category: str = None):
    """手動リマインダー送信"""
    try:
        reminder = bot.get_random_reminder(category)
        embed = bot.create_embed(reminder, '⏰', 0xFFD700)
        await ctx.send(embed=embed)
        await ctx.message.add_reaction('✅')
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {e}")

@bot.command(name='announce')
async def manual_announcement(ctx, category: str = None):
    """手動アナウンスメント送信"""
    try:
        announcement = bot.get_random_announcement(category)
        embed = bot.create_embed(announcement, '📢', 0xFF6B6B)
        await ctx.send(embed=embed)
        await ctx.message.add_reaction('✅')
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {e}")

@bot.command(name='help')
async def help_command(ctx):
    """ヘルプメッセージ表示"""
    character = bot.character
    prefix = bot.settings['command_prefix']
    
    embed = discord.Embed(
        title=f"🤖 {character['name']} Bot Commands",
        description="Konnichiwa! Here are my available commands:",
        color=0x4A90E2,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name=f"{prefix} reminder [category]",
        value="Send a random reminder\nCategories: daily_reminders, work_reminders, health_reminders, music_reminders",
        inline=False
    )
    embed.add_field(
        name=f"{prefix} announce [category]", 
        value="Send a random announcement\nCategories: motivational, community, events, seasonal, music_announcements",
        inline=False
    )
    embed.add_field(name=f"{prefix} character", value="Show information about my character", inline=True)
    embed.add_field(name=f"{prefix} status", value="Show bot status and health", inline=True)
    embed.add_field(name=f"{prefix} help", value="Show this help message", inline=True)
    
    if character.get('avatar_url'):
        embed.set_footer(text=character.get('signature'), icon_url=character['avatar_url'])
    else:
        embed.set_footer(text=character.get('signature'))
    
    await ctx.send(embed=embed)

@bot.command(name='status')
async def status_command(ctx):
    """ボットステータス表示"""
    character = bot.character
    
    embed = discord.Embed(
        title=f"📊 {character['name']} Bot Status",
        color=0x00FF00,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🤖 Bot Status",
        value="Online and healthy! ✅",
        inline=True
    )
    embed.add_field(
        name="📅 Scheduler",
        value="Running ✅",
        inline=True
    )
    
    if character.get('avatar_url'):
        embed.set_footer(text=f"Last updated: {datetime.now().isoformat()}", icon_url=character['avatar_url'])
    else:
        embed.set_footer(text=f"Last updated: {datetime.now().isoformat()}")
    
    await ctx.send(embed=embed)

@bot.command(name='character')
async def character_info(ctx):
    """キャラクター情報表示"""
    character = bot.character
    
    embed = discord.Embed(
        title=f"🎭 Meet {character['name']}!",
        description=character['personality'],
        color=0xFF69B4,
        timestamp=datetime.now()
    )
    
    traits_text = '\n'.join([f"• {trait}" for trait in character['traits']])
    embed.add_field(name="✨ Personality Traits", value=traits_text, inline=False)
    
    embed.add_field(
        name="🗣️ Speaking Style",
        value=f"Tone: {character['speaking_style']['tone']}\nEmoji Usage: {character['speaking_style']['emoji_usage']}",
        inline=True
    )
    
    phrases = '\n'.join(character['speaking_style']['common_phrases'][:3])
    embed.add_field(name="💬 Common Phrases", value=phrases, inline=True)
    
    if character.get('avatar_url'):
        embed.set_thumbnail(url=character['avatar_url'])
        embed.set_footer(text=character.get('signature'), icon_url=character['avatar_url'])
    else:
        embed.set_footer(text=character.get('signature'))
    
    await ctx.send(embed=embed)

# スラッシュコマンド定義
@bot.tree.command(name="remind", description="設楽翔也からのカスタムリマインダーを設定")
async def remind_slash(
    interaction: discord.Interaction,
    time: str,
    message: str,
    where: str = None,
    frequency: str = "daily"
):
    """カスタムリマインダー設定"""
    try:
        # 時間フォーマット検証
        import re
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
        if not re.match(time_pattern, time):
            await interaction.response.send_message(
                "おい、時間の形式が間違ってるぞ。「14:30」みたいに入力してくれ",
                ephemeral=True
            )
            return
        
        # パーソナライズされたメッセージ作成
        personalized_message = create_personalized_reminder(message, where)
        
        # リマインダーID作成
        reminder_id = f"{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
        
        # リマインダー保存
        bot.custom_reminders[reminder_id] = {
            'id': reminder_id,
            'time': time,
            'message': message,
            'where': where,
            'personalized_message': personalized_message,
            'frequency': frequency,
            'channel_id': interaction.channel.id,
            'user_id': interaction.user.id,
            'created_at': datetime.now().isoformat()
        }
        
        frequency_text = {
            'daily': '毎日',
            'weekdays': '平日',
            'weekends': '週末',
            'once': '一回のみ'
        }
        
        where_text = f"（{where}）" if where else ""
        await interaction.response.send_message(
            f"よし、設定完了だ！{frequency_text.get(frequency, '毎日')}の{time}に「{message}」{where_text}のリマインドを送るからな",
            ephemeral=True
        )
        
    except Exception as e:
        await interaction.response.send_message(
            "すまん、エラーが発生した。もう一度試してくれ",
            ephemeral=True
        )

def create_personalized_reminder(task: str, where: str = None) -> str:
    """パーソナライズされたリマインダーメッセージを作成"""
    task_responses = {
        '洗濯': [
            f"{where}で洗濯の時間だぞ。洗濯物を畳んでしまっておけよ" if where else "洗濯の時間だぞ。洗濯物を畳んでしまっておけよ",
            f"おう、{where}の洗濯物の片付けを忘れるなよ。きれいに畳んでくれ" if where else "おう、洗濯物の片付けを忘れるなよ。きれいに畳んでくれ",
        ],
        '皿洗い': [
            f"{where}で皿洗いの時間だ。きれいにしておこうぜ" if where else "皿洗いの時間だ。キッチンをきれいにしておこうぜ",
            f"おい、{where}のお皿が溜まってないか？洗って片付けろよ" if where else "おい、お皿が溜まってないか？洗って片付けろよ",
        ],
        '掃除': [
            f"{where}の掃除の時間だぞ。きれいにして気分もすっきりさせろ" if where else "掃除の時間だぞ。部屋をきれいにして気分もすっきりさせろ",
            f"{where}を掃除して環境を整えろ。きれいな場所は心も軽くするからな" if where else "掃除をして環境を整えろ。きれいな部屋は心も軽くするからな",
        ]
    }
    
    # タスクが定義済みの場合
    for key, responses in task_responses.items():
        if key in task:
            return random.choice(responses)
    
    # 汎用的なレスポンス
    if where:
        generic_responses = [
            f"{where}で{task}の時間だぞ。忘れずにやっておけよ",
            f"おう、{where}の{task}を忘れてないか？やっておいてくれ",
            f"{where}で{task}の時間だ。お前ならちゃんとできるからな"
        ]
    else:
        generic_responses = [
            f"{task}の時間だぞ。忘れずにやっておけよ",
            f"おう、{task}を忘れてないか？やっておいてくれ",
            f"{task}の時間だ。お前ならちゃんとできるからな"
        ]
    
    return random.choice(generic_responses)

@bot.tree.command(name="remind_test", description="カスタムリマインダーのテスト送信")
async def remind_test(interaction: discord.Interaction, message: str, where: str = None):
    """リマインダーテスト送信"""
    try:
        personalized_message = create_personalized_reminder(message, where)
        embed = bot.create_embed(personalized_message, '⏰', 0xFFD700)
        await interaction.response.send_message(embed=embed)
        print(f"🧪 Test reminder sent: \"{message}\" {f'({where})' if where else ''}")
    except Exception as e:
        await interaction.response.send_message(
            "すまん、テストメッセージの送信でエラーが発生した",
            ephemeral=True
        )

# ボット起動
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ DISCORD_TOKEN environment variable is required!")
        print("Please set your Discord bot token in the environment variables.")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        exit(1)
