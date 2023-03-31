FROM python:3.10

RUN apt-get update -y \
    && apt install 'ffmpeg' 'libffi-dev' 'libnacl-dev' 'python3-dev' -y \
    && apt-get clean


WORKDIR .

ADD /requirements.txt /

RUN pip3 install -r /requirements.txt
RUN pip3 install vkwave
RUN pip3 install --upgrade typing_extensions==4.5.0
ADD . .
