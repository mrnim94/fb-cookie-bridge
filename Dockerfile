FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
ENV FBCB_HOST=0.0.0.0 FBCB_PORT=8899 FBCB_COOKIE_FILE=/run/secrets/facebook_cookies.json
EXPOSE 8899
USER nobody
ENTRYPOINT ["fb-cookie-bridge"]
