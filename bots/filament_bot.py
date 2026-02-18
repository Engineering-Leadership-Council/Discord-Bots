import discord
from discord import ui
import os
import asyncio
from typing import List, Dict, Optional
import bot_config
from utils.filament_data_manager import FilamentDataManager

# --- Modals ---
class LogUsageModal(ui.Modal, title="Log Filament Usage"):
    amount = ui.TextInput(label="Amount Used (g)", placeholder="e.g., 50.5", min_length=1, max_length=10)

    def __init__(self, bot, filament_id, filament_name):
        super().__init__()
        self.bot = bot
        self.filament_id = filament_id
        self.filament_name = filament_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_val = float(self.amount.value)
            self.bot.data_manager.log_usage(interaction.user.display_name, self.filament_id, amount_val)
            self.bot.data_manager.update_filament_weight(self.filament_id, amount_val)
            
            await interaction.response.send_message(
                f"✅ Logged **{amount_val}g** usage for **{self.filament_name}**.",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount. Please enter a number.", ephemeral=True)
        except Exception as e:
            print(f"Error logging usage: {e}")
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

class AddFilamentModal(ui.Modal, title="Add New Filament"):
    brand = ui.TextInput(label="Brand", placeholder="e.g., Elegoo", max_length=50)
    type_name = ui.TextInput(label="Type", placeholder="e.g., PLA", max_length=20)
    color = ui.TextInput(label="Color", placeholder="e.g., Matte Black", max_length=30)
    weight = ui.TextInput(label="Initial Weight (g)", placeholder="e.g., 1000", max_length=10)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            weight_val = float(self.weight.value)
            new_id = self.bot.data_manager.add_inventory_item(
                self.type_name.value, 
                self.brand.value, 
                self.color.value, 
                weight_val
            )
            await interaction.response.send_message(
                f"✅ Added **{self.brand.value} {self.type_name.value} ({self.color.value})** with ID **{new_id}**.",
                ephemeral=True
            )
        except ValueError:
             await interaction.response.send_message("❌ Invalid weight. Please enter a number.", ephemeral=True)
        except Exception as e:
            print(f"Error adding filament: {e}")
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# --- Select Menus ---
class FilamentSelect(ui.Select):
    def __init__(self, bot):
        self.bot: 'FilamentBot' = bot
        options = []
        inventory = self.bot.data_manager.get_inventory()
        
        # Sort by ID or usage? Let's sort by color/type for readability
        sorted_inv = sorted(inventory, key=lambda x: (x.get('type', ''), x.get('color', '')))
        
        for item in sorted_inv:
            label = f"{item['brand']} {item['type']} - {item['color']}"
            desc = f"Remaining: {item['weight_g']}g"
            if len(label) > 100: label = label[:97] + "..."
            
            options.append(discord.SelectOption(
                label=label, 
                description=desc, 
                value=str(item['id'])
            ))
            if len(options) >= 25: break 

        super().__init__(placeholder="Select a filament...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        filament_id = int(self.values[0])
        # Find name for modal title
        inventory = self.bot.data_manager.get_inventory()
        item = next((x for x in inventory if x['id'] == filament_id), None)
        name = f"{item['color']} {item['type']}" if item else "Unknown"
        
        await interaction.response.send_modal(LogUsageModal(self.bot, filament_id, name))

# --- Views ---
class FilamentDashboardView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Log Usage", style=discord.ButtonStyle.primary, custom_id="filament_log_usage")
    async def log_usage_btn(self, interaction: discord.Interaction, button: ui.Button):
        # Create a view with just the select menu
        view = ui.View()
        select = FilamentSelect(self.bot)
        if not select.options:
             await interaction.response.send_message("⚠️ No filament in inventory!", ephemeral=True)
             return
        view.add_item(select)
        await interaction.response.send_message("Select the filament you used:", view=view, ephemeral=True)

    @ui.button(label="Add Filament", style=discord.ButtonStyle.success, custom_id="filament_add_item")
    async def add_filament_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddFilamentModal(self.bot))

    @ui.button(label="View Inventory", style=discord.ButtonStyle.secondary, custom_id="filament_view_inv")
    async def view_inv_btn(self, interaction: discord.Interaction, button: ui.Button):
        inventory = self.bot.data_manager.get_inventory()
        if not inventory:
            await interaction.response.send_message("Inventory is empty.", ephemeral=True)
            return

        embed = discord.Embed(title="Current Filament Inventory", color=0xE67E22)
        
        # Group by Type for cleaner display
        grouped = {}
        for item in inventory:
            ftype = item.get('type', 'Other')
            if ftype not in grouped: grouped[ftype] = []
            grouped[ftype].append(item)
            
        for ftype, items in grouped.items():
            content = ""
            for item in items:
                content += f"• **{item['brand']} {item['color']}**: {item['weight_g']}g\n"
            embed.add_field(name=ftype, value=content, inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)


class FilamentBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data_path = os.getenv('FILAMENT_DATA_PATH')
        if not data_path:
            print("ERROR: FILAMENT_DATA_PATH not set in .env")
            data_path = "./data" # Fallback
            
        self.data_manager = FilamentDataManager(data_path)

    async def setup_hook(self):
        # We can add persistent views here if we want the dashboard to survive restarts without reposting
        # For now, simplest is to just re-create it on command
        pass

    async def on_ready(self):
        print(f'Filament Tracker logged in as {self.user} (ID: {self.user.id})')
        for guild in self.guilds:
            try:
                await guild.me.edit(nick=bot_config.FILAMENT_BOT_NICKNAME)
            except Exception as e:
                pass


    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('!filament dashboard'):
            view = FilamentDashboardView(self)
            embed = discord.Embed(
                title="🧵 Filament Tracking Dashboard",
                description="Use the buttons below to manage filament inventory.",
                color=0xE67E22
            )
            await message.channel.send(embed=embed, view=view)
