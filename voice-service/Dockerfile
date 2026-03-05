FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN python -c "\
from speechbrain.inference.speaker import EncoderClassifier; \
EncoderClassifier.from_hparams( \
    source='speechbrain/spkrec-ecapa-voxceleb', \
    savedir='/app/models/ecapa', \
    run_opts={'device': 'cpu'}, \
)"

ENV PYTHONUNBUFFERED=1
ENV OPENBLAS_NUM_THREADS=1
# No-AVX / cloud CPUs: avoid NNPACK init attempts and warning spam
ENV USE_NNPACK=0

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
