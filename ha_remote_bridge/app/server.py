"""HA Remote Bridge server launcher with Ingress-friendly header limits."""

from aiohttp import web

from main import LOGGER, PORT, create_app


async def _run() -> None:
    """Run the app with larger header limits for Home Assistant Ingress traffic."""
    app = create_app()
    runner = web.AppRunner(
        app,
        access_log=LOGGER,
        max_line_size=64 * 1024,
        max_field_size=64 * 1024,
        max_headers=128 * 1024,
    )
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    # Keep the process alive until it is terminated by Supervisor/s6.
    import asyncio

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_run())
