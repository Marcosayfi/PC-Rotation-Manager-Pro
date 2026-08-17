"""Discord bot runner for PC Rotation Manager Pro."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.state_manager import StateManager

logger = logging.getLogger(__name__)

try:
    import discord
    from discord import app_commands
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False


def _format_time(minutes: float) -> str:
    total_seconds = max(0, int(minutes * 60))
    mins, secs = divmod(total_seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    return f"{mins}m {secs}s"


class DiscordBotRunner:
    def __init__(
        self,
        state_manager: StateManager,
        token: str,
        guild_id: str | None = None,
    ) -> None:
        self.state_manager = state_manager
        self.token = token
        self.guild_id = guild_id
        self._loop: asyncio.AbstractEventLoop | None = None

    def _format_status_message(self, status: dict[str, Any]) -> str:
        player_names = {1: "Joe", 2: "Marco"}

        if status.get("on_break"):
            break_player = status.get("break_player")
            break_player_name = player_names.get(break_player, f"Player {break_player}")
            reason = status.get("break_reason", "")
            reason_str = f" ({reason})" if reason else ""
            return f"⏸️ **Status:** On Break ({break_player_name}){reason_str}"

        active_player = status.get("active_player", 1)
        active_player_name = player_names.get(active_player, f"Player {active_player}")
        active_break_tokens = status.get(
            "break_tokens_p1" if active_player == 1 else "break_tokens_p2",
            0,
        )
        p1_time = _format_time(status.get("player1_time", 0.0))
        p2_time = _format_time(status.get("player2_time", 0.0))

        if status.get("stopwatch_mode"):
            stopwatch_time = _format_time(status.get("stopwatch_minutes", 0.0))
            return (
                f"⏱️ **Stopwatch Active:** {active_player_name}\n"
                f"⏱️ **Stopwatch Elapsed:** {stopwatch_time}\n"
                f"🎟️ **Break Tokens Left:** {active_break_tokens}"
            )

        active_time = p1_time if active_player == 1 else p2_time
        return (
            f"🎮 **Active Player:** {active_player_name}\n"
            f"⏳ **Time Remaining:** {active_time}\n"
            f"🎟️ **Break Tokens Left:** {active_break_tokens}"
        )

    def start(self) -> None:
        if not HAS_DISCORD:
            self.state_manager.logger.log(
                "WARNING: discord.py is not installed. Discord bot skipped."
            )
            return

        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)

        @tree.command(
            name="check-time",
            description="Check the current player and time remaining.",
        )
        async def check_time(interaction: discord.Interaction) -> None:
            status = self.state_manager.get_status()
            msg = self._format_status_message(status)
            await interaction.response.send_message(msg)

        @client.event
        async def on_ready() -> None:
            self.state_manager.logger.log(
                f"Discord bot logged in as {client.user}"
            )
            try:
                if self.guild_id and self.guild_id.strip():
                    guild = discord.Object(id=int(self.guild_id.strip()))
                    tree.copy_global_to(guild=guild)
                    synced = await tree.sync(guild=guild)
                    self.state_manager.logger.log(
                        f"Synced {len(synced)} command(s) to guild {self.guild_id}"
                    )
                else:
                    synced = await tree.sync()
                    self.state_manager.logger.log(
                        f"Synced {len(synced)} global command(s)"
                    )
            except Exception as e:
                self.state_manager.logger.log(
                    f"ERROR: Failed to sync Discord commands — {e}"
                )

        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(client.start(self.token))
        except Exception as e:
            self.state_manager.logger.log(
                f"ERROR: Discord bot stopped unexpectedly — {e}"
            )
