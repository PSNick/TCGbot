import disnake as discord
from disnake.ext import commands
import logging
import local_settings
import re


# TODO Log to file for PROD.
intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)
client.remove_command("help")
logging.basicConfig(level=logging.INFO)
embed_color = 0x60ccb4
embed_color_red = 0xff0000


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Activity(name="Tabletop Creators Guild", type=3))


@client.event
async def on_member_join(member):
    # Welcome message
    channel = client.get_channel(local_settings.welcome_channel_id[member.guild.id])
    embed_message = discord.Embed(title="Welcome to Tabletop Creators Guild!", description=f"Hi {member.mention}, {local_settings.welcome_description[member.guild.id]}", color=embed_color)
    # embed_message.set_footer(text="U̜͓̘̬͚̠̭nc̣̮͚̀ͅl̴̩͇e̶ ̛̪̦Bọ̪̠̘̰͚t̘͈̣͚̝̙ͅ ̳͖w̬̲͉͙̲a̺̻̤ͅn҉͇̥t͎̦̤̙̀s̰̲͕ ̟Y̢͖͈̮̭O̮͎̺̰̩̙̦Ṳ.̥̭ ̠͙̲Ș͍̯̰͇͝u̞̻̱p̟͕͍͎͕͚p̤̳͍͍o̯̹͙r̀t̵̘͓̜̰ ̣t̺͠h҉̜̩é̱̭͈̭̭ ̴̺̦̘̱r̬̦̠̮͓͍o̻͉͍̪b͕̭̬͎ͅͅo̙̼̫͇͓̼t ̜̪̖̤͍u͟p͍͎̲͝r̴̗̼͖̬͉i̺̘͔̝̭͉s̯̬̫͇̞̙͚i̥̥̝n̪g̝̕.̪̟̬̗͍̱")
    await channel.send(embed=embed_message)


@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == local_settings.jeeves_id:
        return

    partial_message = client.get_partial_messageable(payload.channel_id)
    message = await client.get_partial_messageable(payload.channel_id).fetch_message(payload.message_id)

    # Automatically generate a single-use invite for messages with 15 upvotes.
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
                invite = await message_full.channel.create_invite(max_age=604800, max_uses=1)
                await message_full.reply(f"A new minion! Here's your invite link:\n{invite.url}")


@client.command()
async def collab(ctx, channel_name, role_name, *member_name):
    guild = ctx.guild

    # Create new role
    new_role = await guild.create_role(name=role_name, mentionable=True, colour=discord.Color.random(), reason="Collab Command")

    # Create new text channel
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False),
                  new_role: discord.PermissionOverwrite(view_channel=True)}
    new_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites,
                                                  category=client.get_channel(local_settings.collabs_category),
                                                  topic=f"Collaboration channel for {role_name}",
                                                  reason="Collab Command")
    # await new_channel.edit(position=1)

    # Add role to members, or author if none specified.
    if member_name:
        for m in member_name:
            collab_member = await guild.fetch_member(re.sub(r"\D", "", m))
            await collab_member.add_roles(new_role, reason="Collab Command")
        # jeeves_member = await guild.fetch_member(local_settings.jeeves_id)
        # await jeeves_member.add_roles(new_role, reason="Collab Command")
        member_name = ', '.join(member_name)
    else:
        collab_member = await guild.fetch_member(ctx.author.id)
        member_name = f"<@{ctx.author.id}>"
        await collab_member.add_roles(new_role, reason="Collab Command")
        # jeeves_member = await guild.fetch_member(local_settings.jeeves_id)
        # await jeeves_member.add_roles(new_role, reason="Collab Command")

    # Add command details in new channel.
    embed_command = discord.Embed(title="Welcome to your new collaboration channel!", description=f"If you would like to add additional members, simply use the following command in this channel and I will take care of the rest. Have fun!\n\n```!summon @name1 @name2 ...```", color=embed_color)
    embed_command.set_footer(text=f"ID: {new_role.id}")

    # Send "Channel created" message in original channel.
    embed_message = discord.Embed(title="A new collaboration channel has been created", description=f"Members with the {role_name} role now have access to it. You can add new members directly on the channel.", color=embed_color)
    embed_message.add_field(name="Channel", value=new_channel.mention)
    embed_message.add_field(name="Members", value=member_name)

    await new_channel.send(embed=embed_command)
    await ctx.send(embed=embed_message)


@client.command()
async def summon(ctx, *member_name):
    if ctx.channel.category.id == local_settings.collabs_category:
        if member_name:
            guild = ctx.guild
            collab_channel = ctx.channel
            collab_message = await collab_channel.history(oldest_first=True, limit=1).flatten()
            collab_message = collab_message[0]

            if collab_message.embeds and collab_message.author.id == local_settings.jeeves_id:
                collab_role_id = int(re.sub(f"ID: ", "", collab_message.embeds[0].footer.text, count=1))
                collab_role = guild.get_role(collab_role_id)

                for m in member_name:
                    # TODO Check if user already has the role, and send a different message for those.
                    collab_member = await guild.fetch_member(re.sub(r"\D", "", m))
                    await collab_member.add_roles(collab_role, reason="Jeeves ADD Command")

                member_name = ', '.join(member_name)
                embed_message = discord.Embed(title="New minions have arrived!", description=f"Welcome {member_name}", color=embed_color)
                await ctx.send(embed=embed_message)
        else:
            embed_message = discord.Embed(title="Error: Members missing", description=f"Please use `!summon @name1 @name2 ...`\n If you are using the command correctly and the problem persists, contact `@Nick#2947` for help.", color=embed_color_red)
            await ctx.send(embed=embed_message)
    else:
        embed_message = discord.Embed(title="Error: Incorrect location", description=f"The **!summon** command can only be used in your collaboration channel. If you are on the correct channel and the problem persists, contact `@Nick#2947` for help.", color=embed_color_red)
        await ctx.send(embed=embed_message)


@client.command(name="help", aliases=["jeeves", "jeeves help", "help jeeves"])
async def help(ctx):
    embed_help = discord.Embed(
        description='''Jeeves was created by <@84855914615537664> to handle new member interactions (invites and welcome messages) and collaborations for the Tabletop Creators Guild.
        
    **Commands:**
    **!collab** will quickly create a role and channel for selected members.
    **!summon** will add new members to the appropriate collaboration channel.
    \n\n
    ''', color=embed_color
    )
    embed_help.set_author(name="Help Page", icon_url="https://discord.com/assets/f9bb9c4af2b9c32a2c5ee0014661546d.png")
    # embed_help.add_field(name="Usage", value='!collab "CHANNEL NAME" "ROLE NAME" @member1 @member2 ...', inline=False)
    embed_help.add_field(name="Usage: !collab", value='!collab "CHANNEL NAME" "ROLE NAME" *(will only add the author)*\n*or*\n!collab "CHANNEL NAME" "ROLE NAME" @member1 @member2 ...', inline=False)
    embed_help.add_field(name="Usage: !summon", value='!summon @member1 @member2 ... *(can only be used in a collab channel)*', inline=False)
    embed_help.set_footer(text="\nv1.0, contact Nick if you encounter any problems.")
    await ctx.send(embed=embed_help)


client.run(local_settings.token)
