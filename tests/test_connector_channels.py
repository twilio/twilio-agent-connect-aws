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


class TestChannelCreation:
    """Which channels get created, and which stay off."""

    def test_voice_and_sms_always_created_others_opt_in(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac)

        assert channels.voice is channel_classes["VoiceChannel"].return_value
        assert channels.sms is channel_classes["SMSChannel"].return_value
        assert channels.rcs is None
        assert channels.whatsapp is None
        assert channels.chat is None
        assert channels.messaging == [channels.sms]
        channel_classes["RCSChannel"].assert_not_called()
        channel_classes["WhatsAppChannel"].assert_not_called()
        channel_classes["ChatChannel"].assert_not_called()

    def test_empty_dict_enables_a_channel(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac, rcs_config={})

        channel_classes["RCSChannel"].assert_called_once_with(tac=mock_tac, config={})
        assert channels.rcs is channel_classes["RCSChannel"].return_value

    def test_all_channels_enabled(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(
            mock_tac,
            rcs_config={},
            whatsapp_config={},
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
            mock_tac,
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
        channels = ConnectorChannels(mock_tac, rcs_config={}, whatsapp_config={}, chat_config={})
        for name in ("voice", "sms", "rcs", "whatsapp", "chat"):
            getattr(channels, name).send_response = AsyncMock()

        assert await channels.send(_session(channel_name), "Hello") is True

        getattr(channels, attr).send_response.assert_awaited_once_with(
            "conv_1", "Hello", role="assistant"
        )
        for other in {"voice", "sms", "rcs", "whatsapp", "chat"} - {attr}:
            getattr(channels, other).send_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disabled_channel_drops_message(
        self, mock_tac: MagicMock, channel_classes: dict[str, MagicMock]
    ) -> None:
        channels = ConnectorChannels(mock_tac)  # WhatsApp not enabled
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
        channels = ConnectorChannels(mock_tac, whatsapp_config={})
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
            tac=mock_tac,
            agent_factory=mock_agent_factory,
            rcs_config={},
            whatsapp_config={},
            chat_config={},
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
        connector = StrandsConnector(
            tac=mock_tac, agent_factory=mock_agent_factory, whatsapp_config={}
        )
        connector.whatsapp.send_response = AsyncMock()

        await connector._handle_message("hi", _session("WHATSAPP"), None)

        connector.whatsapp.send_response.assert_awaited_once_with(
            "conv_1", "Test response", role="assistant"
        )
