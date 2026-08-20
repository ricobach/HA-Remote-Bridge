FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-aiohttp

COPY run.sh /run.sh
COPY app /app
RUN chmod a+x /run.sh

WORKDIR /app

LABEL io.hass.type="app"

CMD ["/run.sh"]
