# pull official base image
FROM python:3.8
# set work directory
WORKDIR /usr/src
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBUG 1
ENV SECRET_KEY foo
ENV DJANGO_ALLOWED_HOSTS localhost 127.0.0.1 [::1]
ENV SQL_ENGINE django.db.backends.postgresql_psycopg2
ENV SQL_USER program
ENV SQL_PASSWORD test
ENV SQL_HOST postgres
ENV SQL_PORT 5432
# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
# copy project
COPY . .
EXPOSE 8060
COPY ./envdev.sh .
RUN chmod +x ./envdev.sh
CMD ["./envdev.sh"]