import discord
import logging
import local_settings
import re
import aiohttp
import aiofiles


# TODO Log to file for PROD.
# TODO Help command/embed.
client = discord.Client()
logging.basicConfig(level=logging.WARNING)

intro_message = "Hi there! \nYou've received a chat request from a Tabletop Creator's Guild user."
emojis = ["<:greenTick:879887568932589578>", "<:redTick:879887568882237510>", "<:greyTick:879887568651558953>"]  # , "📢"


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # If message starts by mentioning a user on a specific channel.
    if message.content.startswith('<@') and message.channel.id in local_settings.jeeves_channel:
        original_author_id = message.author
        original_message_id = message.id

        # Original message content
        first_mention = message.mentions[0].mention
        if "<@!" not in first_mention[:5]:
            first_mention = re.sub(f"<@", "<@!", first_mention, count=1)
        original_message = re.sub(f"{first_mention}", "", message.content, count=1)

        # message_actions = f"<:greenTick:879887568932589578> Accept\n<:redTick:879887568882237510> Decline*\n<:greyTick:879887568651558953> Ignore\n📢 Report*\n* These actions will ask for a reason. Click the corresponding icon below.\n"
        message_actions = f"<:greenTick:879887568932589578> Accept\n<:redTick:879887568882237510> Decline\n<:greyTick:879887568651558953> Ignore (won't notify the author)\nClick the corresponding icon below.\n"

        embed_message = discord.Embed(
            description=intro_message
        )
        embed_message.set_author(name="Jeeves")  # , icon_url=message.author.avatar_url
        embed_message.set_footer(text=f"Message ID: {original_message_id}")
        embed_message.add_field(name="Author", value=f"{message.author.mention}")
        embed_message.add_field(name="Message", value=original_message, inline=False)
        embed_message.add_field(name="Actions", value=message_actions, inline=False)

        # await message.mentions[0].send(f"User {original_author_id.mention} sent: {original_message}")
        try:
            sent_message = await message.mentions[0].send(embed=embed_message)
            for emoji in emojis:
                await sent_message.add_reaction(emoji)

        except discord.errors.HTTPException:
            thread_error = await message.create_thread(name="Error Information")
            embed_thread = discord.Embed(
                description=f"Invalid format. Please send a new message first tagging a user followed by a short message."
            )
            embed_thread.add_field(name="Example", value=message.author.mention + " Lorem ipsum dolor sit amet", inline=False)
            embed_thread.add_field(name="Report", value=f"If you believe the bot is not working correctly, please contact <@!{local_settings.bot_admin_id}>", inline=False)
            await thread_error.send(embed=embed_thread)

    # Add emojis
    if message.content.startswith('jeeves add') or message.content.startswith('jeeves emoji'):
        if message.author == client.user:
            return

        url_validate = re.compile(r'^http.+(\.png|\.jpeg|\.gif|\.jpg)$', re.IGNORECASE)
        name_validate = re.compile(r'^[a-zA-Z0-9]{2,30}$')

        split_message = message.content.split(" ")

        emoji_url = ""
        emoji_name = ""

        try:
            emoji_url = split_message[2]
            emoji_name = split_message[3]
        except:
            await message.channel.send(message.author.mention + " Invalid command. Try: ```jeeves emoji image_url emoji_name```\nExample:\n```\njeeves emoji https://media.dnd.wizards.com/dnd_witchlight_highlight.png witchlight\n```")

        # try:
        if re.match(url_validate, emoji_url) is None:
            await message.channel.send(message.author.mention + " The URL is not valid. Only JPG, PNG and GIF files accepted at a maximum size of 256kb.")
        elif re.match(name_validate, emoji_name) is None:
            await message.channel.send(message.author.mention + " The Emoji's name is not valid. Only an alphanumeric name between 2-30 characters can be accepted.")
        else:

            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as resp:
                    if resp.status == 200 and len(await resp.read()) < 255000:  # File has to be under 256kb
                        emoji_added = await message.guild.create_custom_emoji(name=emoji_name, image=await resp.read())
                        await message.channel.send(f"The emoji has been added: <:{emoji_added.name}:{emoji_added.id}>\n```:{emoji_name}:```")
                    else:
                        await message.channel.send(message.author.mention + f" I was unable to fetch the image. Make sure the file is under 256kb. Poking <@!{local_settings.bot_admin_id}> for help.")


