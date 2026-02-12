import discord
import os
import re

class RoleBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        
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

        # Command: !setup_reaction <#channel> "Title" <Emoji> @Role ...
        if message.content.startswith('!setup_reaction'):
            # Check Perms
            if not message.channel.permissions_for(message.author).administrator:
                await message.reply("❌ `sudo` access denied.")
                return

            try:
                # 1. Extract Target Channel
                if not message.channel_mentions:
                    await message.reply("❌ Target channel not found.")
                    return
                target_channel = message.channel_mentions[0]

                # 2. Extract Title
                title = "React to get Roles!"
                quote_match = re.search(r'"([^"]*)"', message.content)
                if quote_match:
                    title = quote_match.group(1)

                # 3. Clean content for parsing pairs
                # Remove command, channel mention, and title to avoid false matches
                clean_content = message.content.replace('!setup_reaction', '', 1)
                clean_content = clean_content.replace(target_channel.mention, '', 1)
                if quote_match:
                    clean_content = clean_content.replace(quote_match.group(0), '', 1)
                
                # 4. Find Emoji-Role Pairs
                # Regex looks for: (Non-whitespace) followed by (Role Mention)
                # Matches: "🔴 <@&123>" or "<:custom:123> <@&456>"
                pair_pattern = r'(\S+)\s+(<@&\d+>)'
                matches = re.findall(pair_pattern, clean_content)

                if not matches:
                    await message.reply('Usage: `!setup_reaction #channel "Title" <Emoji> @Role ...`\nExample: `!setup_reaction #gen "Roles" 🔴 @Red 🔵 @Blue`')
                    return

                # 5. Build Description and Role Map
                description = ""
                emojis_to_add = []
                
                for emoji, role_mention in matches:
                    description += f"{emoji} : {role_mention}\n"
                    emojis_to_add.append(emoji)
                
                # 6. Create and Send Embed
                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=0x3498DB # Blue for info
                )
                embed.set_footer(text="Sudo Master • Reaction Roles")

                sent_msg = await target_channel.send(embed=embed)
                
                # 7. Add Reactions
                for emoji in emojis_to_add:
                    try:
                        await sent_msg.add_reaction(emoji)
                    except Exception as e:
                        print(f"Failed to add reaction {emoji}: {e}")
                        # Continue adding others even if one fails
                
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
        # Description format: "<Emoji> : <@&12345678>"
        # We need to match the reaction emoji to the line.
        
        emoji_str = str(payload.emoji) 
        # payload.emoji is a PartialEmoji. str() converts it to:
        # - Unicode: "🔴"
        # - Custom: "<:name:id>" or "<a:name:id>"
        
        description_lines = (embed.description or "").split('\n')
        target_role_id = None

        for line in description_lines:
            # We look for the line that starts with the emoji.
            # Simple startswith might be risky if emojis are subsets of each other, 
            # but usually fine.
            # Best to check if line starts with "{emoji_str} :"
            
            # Allow flexible spacing around colon
            if line.strip().startswith(emoji_str):
                # Found the line! Now extract role ID.
                # Regex for role mention: <@&(\d+)>
                role_match = re.search(r'<@&(\d+)>', line)
                if role_match:
                    target_role_id = int(role_match.group(1))
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
                    print(f"Error: Missing permissions to manage roles (Target Role: {role.name}).")
            else:
                print(f"Error: Role ID {target_role_id} not found in guild.")

