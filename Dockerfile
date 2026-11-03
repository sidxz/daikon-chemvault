# Build stage: pipenv installs the locked dependencies into /project/.venv. Neither pipenv nor pip
# reaches the runtime image: nothing installs packages at runtime, and both carry vendored copies of
# urllib3, msgpack and setuptools that image scans flag. Nothing in the lock needs a compiler.
FROM python:3.12-slim AS build

WORKDIR /project
ENV PIPENV_VENV_IN_PROJECT=1

RUN pip install --no-cache-dir pipenv
COPY Pipfile Pipfile.lock ./
# PaDEL-Descriptor (Java, with old guava and log4j jars) comes in through admet_ai's dependencies
# (astartes, aimsim_core, padelpy); the image has no Java and chemvault never calls it.
RUN pipenv install --deploy \
    && .venv/bin/python -m pip uninstall -y pip \
    && rm -rf .venv/lib/python3.12/site-packages/padelpy/PaDEL-Descriptor

FROM python:3.12-slim

WORKDIR /project
ENV PATH=/project/.venv/bin:$PATH

# libxrender1/libxext6 for RDKit drawing; postgresql-client for pg_isready and psql in docker-entrypoint.sh
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    libxrender1 \
    libxext6 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /project/.venv .venv
COPY . .
RUN chmod +x docker-entrypoint.sh

EXPOSE 10001

ENTRYPOINT ["/project/docker-entrypoint.sh"]
