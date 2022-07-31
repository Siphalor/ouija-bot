import os
import random

import interactions
from dotenv import load_dotenv
from interactions.ext.tasks import create_task, IntervalTrigger

import persistence

load_dotenv()

SCOPE = os.getenv("DISCORD_SCOPE")
if SCOPE == "None":
    SCOPE = interactions.MISSING

TOKEN = os.getenv("DISCORD_TOKEN")
bot = interactions.Client(
    TOKEN,
    intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_MESSAGE_CONTENT,
)
save_counter: int = 0

persistence.load()

config_options_option = interactions.Option(
    name="option",
    description="The option to target",
    type=interactions.OptionType.STRING,
    required=True,
    choices=[
        interactions.Choice(
            name="Unit - How much to add each step: `word` or `letter`",
            value="unit",
        ),
        interactions.Choice(
            name="Mode - `Polls` or Round-`robbin`'",
            value="mode",
        ),
        interactions.Choice(
            name="Lowercase all",
            value="lowercase",
        ),
        interactions.Choice(
            name="Update interval",
            value="time"
        )
    ]
)


@bot.command(
    name="start",
    description="Start the ouija round",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=SCOPE,
)
async def start_command(ctx: interactions.CommandContext):
    guild_data = persistence.get_guild(str(ctx.guild_id))

    if guild_data["running"]:
        await ctx.send("Ouija has already been started!", ephemeral=True)
        return

    await ctx.send("Ouija round started!")
    persistence.start_guild(ctx.guild_id, await ctx.get_channel())


@bot.command(
    name="goodbye",
    description="End a ouija round",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=SCOPE,
)
async def goodbye_command(ctx: interactions.CommandContext):
    guild_data = persistence.get_guild(str(ctx.guild_id))

    if not guild_data["running"]:
        await ctx.send("Ouija round has not been started yet", ephemeral=True)
    else:
        persistence.stop_guild(ctx.guild_id)
        await ctx.send("Complete message: " + guild_data["message"])


@bot.command(
    name="config",
    description="Configure this bot",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=SCOPE,
)
async def config_command(_ctx: interactions.CommandContext):
    pass


@config_command.subcommand(
    name="get",
    description="Get the current configuration",
    options=[config_options_option],
)
async def config_get_command(ctx: interactions.CommandContext, option: str):
    guild_data = persistence.get_guild(str(ctx.guild_id))
    if option == "mode":
        await ctx.send(f"Mode is set to `{guild_data['mode']}`.", ephemeral=True)
    elif option == "unit":
        await ctx.send(f"Unit is set to `{guild_data['unit']}`.", ephemeral=True)
    elif option == "lowercase":
        await ctx.send(f"Lowercase all is set to `{guild_data['lowercase']}`.", ephemeral=True)
    elif option == "time":
        await ctx.send(f"Update interval is set to `{guild_data['interval']}`.", ephemeral=True)


@config_command.subcommand(
    name="set",
    description="Update the configuration",
    options=[
        config_options_option,
        interactions.Option(
            name="value",
            description="The value to set the config to",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ]
)
async def config_set_command(ctx: interactions.CommandContext, option: str, value: str):
    guild_data = persistence.get_guild(str(ctx.guild_id))

    value = value.lower().strip()

    if option == "mode":
        if value == "poll":
            guild_data["mode"] = "poll"
        elif value == "robbin":
            guild_data["mode"] = "robbin"
        else:
            await ctx.send("Incorrect value, use `poll` or `robbin`", ephemeral=True)
            return

        await ctx.send(f"Mode is now set to {guild_data['mode']}.", ephemeral=True)

    elif option == "unit":
        if value == "letter":
            guild_data['unit'] = value
        elif value == "word":
            guild_data['unit'] = value
        else:
            await ctx.send("Incorrect value, use `letter` or `word`", ephemeral=True)
            return

        await ctx.send(f"Unit is now set to {guild_data['unit']}.", ephemeral=True)

    elif option == "lowercase":
        if value == "true":
            guild_data['lowercase'] = True
        elif value == "false":
            guild_data['lowercase'] = False
        else:
            await ctx.send("Incorrect value, use `true` or `false`", ephemeral=True)
            return

        await ctx.send(f"Lowercase all is now set to {guild_data['lowercase']}.", ephemeral=True)

    elif option == "poll_time":
        if not value.isnumeric() and int(value) > 0:
            await ctx.send("Incorrect value, must be numeric and positive", ephemeral=True)
            return

        guild_data['interval'] = int(value)
        await ctx.send(f"Update interval time is now set to {guild_data['interval']}.", ephemeral=True)

    persistence.save()


@bot.event(name="on_message_create")
async def on_message_create(message: interactions.Message):
    running_data = await persistence.get_running(str(message.guild_id), bot)

    if running_data is None:
        return
    if message.channel_id != running_data['channel'].id:
        return

    unit = None
    if running_data['guild']['unit'] == "letter" and len(message.content) == 1:
        unit = message.content
    elif running_data['guild']['unit'] == "word" and not any(c.isspace() for c in message.content):
        unit = message.content

    if unit is not None:
        if running_data['guild']['lowercase']:
            unit = unit.lower()

        if running_data['guild']['mode'] == "poll":
            running_data['units'][message.author.id] = unit
        elif running_data['guild']['mode'] == "robbin":
            if running_data['guild']['unit'] == 'letter':
                running_data['guild']['message'] += unit
            else:
                running_data['guild']['message'] += " " + unit


@create_task(IntervalTrigger(1))
async def timer():
    global save_counter
    if save_counter >= 120:
        persistence.save()
        save_counter = 0
    else:
        save_counter += 1

    for running_data in await persistence.get_all_running(bot):
        running_data['timer'] += 1
        if running_data['timer'] < running_data['guild']['interval']:
            return

        running_data['timer'] = 0
        message = running_data['guild']['message']

        if running_data['guild']['mode'] == "robbin":
            if running_data.get('last_message') == message:
                running_data['misses'] += 1
                if running_data['misses'] > 6:
                    await running_data['channel'].send(f"Goodbye: {message}")
                    persistence.stop_guild(str(running_data['channel'].guild_id))
                    return
            else:
                running_data['last_message'] = message

            await running_data['channel'].send(f"Current message: {message}")
            return

        if running_data['units']:
            letter_distribution = {}
            for value in running_data['units'].values():
                if value in letter_distribution:
                    letter_distribution[value] += 1
                else:
                    letter_distribution[value] = 1

            most = max(letter_distribution.items(), key=lambda a: a[1])[1]
            unit = random.choice([c for (c, o) in letter_distribution.items() if o == most]).strip()

            if running_data['guild']['unit'] == "letter" and unit == '_':
                unit = ' '

            if running_data['guild']['lowercase']:
                unit = unit.lower()

            message = message + unit
            await running_data['channel'].send(f"\"{unit}\" won; current message: {message}")
        else:
            if message and message[len(message) - 1] != ' ':
                await running_data['channel'].send("No letters received; adding space: " + message)
            else:
                await running_data['channel'].send("No letters received; skipping: " + message)
            message += ' '

        running_data['guild']['message'] = message
        running_data['units'] = {}


timer.start()
bot.start()