@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == local_settings.jeeves_id:
        return

    partial_message = client.get_partial_messageable(payload.channel_id)
    message = await client.get_partial_messageable(payload.channel_id).fetch_message(payload.message_id)

    # User private messages
    if message.embeds and message.embeds[0].description == intro_message:
        original_message_id = int(re.sub(f"Message ID: ", "", message.embeds[0].footer.text, count=1))
        original_message = await client.get_channel(local_settings.guild_channel_id).fetch_message(original_message_id)

        if payload.emoji.name == "greenTick" and payload.emoji.id == 879887568932589578:
            await original_message.add_reaction("<:greenTick:879887568932589578>")

            embed_thread = discord.Embed(
                description=f"<:greenTick:879887568932589578> Your chat request has been accepted. You can now send <@!{payload.user_id}> a message."
            )

            # TODO Need to find another way of checking if there's a thread. Currently if it's archived, it becomes
            #  NoneType and this check throws an error.
            if type(client.get_channel(original_message_id)) != discord.threads.Thread:
                print(type(client.get_channel(original_message_id)))
                original_thread = await original_message.create_thread(name="Chat request information", auto_archive_duration=60)
            else:
                original_thread = client.get_channel(original_message_id)

            sent_thread = await original_thread.send(embed=embed_thread)

        elif payload.emoji.name == "redTick" and payload.emoji.id == 879887568882237510:
            await original_message.add_reaction("<:redTick:879887568882237510>")

            deny_reason = ""

            embed_thread = discord.Embed(
                description=f"<:redTick:879887568882237510> Your chat request has not been accepted."
            )
            if deny_reason:
                embed_thread.add_field(name="Reason", value=deny_reason, inline=False)

            if type(client.get_channel(original_message_id)) != discord.threads.Thread:
                original_thread = await original_message.create_thread(name="Chat request information")
            else:
                original_thread = client.get_channel(original_message_id)

            sent_thread = await original_thread.send(embed=embed_thread)

            await partial_message.send("The chat request has been declined. If you need to report it, please contact any of the mods on the Tabletop Creator's Guild server.")

        elif payload.emoji.name == "greyTick" and payload.emoji.id == 879887568651558953:
            for emoji in emojis:
                # Enable to also remove all reactions on the original sender's message.
                # await original_message.remove_reaction(emoji, message.author)
                await message.remove_reaction(emoji, message.author)
            await partial_message.send("The chat request will be ignored. If you need to report it, please contact any of the mods on the Tabletop Creator's Guild server.")

        # Not currently in use. Reports are done manually.
        elif payload.emoji.name == "📢":
            print(payload.emoji.name)

    # Auto invites at 15 votes
    vote_count = 0
    vote_reactions = {}
    if message.channel.id in local_settings.votes_channel:
        if payload.emoji.name == local_settings.votes_emoji[0] and payload.emoji.id == local_settings.votes_emoji[1]:
            for i in message.reactions:
                try:
                    vote_reactions[i.emoji.id] = i.count
                except AttributeError:
                    vote_reactions[i.emoji] = i.count
                if type(i.emoji) != str and i.emoji.name == local_settings.votes_emoji[0] and i.emoji.id == local_settings.votes_emoji[1]:
                    vote_count += i.count
            if vote_count >= local_settings.votes_needed and local_settings.votes_done_emoji[0][1] not in vote_reactions and local_settings.votes_done_emoji[1][1] not in vote_reactions:
                # Add the 2 "done" reactions to the message.
                for e in local_settings.votes_done_emoji:
                    await message.add_reaction(f"<:{e[0]}:{e[1]}>")
                # Create invite and send it on the channel tagging the message author.
                message_full = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
                invite = await message_full.channel.create_invite(max_age=432000, max_uses=1)
                await message_full.reply(f"Woohoo! Here's your invite link:\n{invite.url}")


client.run(local_settings.token)