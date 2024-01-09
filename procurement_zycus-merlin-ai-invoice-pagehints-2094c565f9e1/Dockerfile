FROM ubuntu:18.04
RUN apt-get update && apt-get upgrade -y && apt-get -y install g++ curl vim wget unzip
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN apt-get install poppler-utils -y

RUN curl -LO "http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh"
RUN bash Miniconda3-latest-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda3-latest-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda

# RUN apt-get update && \
#     apt-get install -y --no-install-recommends linux-perf && \
#     ln -s /usr/bin/perf_* /usr/bin/perf && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ./ ./
# RUN mkdir -p /models/Merlin-AI-Invoice-PageHints/models/
# RUN wget http://192.168.1.215:8081/nexus/repository/zycus.docket/models/Merlin-AI-Invoice-PageHints/model_PageHints/v4.5/model_PageHints-v4.5.zip -P /models/Merlin-AI-Invoice-PageHints/models/
# RUN unzip -o /models/Merlin-AI-Invoice-PageHints/models/model_PageHints-v4.5.zip -d /models/Merlin-AI-Invoice-PageHints/models/
WORKDIR /app
RUN conda env create -f /code/environment.yml && conda clean -afy 
ENV PYTHONUNBUFFERED=1
ENV PATH=/miniconda/bin:$PATH
ENV PATH /miniconda/envs/env_cascade_tabnet/bin:$PATH
RUN chmod +x /templates/setup.sh
RUN /templates/setup.sh
RUN /miniconda/bin/activate env_cascade_tabnet
RUN chmod +x /templates/run.sh
CMD ["/templates/run.sh"]


