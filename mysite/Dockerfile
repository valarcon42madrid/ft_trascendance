# pull official base image
FROM python:3.11.4-slim-buster

# set work directory
WORKDIR /usr/src/mysite

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update && apt-get install -y netcat

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
# creo que no hace falta. Relacionado con Blockchain.
# RUN pip install --upgrade web3
# RUN pip install cryptography
# RUN pip installpyOpenSSL

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /usr/src/mysite/entrypoint.sh
RUN chmod +x /usr/src/mysite/entrypoint.sh

# copy project
COPY . .

# run entrypoint.sh
ENTRYPOINT ["/usr/src/mysite/entrypoint.sh"]
