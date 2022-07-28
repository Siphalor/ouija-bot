import os
import random
from typing import Optional

import interactions
from dotenv import load_dotenv
from interactions.ext.tasks import create_task, IntervalTrigger

load_dotenv()

SCOPE = os.getenv("DISCORD_SCOPE")
TOKEN = os.getenv("DISCORD_TOKEN")
bot = interactions.Client(
    TOKEN,
    intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_MESSAGE_CONTENT
)

ouija_running = False
current_channel: Optional[interactions.Channel] = None
current_message = ""
letters = {}


@bot.command(
    name="start",
    description="Start the ouija round",
    scope=SCOPE,
)
async def start_command(ctx: interactions.CommandContext):
    global current_message, current_channel, ouija_running, letters
    if ouija_running:
        await ctx.send("Ouija has already been started!", ephemeral=True)
        return

    await ctx.send("Ouija round started!")
    current_message = ""
    current_channel = await ctx.get_channel()
    ouija_running = True
    letters = {}


@bot.command(
    name="goodbye",
    description="End a ouija round",
    scope=SCOPE,
)
async def goodbye_command(ctx: interactions.CommandContext):
    global current_message, ouija_running
    if not ouija_running:
        await ctx.send("Ouija round has not been started yet", ephemeral=True)
        pass
    else:
        ouija_running = False
        await ctx.send("Complete message: " + current_message)


@bot.event(name="on_message_create")
async def on_message_create(message: interactions.Message):
    global current_message, ouija_running, current_channel, letters
    if not ouija_running or current_channel is None:
        return
    if current_channel.id != message.channel_id:
        return

    if len(message.content) == 1:
        letters[message.author.id] = message.content


@create_task(IntervalTrigger(10))
async def timer():
    global current_message, ouija_running, current_channel, letters
    if ouija_running:
        if letters:
            letter_distribution = {}
            for value in letters.values():
                if value in letter_distribution:
                    letter_distribution[value] += 1
                else:
                    letter_distribution[value] = 1

            most = max(letter_distribution.items(), key=lambda a: a[1])[1]
            letter = random.choice([c for (c, o) in letter_distribution.items() if o == most])

            if letter == '_':
                letter = ' '

            letter = letter.lower()
            current_message = current_message + letter
            await current_channel.send(f"\"{letter}\" won; current message: " + current_message)
        else:
            if current_message[len(current_message) - 1] != ' ':
                await current_channel.send("No letters received; adding space: " + current_message)
            else:
                await current_channel.send("No letters received; skipping: " + current_message)
            current_message += ' '

        letters = {}


timer.start()
bot.start()
