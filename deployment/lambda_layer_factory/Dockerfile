FROM public.ecr.aws/amazonlinux/amazonlinux

WORKDIR /
RUN yum update -y
RUN yum install gcc gcc-c++ openssl-devel bzip2-devel libffi-devel wget tar gzip zip make -y

# Install Python 3.9
WORKDIR /
RUN wget https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz
RUN tar -xzf Python-3.9.0.tgz
WORKDIR /Python-3.9.0
RUN ./configure --enable-optimizations
RUN make install

# Install Python packages and build zip files at runtime
WORKDIR /
RUN mkdir -p /packages/lambda_layer-python-3.9/python/lib/python3.9/site-packages
COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
