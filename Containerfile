# NPM stage
FROM docker.io/library/node:18-bullseye-slim as stagenpm

WORKDIR /stagenpm

COPY ./package-lock.json ./package.json ./
RUN npm install
COPY ./frontend ./frontend
RUN mkdir -p /stagenpm/dlcdb/static/dist
RUN npm run prod


# Django app stage
#FROM docker.io/library/debian:bullseye-slim as djangostage
FROM docker.io/library/python:3.9-bullseye as stagedjango

WORKDIR /stagepython

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system packages required by Wagtail and Django.
RUN apt-get update --yes --quiet \
    && apt-get install --yes --quiet --no-install-recommends \
      # python3 python3-venv python3-dev \
      libldap2-dev libsasl2-dev gcc \
      libmagic1 \
      make \
      # apache2 libapache2-mod-wsgi-py3 \
      # npm \
    && rm -rf /var/lib/apt/lists/*

# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
COPY requirements.txt /stagepython/
RUN pip install --no-cache-dir -r requirements.txt

COPY docs docs
RUN cd ./docs/ && make html && cd ../

# Prepare apache
FROM httpd:bullseye as apachestage
# COPY ./Containerfiles/apache-vhost-dlcdb.conf /etc/apache/sites-enabled/000-default.conf
# COPY ./Containerfiles/httpd-foreground /usr/local/bin/
# RUN a2enmod wsgi
# EXPOSE 80

WORKDIR /app


COPY ./Containerfiles/entrypoint.sh ./Containerfiles/entrypoint.sh
COPY . /app/
COPY ./Containerfiles/env.production /app/.env

# copy npm generated assets
COPY --from=stagenpm /stagenpm/dlcdb/static/dist /app/dlcdb/static/dist

# copy prepared venv
COPY --from=stagepython /opt/venv /app/venv
COPY --from=stagepython /stagepython/docs /app/docs

ENTRYPOINT ["./Containerfiles/entrypoint.sh"]

# CMD ["curl", "http://127.0.0.1:8000/"]
CMD [ "python3", "./manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["httpd-foreground"]
