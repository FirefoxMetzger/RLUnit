FROM python:3.6

# install dependancies
ADD hub/Requirements.txt .
RUN pip install -r Requirements.txt && rm Requirements.txt


# The actual container files
WORKDIR /app
COPY ./hub /app

ENTRYPOINT ["uwsgi", "--ini", "hub.ini"]
