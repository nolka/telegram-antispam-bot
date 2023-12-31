FROM python:3.11-alpine

ENV TELEGRAM_BOT_USERNAME=pd_antispam_bot
ENV TELEGRAM_BOT_TOKEN=
ENV PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER=
ENV METRICS_PORT=9090
ENV METRICS_HOST=0.0.0.0

COPY . /app

WORKDIR /app

RUN rm -fr storage && \
    rm -fr venv && \
    if [ -f .env ]; then \
    rm .env; \
    fi
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./main.py" ]
