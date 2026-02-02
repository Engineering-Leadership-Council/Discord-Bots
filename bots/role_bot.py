import discord
import os

# Configuration for Affiliate Clubs
# Format: "Label": Role_ID
# REPLACE THESE WITH REAL ROLE JS FROM YOUR SERVER
CLUB_ROLES = {
    "Robotics Club": int(os.getenv('ROBOTICS_CLUB_ROLE_ID', '0')),
}

class ClubRoleSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for label in CLUB_ROLES.keys():
            options.append(discord.SelectOption(label=label, value=label))

        super().__init__(
            placeholder="Select a club to join...",
            min_values=1,
            max_values=1, # Allow picking one at a time, or multiple? Let's say 1 for now or handle list.
            options=options,
            custom_id="select:club_roles"
        )

    async def callback(self, interaction: discord.Interaction):
        club_name = self.values[0]
        role_id = CLUB_ROLES.get(club_name)
        
        if role_id == 0:
            await interaction.response.send_message(f"⚠️ Configuration Error: The role ID for **{club_name}** hasn't been set yet.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ Error: Role not found on server.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"➖ Removed **{club_name}** role.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"➕ Added **{club_name}** role!", ephemeral=True)

class ClubRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view
        self.add_item(ClubRoleSelect())

class RoleBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        # We need to register the persistent view so it works after restart
        self.add_view(ClubRoleView())
        
        # Set nickname
        for guild in self.guilds:
            try:
                await guild.me.edit(nick="Sudo Master")
                print(f"Changed nickname to 'Sudo Master' in {guild.name}")
            except Exception as e:
                print(f"Nickname change failed in {guild.name}: {e}")

    async def on_message(self, message):
        # Ignore own messages
        if message.author == self.user:
            return

        # Debug: Print raw message content
        print(f"DEBUG: Message from {message.author}: {message.content}")

        # Command: !setup_clubs <#channel>
        if message.content.startswith('!setup_clubs'):
            # Security check: limit to admins? For now, we'll assume the user running this has perms.
            permissions = message.channel.permissions_for(message.author)
            if not permissions.administrator:
                await message.reply("❌ `sudo` access denied. You need Administrator permissions.")
                return

            # Parse channel link
            # format: !setup_clubs <#12345678>
            try:
                # Extract the first channel mention
                if not message.channel_mentions:
                     await message.reply("usage: `!setup_clubs #channel`")
                     return
                
                target_channel = message.channel_mentions[0]
                
                embed = discord.Embed(
                    title="🔧 Affiliate Clubs & Projects",
                    description="Select a club from the dropdown below to join (or leave) it!\n\n*Roles grant access to private channels.*",
                    color=0x2ECC71 # Green for 'Sudo'
                )
                
                await target_channel.send(embed=embed, view=ClubRoleView())
                await message.reply(f"✅ Setup complete! Menu posted in {target_channel.mention}")
                
            except Exception as e:
                await message.reply(f"❌ Error: {e}")
