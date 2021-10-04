import discord
import logging
import local_settings
import re

# TODO Log to file for PROD.
logging.basicConfig(level=logging.WARNING)
client = discord.Client()

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
        sent_message = await message.mentions[0].send(embed=embed_message)

        for emoji in emojis:
            await sent_message.add_reaction(emoji)


@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == local_settings.jeeves_id:
        return

    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    # reaction = discord.utils.get(message.reactions, emoji="📩")
    original_message_id = int(re.sub(f"Message ID: ", "", message.embeds[0].footer.text, count=1))
    original_message = await client.get_channel(local_settings.guild_channel_id).fetch_message(original_message_id)

    if message.channel.type == discord.ChannelType.private and message.embeds[0].description == intro_message:
        print("private")

        if payload.emoji.name == "greenTick" and payload.emoji.id == 879887568932589578:
            print(payload.emoji.name)
            await original_message.add_reaction("<:greenTick:879887568932589578>")

            embed_thread = discord.Embed(
                description=f"<:greenTick:879887568932589578> Your chat request has been accepted. You can now send <@!{payload.user_id}> a message."
            )

            if type(client.get_channel(original_message_id)) != discord.threads.Thread:
                original_thread = await original_message.create_thread(name="Chat request information")
            else:
                original_thread = client.get_channel(original_message_id)

            sent_thread = await original_thread.send(embed=embed_thread)

        elif payload.emoji.name == "redTick" and payload.emoji.id == 879887568882237510:
            print(payload.emoji.name)
            await original_message.add_reaction("<:redTick:879887568882237510>")

            deny_reason = ""

            embed_thread = discord.Embed(
                description=f"<:redTick:879887568882237510> Your chat request has been denied."
            )
            if deny_reason:
                embed_thread.add_field(name="Reason", value=deny_reason, inline=False)

            if type(client.get_channel(original_message_id)) != discord.threads.Thread:
                original_thread = await original_message.create_thread(name="Chat request information")
            else:
                original_thread = client.get_channel(original_message_id)

            sent_thread = await original_thread.send(embed=embed_thread)

        elif payload.emoji.name == "greyTick" and payload.emoji.id == 879887568651558953:
            print(payload.emoji.name)
            for emoji in emojis:
                await original_message.remove_reaction(emoji, message.author)
                await message.remove_reaction(emoji, message.author)
            await message.channel.send("The chat request will be ignored.")

        elif payload.emoji.name == "📢":
            print(payload.emoji.name)

    else:
        print("else")
        return

client.run(local_settings.token)