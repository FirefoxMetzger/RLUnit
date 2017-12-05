FROM firefoxmetzger/gym:latest
ENV PYTHONPATH=$PYTHONPATH:/usr/local/gym

# install python3.6
RUN 	apt update && \ 
	apt install -y python-software-properties software-properties-common && \
	add-apt-repository ppa:jonathonf/python-3.6 && \
	apt update && \
	apt install -y python3.6 python3.6-dev

# install easy_install and pip for python 3.6
# while at it install pip3, pip3.4 and pip3.6
RUN	curl https://bootstrap.pypa.io/ez_setup.py -o - | python3.6 && \
	python3.6 -m easy_install pip
	

# install dependancies
ADD distributor/Requirements.txt .
RUN pip3.6 install -r Requirements.txt && rm Requirements.txt


# The actual container files
WORKDIR /app
COPY ./distributor/ /app

ENTRYPOINT ["uwsgi", "--ini", "distributor.ini"]
