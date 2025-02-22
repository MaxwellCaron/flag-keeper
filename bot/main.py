import re
import os
from loguru import logger
from db import FlagsDatabase, FlagAlreadySubmitted
from interactions import Client, Intents, SlashContext, slash_command, OptionType, SlashCommandOption, GuildText, Permissions


DISCORD_BOT_ID = os.getenv('DISCORD_BOT_ID')
POINTS_GAINED = int(os.getenv('POINTS_GAINED'))
POINTS_LOST = -int(os.getenv('POINTS_LOST'))
POINTS_LOST_SCALED = float(os.getenv('POINTS_LOST_SCALED'))

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
            min_length=64,
            max_length=64
        )
    ]
)
async def submit_flag_function(ctx: SlashContext, flag: str):
    channel_name = ctx.channel.name.lower()
    if not channel_name.endswith('chat'):
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
        await ctx.send(f'# Flag successfully submitted. `+{POINTS_GAINED} points`')
        loser_channel = get_team_channel(valid_flag['channel_id'])
        await loser_channel.send(f'# 🚨 Team {team} has found one of your flags! 🚨')


@slash_command(
    name="calculate_scores",
    description="Calculates total points gained/lost from flag submissions for each team.",
    default_member_permissions=Permissions.ADMINISTRATOR
)
async def calculate_scores_function(ctx: SlashContext):
    submitted_flags = database.get_submitted_flags()
    found_flags = database.get_found_flags()
    if not submitted_flags or not found_flags:
        await ctx.send('Error retrieving results.', ephemeral=True)
        return

    scale = int(POINTS_LOST * POINTS_LOST_SCALED) if POINTS_LOST_SCALED else 0
    gained_points = {team_num: calculate_gained_points(flags) for team_num, flags in submitted_flags}
    lost_points = {team_num: calculate_lost_points(flags, scale) for team_num, flags in found_flags}

    final_str = '\n'.join(f'{i+1},{gained_points.get(team_num, 0)},{lost_points.get(team_num, 0)}'
                          for i, team_num in enumerate(gained_points.keys()))

    await ctx.send(f'```{final_str}```')


def calculate_gained_points(flags: int) -> int:
    return flags * POINTS_GAINED


def calculate_lost_points(flags: int, scale: int) -> int:
    points = flags * POINTS_LOST
    scaled = (flags - 1) * scale if scale else 0
    return points + scaled


if __name__ == '__main__':
    database = FlagsDatabase()
    database.initialize_database()
    database.import_flags()
    bot.start(DISCORD_BOT_ID)
