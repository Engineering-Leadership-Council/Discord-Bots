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
            try:
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

        # Command: !setup_reaction <#channel> "Title" @Role1 @Role2 ...
        if message.content.startswith('!setup_reaction'):
            # Check Perms
            if not message.channel.permissions_for(message.author).administrator:
                await message.reply("❌ `sudo` access denied.")
                return

            try:
                # Split args. careful with quotes.
                # Expected: !setup_reaction #channel "Title" @Role1 @Role2
                args = message.content.split(' ', 2)
                if len(args) < 3:
                     await message.reply('Usage: `!setup_reaction #channel "Title" @Role1 @Role2 ...`')
                     return

                # Target Channel
                if not message.channel_mentions:
                    await message.reply("❌ Target channel not found.")
                    return
                target_channel = message.channel_mentions[0]

                # Remaining args: "Title" @Role1 @Role2
                # We can't rely on simple split because of Title spaces.
                # However, the mentions will always be at the end.
                
                roles = message.role_mentions
                if not roles:
                    await message.reply("❌ No roles mentioned.")
                    return
                
                # Check limit (1-9)
                number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
                if len(roles) > len(number_emojis):
                    await message.reply(f"❌ Max {len(number_emojis)} roles per message.")
                    return

                # Extract Title (everything between channel and first role)
                # This is a bit "hacky" string parsing but works for simple cases.
                # Safer way: Use the raw content, find the channel end, find the first role start.
                
                # Let's construct the Embed Description
                description = ""
                for i, role in enumerate(roles):
                    emoji = number_emojis[i]
                    description += f"{emoji} : {role.mention}\n"
                
                # Simple Title extraction: content between channel mention and first role mention
                # Note: This might be brittle if user formatting is weird.
                # Let's just take a generic approach for now or assume quotes.
                # Actually, let's just use "React to get roles!" if parsing fails, but let's try.
                # A safer bet is just to use the role list as the main content.
                
                title = "React to get Roles!"
                # Try to find quotes
                import re
                quote_match = re.search(r'"([^"]*)"', message.content)
                if quote_match:
                    title = quote_match.group(1)

                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=0x3498DB # Blue for info
                )
                embed.set_footer(text="Sudo Master • Reaction Roles")

                sent_msg = await target_channel.send(embed=embed)
                
                # Add Reactions
                for i in range(len(roles)):
                    await sent_msg.add_reaction(number_emojis[i])
                
                await message.reply(f"✅ Reaction Role message created in {target_channel.mention}")

            except Exception as e:
                await message.reply(f"❌ Error: {e}")
                print(f"Error in setup_reaction: {e}")

    async def on_raw_reaction_add(self, payload):
        await self.handle_reaction(payload, add=True)

    async def on_raw_reaction_remove(self, payload):
        await self.handle_reaction(payload, add=False)

    async def handle_reaction(self, payload, add):
        # Ignore bots and self
        if payload.user_id == self.user.id:
            return

        # Fetch Guild
        guild = self.get_guild(payload.guild_id)
        if not guild:
            return
        
        # Fetch Member (for removal events, 'member' might be None in payload, need to fetch)
        member = guild.get_member(payload.user_id)
        if not member:
            return # Member left?

        # Fetch Channel and Message
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return 
        
        # Check Author (Must be ME)
        if message.author.id != self.user.id:
            return

        # Check Embeds
        if not message.embeds:
            return
        
        embed = message.embeds[0]
        
        # Check Footer (to distinguish from other Sudo Master messages if needed)
        if not embed.footer or "Sudo Master" not in (embed.footer.text or ""):
            return

        # LOGIC: Read the Embed Description to find the matching role
        # Description format: "1️⃣ : <@&12345678>"
        emoji_str = str(payload.emoji)
        
        description_lines = (embed.description or "").split('\n')
        target_role_id = None

        for line in description_lines:
            if line.startswith(emoji_str):
                # Found the line! Now extract role ID.
                # Line: "1️⃣ : <@&12345>"
                # Split by ':'
                parts = line.split(':')
                if len(parts) < 2: 
                    continue
                
                role_mention = parts[1].strip()
                # role_mention is "<@&12345>"
                # Extract digits
                import re
                match = re.search(r'\d+', role_mention)
                if match:
                    target_role_id = int(match.group())
                break
        
        if target_role_id:
            role = guild.get_role(target_role_id)
            if role:
                try:
                    if add:
                        await member.add_roles(role)
                        print(f"Added role {role.name} to {member.name}")
                    else:
                        await member.remove_roles(role)
                        print(f"Removed role {role.name} from {member.name}")
                except discord.Forbidden:
                    print("Error: Missing permissions to manage roles.")
            else:
                print("Error: Role not found in guild.")
