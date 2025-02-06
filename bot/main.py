import re
import os
from loguru import logger
from db import FlagsDatabase, FlagAlreadySubmitted
from interactions import Client, Intents, SlashContext, slash_command, OptionType, SlashCommandOption, GuildText


DISCORD_BOT_ID = os.getenv('DISCORD_BOT_ID')
bot = Client(
    intents=Intents.DEFAULT,
    send_command_tracebacks=False,
    sync_interactions=True,
    asyncio_debug=True,
    logger=logger
)


def extract_team(channel_nam: str) -> int | None:
    team = re.search(r'\d+', channel_nam)
    return int(team.group(0)) if team else None


def get_team_channel(channel_id: int) -> GuildText | None:
    channel = bot.get_channel(channel_id)
    return channel if channel else None


@slash_command(
    name="submit_flag",
    description="",
    options=[
        SlashCommandOption(
            name="flag",
            description="Flag",
            required=True,
            type=OptionType.STRING,
            min_length=32,
            max_length=32
        )
    ]
)
async def submit_flag_function(ctx: SlashContext, flag: str):
    channel_name = ctx.channel.name.lower()
    if not channel_name.startswith('team'):
        await ctx.send('Invalid channel.', ephemeral=True)
        return

    team = extract_team(channel_name)
    if not team:
        await ctx.send('Could not find team number.')
        return

    valid_flag = database.get_team(flag)
    if not valid_flag:
        await ctx.send('Invalid flag.')
        return

    if valid_flag['team'] == team:
        await ctx.send('Cannot submit your own flag.')
        return

    try:
        database.submit_flag(flag, team)
    except FlagAlreadySubmitted as e:
        await ctx.send(e.message)
    except Exception as e:
        logger.critical(f'{e.__class__.__name__}: {e}')
        await ctx.send('An unknown error occurred.')
    else:
        await ctx.send('# Flag successfully submitted. `+50 points`')
        loser_channel = get_team_channel(valid_flag['channel_id'])
        await loser_channel.send(f'# 🚨 Team {team} has found one of your flags! 🚨')


if __name__ == '__main__':
    database = FlagsDatabase()
    database.initialize_database()
    database.import_flags()
    bot.start(DISCORD_BOT_ID)
