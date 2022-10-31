# NPM stage
FROM docker.io/library/node:18-bullseye-slim AS stagenpm

WORKDIR /stagenpm

COPY ./package-lock.json ./package.json ./
RUN npm install
COPY ./frontend ./frontend
RUN mkdir -p /stagenpm/dlcdb/static/dist
RUN npm run prod


# Django app stage
#FROM docker.io/library/debian:bullseye-slim as djangostage
#FROM docker.io/library/python:3.9-bullseye as stagepython
FROM docker.io/library/debian:bullseye-slim AS stagepython

WORKDIR /stagepython

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system packages required by Wagtail and Django.
RUN apt-get update --yes --quiet \
    && apt-get install --yes --quiet --no-install-recommends \
      python3 python3-venv python3-dev \
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
# FROM docker.io/library/httpd:bullseye as apachestage
# FROM docker.io/library/debian:bullseye-slim as apachestage
FROM docker.io/library/debian:bullseye-slim AS apachestage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update --yes --quiet \
    && apt-get install --yes --quiet --no-install-recommends \
      tree \
      bash \
      libmagic1 \
      python3-minimal \
      apache2 libapache2-mod-wsgi-py3 \
    && rm -rf /var/lib/apt/lists/*

# RUN a2enmod wsgi  # already enabled during installation of libapache2-mod-wsgi-py3

COPY Containerfiles/entrypoint.sh Containerfiles/entrypoint.sh
COPY . /app/
COPY ./Containerfiles/env.production /app/.env
COPY ./Containerfiles/apache-vhost-dlcdb.conf /etc/apache2/sites-enabled/000-default.conf

# copy npm generated assets
COPY --from=stagenpm /stagenpm/dlcdb/static/dist /app/dlcdb/static/dist

# copy prepared venv
COPY --from=stagepython /opt/venv /opt/venv
COPY --from=stagepython /stagepython/docs /app/docs

ENTRYPOINT ["Containerfiles/entrypoint.sh"]

# CMD [ "python3", "./manage.py", "runserver", "0.0.0.0:8000"]
CMD ["/usr/sbin/apachectl", "-D", "FOREGROUND"]
