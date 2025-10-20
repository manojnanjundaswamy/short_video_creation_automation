FROM node:20-bullseye

ENV N8N_VERSION=1.24.0
ENV PYTHONUNBUFFERED=1

# Miniconda installation directory and environment name
ENV CONDA_DIR=/root/miniconda3
ENV CONDA_ENV_NAME=cosyvoice
ENV PATH="$CONDA_DIR/envs/$CONDA_ENV_NAME/bin:$CONDA_DIR/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    ffmpeg \
    pkg-config \
    build-essential \
    git \
    bash \
    curl \
    wget \
    libffi-dev \
    libssl-dev \
    imagemagick \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    fontconfig \
    fonts-dejavu \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda silently
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-py39_25.5.1-1-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p $CONDA_DIR && \
    rm /tmp/miniconda.sh

# Initialize conda for bash shell (enables 'conda activate' in RUN commands)
RUN $CONDA_DIR/bin/conda init bash

# Create and set up the Conda environment with Python 3.10 and install all packages including CosyVoice and your python dependencies
RUN /root/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    /root/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    bash -c " \
    source /root/miniconda3/etc/profile.d/conda.sh && \
    conda create -n cosyvoice python=3.10 -y && \
    conda activate cosyvoice && \
    pip install --upgrade pip setuptools wheel 'cython<3.0' && \
    pip install requests moviepy==1.0.3 python-dotenv tqdm gtts pydub pillow==9.5.0 ffmpeg-python imagehash google-api-python-client google-auth-oauthlib opencv-python-headless numpy psutil && \
    git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git /opt/CosyVoice && \
    cd /opt/CosyVoice && \
    git submodule update --init --recursive && \
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com \
"
RUN PIP_USE_PEP517=0 pip install --no-cache-dir "av==10.0.0"
RUN pip install --no-cache-dir faster-whisper==0.7.0

# Install n8n globally with npm
RUN npm install -g n8n@$N8N_VERSION

WORKDIR /home/node

EXPOSE 5678

# Default command to start n8n
CMD ["n8n", "start"]
