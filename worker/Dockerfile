FROM firefoxmetzger/gym:latest
ENV PYTHONPATH=$PYTHONPATH:/usr/local/gym

# install python3.6
RUN 	apt update && \ 
	apt install -y python-software-properties software-properties-common && \
	add-apt-repository ppa:jonathonf/python-3.6 && \
	apt update && \
	apt install -y python3.6

# install easy_install and pip for python 3.6
RUN	curl https://bootstrap.pypa.io/ez_setup.py -o - | python3.6 && \
	python3.6 -m easy_install pip

# external dependancies
WORKDIR /app
COPY worker/Requirements.txt /app
RUN pip3.6 install -r Requirements.txt && rm Requirements.txt

COPY worker/worker.py /app
CMD ["python3.6", "worker.py"]
