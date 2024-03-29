FROM base-web

# pre-create directories
RUN set -ex; mkdir -p \
  mtp_emails/assets \
  mtp_emails/assets-static \
  static \
  media \
  spooler \
  reports

# cache python packages, unless requirements change
COPY ./requirements requirements
RUN venv/bin/pip install -r requirements/base.txt

# add app and build it
COPY . /app
RUN set -ex; \
  venv/bin/python run.py --requirements-file requirements/base.txt build \
  && \
  chown -R mtp:mtp /app
USER 1000

ARG APP_GIT_COMMIT
ARG APP_GIT_BRANCH
ARG APP_BUILD_TAG
ARG APP_BUILD_DATE
ENV APP_GIT_COMMIT ${APP_GIT_COMMIT}
ENV APP_GIT_BRANCH ${APP_GIT_BRANCH}
ENV APP_BUILD_TAG ${APP_BUILD_TAG}
ENV APP_BUILD_DATE ${APP_BUILD_DATE}

# run uwsgi on 8080
EXPOSE 8080
ENV DJANGO_SETTINGS_MODULE=mtp_emails.settings.docker
CMD venv/bin/uwsgi --ini emails.ini
