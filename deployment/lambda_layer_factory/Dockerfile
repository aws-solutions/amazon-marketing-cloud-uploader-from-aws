FROM public.ecr.aws/amazonlinux/amazonlinux

WORKDIR /
RUN yum update -y
RUN yum install gcc gcc-c++ openssl-devel bzip2-devel libffi-devel wget tar gzip zip make zlib-devel -y

# Install Python 3.12
WORKDIR /
RUN wget https://www.python.org/ftp/python/3.12.2/Python-3.12.2.tgz
RUN tar -xzf Python-3.12.2.tgz
WORKDIR /Python-3.12.2
RUN ./configure --enable-optimizations
RUN make install

# Install Python packages and build zip files at runtime
WORKDIR /
RUN mkdir -p /packages/lambda_layer-python-3.12/python/lib/python3.12/site-packages
COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
