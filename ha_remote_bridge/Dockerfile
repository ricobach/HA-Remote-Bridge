FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

RUN apk add --no-cache \
    python3 \
    py3-aiohttp \
    py3-zeroconf \
    openssh-client-default \
    openssh-keygen \
    ttyd \
    tmux \
    novnc \
    samba-client

COPY run.sh /run.sh
COPY app /app
RUN chmod a+x /run.sh

WORKDIR /app

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

CMD ["/run.sh"]
