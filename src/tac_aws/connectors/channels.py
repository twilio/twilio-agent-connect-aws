"""The channel set the AWS connectors build and route responses through.

Every connector in this package manages the same thing: one channel per Twilio
channel TAC supports, plus the routing that picks the right one for an inbound
message. That shared piece lives here so `StrandsConnector`, `BedrockConnector`,
and `BedrockAgentCoreConnector` differ only in how they reach their agent
runtime.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from tac.channels.chat import ChatChannel, ChatChannelConfig
from tac.channels.rcs import RCSChannel, RCSChannelConfig
from tac.channels.sms import SMSChannel, SMSChannelConfig
from tac.channels.voice import VoiceChannel, VoiceChannelConfig
from tac.channels.whatsapp import WhatsAppChannel, WhatsAppChannelConfig
from tac.core.logging import get_logger
from tac.core.tac import TAC
from tac.models.session import ConversationSession

if TYPE_CHECKING:
    from tac.channels.base import BaseChannel
    from tac.channels.messaging import MessagingChannel

logger = get_logger(__name__)

ChannelResponse = str | AsyncGenerator[str, None]
"""A response to deliver: complete text, or a stream of tokens."""

_SENDER_HINTS = {
    "RCS": " Set TWILIO_RCS_SENDER_ID (or TACConfig.rcs_sender_id) to enable it.",
    "WHATSAPP": " Set TWILIO_WHATSAPP_NUMBER (or TACConfig.whatsapp_number) to enable it.",
}
"""The env var that turns on each sender-gated channel, for the routing error."""


class ConnectorChannels:
    """The TAC channels a connector owns, and the routing between them.

    Voice, SMS, and Chat are always created. RCS and WhatsApp are created only
    when their Twilio sender is configured — `TWILIO_RCS_SENDER_ID` /
    `TACConfig.rcs_sender_id` for RCS, `TWILIO_WHATSAPP_NUMBER` /
    `TACConfig.whatsapp_number` for WhatsApp — because `RCSChannel` and
    `WhatsAppChannel` raise `ValueError` at construction without one. The
    `*_config` arguments are tuning only (`memory_mode`, dedup, agent identity);
    they never enable or disable a channel.

    Attributes:
        voice: `VoiceChannel` for voice conversations
        sms: `SMSChannel` for SMS conversations
        chat: `ChatChannel` for web chat conversations
        rcs: `RCSChannel`, or None when no RCS sender ID is configured
        whatsapp: `WhatsAppChannel`, or None when no WhatsApp number is configured
        messaging: Every available messaging channel, ready to hand to a server as
            `messaging_channels=...`

    Example:
        ```python
        # With TWILIO_WHATSAPP_NUMBER set, connector.whatsapp is ready to use.
        connector = StrandsConnector(
            tac=tac,
            agent_factory=create_agent,
            sms_config=SMSChannelConfig(memory_mode="always"),
        )

        server = TACAWSFastAPIServer(
            tac=tac,
            voice_channel=connector.voice,
            messaging_channels=connector.channels.messaging,
        )
        ```
    """

    def __init__(
        self,
        tac: TAC,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        rcs_config: RCSChannelConfig | dict[str, Any] | None = None,
        whatsapp_config: WhatsAppChannelConfig | dict[str, Any] | None = None,
        chat_config: ChatChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        self.voice = VoiceChannel(tac=tac, config=voice_config)
        self.sms = SMSChannel(tac=tac, config=sms_config)
        self.chat = ChatChannel(tac=tac, config=chat_config)
        # RCS and WhatsApp follow their Twilio sender: the TAC channel requires
        # one at construction, so without it there is nothing to build.
        self.rcs = RCSChannel(tac=tac, config=rcs_config) if tac.config.rcs_sender_id else None
        self.whatsapp = (
            WhatsAppChannel(tac=tac, config=whatsapp_config) if tac.config.whatsapp_number else None
        )

        self.messaging: list[MessagingChannel] = [
            channel
            for channel in (self.sms, self.rcs, self.whatsapp, self.chat)
            if channel is not None
        ]
        # Keys are TAC's channel names — the values ConversationSession.channel
        # carries and each channel's get_channel_name() returns.
        self._by_name: dict[str, BaseChannel] = {
            name: channel
            for name, channel in (
                ("VOICE", self.voice),
                ("SMS", self.sms),
                ("RCS", self.rcs),
                ("WHATSAPP", self.whatsapp),
                ("CHAT", self.chat),
            )
            if channel is not None
        }

        logger.debug(f"Channels available: {', '.join(self._by_name)}")

    def get(self, channel_name: str) -> BaseChannel | None:
        """The available channel with this TAC channel name, or None."""
        return self._by_name.get(channel_name)

    async def send(
        self,
        context: ConversationSession,
        response: ChannelResponse,
        role: str = "assistant",
    ) -> bool:
        """Send a response on the channel the conversation arrived on.

        A streamed response goes to the voice channel token by token; messaging
        channels send one complete message, so a stream is collected first.

        Args:
            context: Conversation session — `context.channel` selects the channel.
            response: Complete text, or an async generator of tokens.
            role: Message role passed through to the channel.

        Returns:
            True if a channel handled it; False when no channel is available for
            `context.channel` (logged as an error — the message is dropped).
        """
        channel = self.get(context.channel)
        if channel is None:
            hint = _SENDER_HINTS.get(context.channel, "")
            logger.error(
                f"No channel handler for {context.channel}. "
                f"Available: {', '.join(self._by_name) or 'none'}.{hint}",
                conversation_id=context.conversation_id,
            )
            return False

        if not isinstance(response, str) and channel is not self.voice:
            response = "".join([chunk async for chunk in response])

        await channel.send_response(context.conversation_id, response, role=role)
        return True
