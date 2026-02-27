FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
ENV PATH="/uv/bin:${PATH}"

# Install python dependencies using uv
COPY requirements.txt .
RUN uv pip install --no-cache --system -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for PDFs
RUN mkdir -p tmp/pdfs

# Expose the port (HF Spaces defaults to 7860)
EXPOSE 7860

# Command to run the application
# We use uvicorn directly on main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
