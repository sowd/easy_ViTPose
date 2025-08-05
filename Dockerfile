ARG BASE_IMAGE=nvidia/cuda:12.8.0-cudnn-devel-ubuntu24.04
#ARG BASE_IMAGE=nvidia/cuda:12.5.1-base-ubuntu24.04

FROM ${BASE_IMAGE}

ARG NORMAL_USER=hoikutech

USER root

ENV DEBIAN_FRONTEND noninteractive

ENV NB_USER $NORMAL_USER

ENV NB_UID 1000
ENV HOME /home/$NB_USER
ENV NB_PREFIX /

# Use bash instead of sh
SHELL ["/bin/bash", "-c"]

WORKDIR $HOME

RUN apt-get update

# Install exactly python 3.10
#RUN apt-get update
#RUN apt-get install -y curl python3-pip python3-venv python3-numpy python3-opencv python3-onnx

RUN apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.10 python3.10-venv python3.10-dev python3.10-distutils \
    curl build-essential && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
# pip を Python 3.10 用にインストール
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3


##################
## Install easy_ViTPose
## https://github.com/JunkyByte/easy_ViTPose
##################
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
RUN apt install -y git cmake
RUN git clone https://github.com/sowd/easy_ViTPose.git
WORKDIR easy_ViTPose
RUN pip install -e .
RUN pip install -r requirements.txt

#COPY vitpose-b-multi-coco.pth /home/$NB_USER/vitpose-b-multi-coco.pth
#COPY vitpose-s-wholebody.pth /home/$NB_USER/vitpose-s-wholebody.pth
COPY vitpose-s-wholebody.pth .

WORKDIR models
RUN bash ./download.sh
#COPY vitpose-l-ap10k.onnx /home/$NB_USER/
#COPY vyolov8l.pt /home/$NB_USER/

WORKDIR /home/$NB_USER/easy_ViTPose

CMD ["python3", "apiserver.py"]
