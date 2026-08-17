FROM python:3.11-slim

LABEL description="LEGACY-CONTRACT Research Platform"
LABEL version="0.1.0"

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gnucobol \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Verify GnuCOBOL version
RUN cobc --version | head -1

# Install Poetry
RUN pip install poetry==1.7.1

WORKDIR /workspace

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy source
COPY . .

# Set Python path
ENV PYTHONPATH=/workspace/src

# Default: run all Paper 1 experiments
CMD ["make", "reproduce-paper1"]
