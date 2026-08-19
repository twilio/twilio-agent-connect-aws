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


class ConnectorChannels:
    """The TAC channels a connector owns, and the routing between them.

    Voice and SMS are always created. RCS, WhatsApp, and Chat are created only
    when you pass their config, because each needs something extra that the
    channel constructor requires up front — `TWILIO_RCS_SENDER_ID` for RCS,
    `TWILIO_WHATSAPP_NUMBER` for WhatsApp, and an agent identity for Chat.
    Pass an empty dict (`rcs_config={}`) to enable one with default settings.

    Attributes:
        voice: `VoiceChannel` for voice conversations
        sms: `SMSChannel` for SMS conversations
        rcs: `RCSChannel`, or None when `rcs_config` was not given
        whatsapp: `WhatsAppChannel`, or None when `whatsapp_config` was not given
        chat: `ChatChannel`, or None when `chat_config` was not given
        messaging: Every enabled messaging channel, ready to hand to a server as
            `messaging_channels=...`

    Example:
        ```python
        connector = StrandsConnector(
            tac=tac,
            agent_factory=create_agent,
            sms_config=SMSChannelConfig(memory_mode="always"),
            whatsapp_config={},  # enable WhatsApp with defaults
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
        self.rcs = RCSChannel(tac=tac, config=rcs_config) if rcs_config is not None else None
        self.whatsapp = (
            WhatsAppChannel(tac=tac, config=whatsapp_config)
            if whatsapp_config is not None
            else None
        )
        self.chat = ChatChannel(tac=tac, config=chat_config) if chat_config is not None else None

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

        logger.debug(f"Channels enabled: {', '.join(self._by_name)}")

    def get(self, channel_name: str) -> BaseChannel | None:
        """The enabled channel with this TAC channel name, or None."""
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
            True if a channel handled it; False when no channel is enabled for
            `context.channel` (logged as an error — the message is dropped).
        """
        channel = self.get(context.channel)
        if channel is None:
            logger.error(
                f"No channel handler for {context.channel}. "
                f"Enabled: {', '.join(self._by_name) or 'none'}",
                conversation_id=context.conversation_id,
            )
            return False

        if not isinstance(response, str) and channel is not self.voice:
            response = "".join([chunk async for chunk in response])

        await channel.send_response(context.conversation_id, response, role=role)
        return True
