"""OmniChannelFastAPIServer: FastAPI-based multi-channel TAC server.

Example:
    ```python
    from strands import Agent
    from tac import TAC, TACConfig
    from tac.channels import SMSChannel, VoiceChannel
    from tac_aws.adapters import StrandsAdapter
    from tac_aws.handlers import OmniChannelHandlers
    from tac_aws.servers import OmniChannelFastAPIServer

    tac = TAC(config=TACConfig.from_env())
    agent = Agent(model="gpt-4o")
    adapter = StrandsAdapter(agent)

    # Create handlers (manages conversation logic)
    handlers = OmniChannelHandlers(
        tac=tac,
        adapter=adapter,
        voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
        sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
    )

    # Create server (handles HTTP routing)
    server = OmniChannelFastAPIServer(handlers=handlers)
    server.start()
    ```

Requires: pip install tac-aws[server]
"""

from __future__ import annotations

import asyncio

from tac.core.logging import get_logger
from tac.server import FastAPIWebSocketAdapter, TACServerConfig

from tac_aws.handlers import OmniChannelHandlers

try:
    import uvicorn
    from fastapi import FastAPI, Form, Request, WebSocket
    from fastapi.responses import JSONResponse, Response
except ImportError as e:
    raise ImportError(
        "OmniChannelFastAPIServer requires FastAPI and uvicorn. "
        "Install with: pip install tac-aws[server]"
    ) from e

logger = get_logger(__name__)


class OmniChannelFastAPIServer:
    """FastAPI-based multi-channel TAC server.

    Provides HTTP routing for SMS, Voice, and Conversation Intelligence webhooks.
    Conversation management is handled by OmniChannelHandlers.

    Args:
        handlers: OmniChannelHandlers instance with TAC, adapter, and channels
        server_config: Optional TACServerConfig for server customization

    Example:
        ```python
        from tac import TAC, TACConfig
        from tac.channels import VoiceChannel, SMSChannel
        from tac_aws.adapters import StrandsAdapter
        from tac_aws.handlers import OmniChannelHandlers
        from strands import Agent

        tac = TAC(config=TACConfig.from_env())
        agent = Agent(model="gpt-4o")
        adapter = StrandsAdapter(agent)

        # Create handlers (manages conversation logic)
        handlers = OmniChannelHandlers(
            tac=tac,
            adapter=adapter,
            voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
            sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
        )

        # Create server (handles HTTP routing)
        server = OmniChannelFastAPIServer(handlers=handlers)
        server.start()
        ```
    """

    def __init__(
        self,
        handlers: OmniChannelHandlers,
        server_config: TACServerConfig | None = None,
    ) -> None:
        # Store handlers (contains TAC, adapter, channels, and conversation logic)
        self.handlers = handlers
        self.config = server_config or TACServerConfig.from_env()

        # Convenience accessors
        self.tac = self.handlers.tac
        self.adapter = self.handlers.adapter
        self.voice_channel = self.handlers.voice
        self.sms_channel = self.handlers.sms

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application with routes."""
        app = FastAPI(title="OmniChannel TAC Server")
        config = self.config

        if self.sms_channel is not None:
            sms = self.sms_channel

            @app.post(config.sms_webhook_path)
            async def sms_webhook(request: Request) -> JSONResponse:
                """Handle incoming SMS webhooks from Twilio."""
                try:
                    form_data = await request.json()
                    webhook_data = dict(form_data)
                    idempotency_token = request.headers.get("i-twilio-idempotency-token")
                    asyncio.create_task(sms.process_webhook(webhook_data, idempotency_token))
                    return JSONResponse(content={"status": "ok"}, status_code=200)
                except Exception as e:
                    logger.error("SMS webhook error", error=str(e), exc_info=True)
                    return JSONResponse(
                        content={"status": "error", "message": str(e)}, status_code=400
                    )

        if self.voice_channel is not None:
            vc = self.voice_channel

            if not config.public_domain:
                logger.warning(
                    "public_domain is not set — voice URLs will be malformed. "
                    "Set TWILIO_TAC_VOICE_PUBLIC_DOMAIN environment variable."
                )

            @app.post(config.twiml_path)
            async def post_twiml(
                From: str = Form(...),  # noqa: N803
                To: str = Form(...),  # noqa: N803
                CallSid: str = Form(...),  # noqa: N803
            ) -> Response:
                """Generate TwiML for incoming voice calls."""
                websocket_url = f"wss://{config.public_domain}{config.websocket_path}"
                callback_url = (
                    f"https://{config.public_domain}{config.conversation_relay_callback_path}"
                )

                twiml = await vc.handle_incoming_call(
                    to_number=To,
                    from_number=From,
                    options={
                        "websocket_url": websocket_url,
                        "action_url": callback_url,
                        "welcome_greeting": config.welcome_greeting,
                    },
                    call_sid=CallSid,
                )
                return Response(content=twiml, media_type="application/xml")

            @app.websocket(config.websocket_path)
            async def websocket_endpoint(websocket: WebSocket) -> None:
                """Handle voice WebSocket connections."""
                adapter = FastAPIWebSocketAdapter(websocket)
                await vc.handle_websocket(adapter)

            @app.post(config.conversation_relay_callback_path)
            async def conversation_relay_callback(request: Request) -> Response:
                """Handle ConversationRelay callback webhook from Twilio."""
                form_data = await request.form()
                payload_dict = {key: str(value) for key, value in form_data.items()}
                try:
                    result = await vc.handle_conversation_relay_callback(payload_dict)
                    if result is not None:
                        return Response(content=result, media_type="text/xml")
                    return Response(content="OK", media_type="text/plain")
                except Exception as e:
                    logger.error("Callback error", error=str(e), exc_info=True)
                    return Response(content=str(e), media_type="text/plain", status_code=500)

        if config.cintel_webhook_path is not None:
            tac = self.tac

            @app.post(config.cintel_webhook_path)
            async def cintel_webhook(request: Request) -> JSONResponse:
                """Handle Conversation Intelligence webhook events."""
                payload = await request.json()
                result = await tac.process_cintel_event(payload)
                return JSONResponse(content=result.model_dump())

        return app

    def start(self) -> None:
        """Create the FastAPI app and start uvicorn."""
        logger.info(
            f"Starting OmniChannelFastAPIServer on {self.config.host}:{self.config.port}",
            channels=[
                "voice" if self.voice_channel else None,
                "sms" if self.sms_channel else None,
            ],
        )

        app = self._create_app()
        uvicorn.run(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            access_log=False,  # Disable verbose HTTP request logs
        )
