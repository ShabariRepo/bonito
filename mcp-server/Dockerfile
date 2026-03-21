FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .
EXPOSE 8080
CMD ["bonito-mcp", "--transport", "sse", "--port", "8080"]
