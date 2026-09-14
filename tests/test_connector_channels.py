"""Tests for ConnectorChannels — the channel set and routing shared by connectors."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tac_aws.connectors import StrandsConnector
from tac_aws.connectors.channels import ConnectorChannels

CHANNEL_PATCHES = (
    "VoiceChannel",
    "SMSChannel",
    "RCSChannel",
    "WhatsAppChannel",
    "ChatChannel",
)


@pytest.fixture
def channel_classes():
    """Patch every TAC channel class ConnectorChannels constructs.

    Stops only the patchers this fixture started — `patch.stopall()` would also
    stop patches owned by other fixtures, making the suite order-dependent.
    """
    patchers = {name: patch(f"tac_aws.connectors.channels.{name}") for name in CHANNEL_PATCHES}
    mocks = {name: patcher.start() for name, patcher in patchers.items()}
    yield mocks
    for patcher in patchers.values():
        patcher.stop()


def _session(channel: str) -> MagicMock:
    session = MagicMock()
    session.conversation_id = "conv_1"
    session.channel = channel
    return session


def _with_senders(tac: MagicMock) -> MagicMock:
    """Configure both sender-gated channels on a mock TAC."""
    tac.config.rcs_sender_id = "rcs_sender_123"
    tac.config.whatsapp_number = "whatsapp:+15551234567"
    return tac


class TestChannelCreation:
    """Which channels get created, and which stay off."""

    def test_voice_sms_and_chat_always_created(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac)

        assert channels.voice is channel_classes["VoiceChannel"].return_value
        assert channels.sms is channel_classes["SMSChannel"].return_value
        assert channels.chat is channel_classes["ChatChannel"].return_value
        assert channels.messaging == [channels.sms, channels.chat]

    def test_sender_gated_channels_off_without_a_sender(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac)

        assert channels.rcs is None
        assert channels.whatsapp is None
        channel_classes["RCSChannel"].assert_not_called()
        channel_classes["WhatsAppChannel"].assert_not_called()

    def test_configured_sender_enables_the_channel(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        mock_tac.config.rcs_sender_id = "rcs_sender_123"

        channels = ConnectorChannels(mock_tac)

        channel_classes["RCSChannel"].assert_called_once_with(tac=mock_tac, config=None)
        assert channels.rcs is channel_classes["RCSChannel"].return_value
        assert channels.whatsapp is None

    def test_config_alone_does_not_enable_a_channel(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        """`*_config` is tuning only — without a sender the channel stays off."""
        channels = ConnectorChannels(mock_tac, whatsapp_config={"memory_mode": "never"})

        assert channels.whatsapp is None
        channel_classes["WhatsAppChannel"].assert_not_called()

    def test_all_channels_available(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(
            _with_senders(mock_tac),
            chat_config={"agent_address": "ai-assistant"},
        )

        assert channels.messaging == [
            channels.sms,
            channels.rcs,
            channels.whatsapp,
            channels.chat,
        ]
        for name in ("VOICE", "SMS", "RCS", "WHATSAPP", "CHAT"):
            assert channels.get(name) is not None

    def test_configs_forwarded_to_each_channel(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        ConnectorChannels(
            _with_senders(mock_tac),
            voice_config={"memory_mode": "once"},
            sms_config={"memory_mode": "always"},
            whatsapp_config={"memory_mode": "never"},
        )

        channel_classes["VoiceChannel"].assert_called_once_with(
            tac=mock_tac, config={"memory_mode": "once"}
        )
        channel_classes["WhatsAppChannel"].assert_called_once_with(
            tac=mock_tac, config={"memory_mode": "never"}
        )


class TestRouting:
    """send() picks the channel matching ConversationSession.channel."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("channel_name", "attr"),
        [
            ("VOICE", "voice"),
            ("SMS", "sms"),
            ("RCS", "rcs"),
            ("WHATSAPP", "whatsapp"),
            ("CHAT", "chat"),
        ],
    )
    async def test_routes_to_matching_channel(
        self,
        mock_tac: MagicMock,
        channel_classes: dict[str, MagicMock],
        channel_name: str,
        attr: str,
    ) -> None:
        channels = ConnectorChannels(_with_senders(mock_tac))
        for name in ("voice", "sms", "rcs", "whatsapp", "chat"):
            getattr(channels, name).send_response = AsyncMock()

        assert await channels.send(_session(channel_name), "Hello") is True

        getattr(channels, attr).send_response.assert_awaited_once_with(
            "conv_1", "Hello", role="assistant"
        )
        for other in {"voice", "sms", "rcs", "whatsapp", "chat"} - {attr}:
            getattr(channels, other).send_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unavailable_channel_drops_message(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac)  # no WhatsApp number configured
        channels.sms.send_response = AsyncMock()
        channels.voice.send_response = AsyncMock()

        assert await channels.send(_session("WHATSAPP"), "Hello") is False

        channels.sms.send_response.assert_not_awaited()
        channels.voice.send_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stream_passes_through_to_voice(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac)
        channels.voice.send_response = AsyncMock()

        async def stream() -> AsyncGenerator[str, None]:
            yield "a"

        generator = stream()
        await channels.send(_session("VOICE"), generator)

        # Voice streams token by token — the generator itself is handed over
        channels.voice.send_response.assert_awaited_once_with("conv_1", generator, role="assistant")

    @pytest.mark.asyncio
    async def test_stream_is_buffered_for_messaging(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(_with_senders(mock_tac))
        channels.whatsapp.send_response = AsyncMock()

        async def stream() -> AsyncGenerator[str, None]:
            yield "Hello "
            yield "world"

        await channels.send(_session("WHATSAPP"), stream())

        # Messaging channels reject generators, so the stream is collected first
        channels.whatsapp.send_response.assert_awaited_once_with(
            "conv_1", "Hello world", role="assistant"
        )


class TestConnectorExposure:
    """Connectors surface the whole channel set."""

    def test_connector_exposes_every_channel(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        channel_classes: dict[str, MagicMock],
    ) -> None:
        connector = StrandsConnector(
            tac=_with_senders(mock_tac),
            agent_factory=mock_agent_factory,
        )

        assert connector.voice is connector.channels.voice
        assert connector.sms is connector.channels.sms
        assert connector.rcs is connector.channels.rcs
        assert connector.whatsapp is connector.channels.whatsapp
        assert connector.chat is connector.channels.chat
        assert len(connector.channels.messaging) == 4

    @pytest.mark.asyncio
    async def test_connector_routes_response_to_whatsapp(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        channel_classes: dict[str, MagicMock],
    ) -> None:
        connector = StrandsConnector(tac=_with_senders(mock_tac), agent_factory=mock_agent_factory)
        connector.whatsapp.send_response = AsyncMock()

        await connector._handle_message("hi", _session("WHATSAPP"), None)

        connector.whatsapp.send_response.assert_awaited_once_with(
            "conv_1", "Test response", role="assistant"
        )
