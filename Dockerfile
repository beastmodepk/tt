FROM images.paas.redhat.com/exd-sp-guild-source-compliance/scom-jenkins-agent-base
LABEL maintainer="Red Hat - Release automation"

WORKDIR /src

USER root

RUN dnf -y install \
    --setopt=deltarpm=0 \
    --setopt=install_weak_deps=false \
    --setopt=tsflags=nodocs \
    python3-pip \
    python3-devel \
    libpq-devel \
    krb5-workstation \
    krb5-devel \
    gcc \
    && dnf update -y \
    && dnf clean all

RUN update-alternatives --set python3 $(which python3.6)
RUN curl -s https://password.corp.redhat.com/RH-IT-Root-CA.crt \
    -o /etc/pki/ca-trust/source/anchors/RH-IT-Root-CA.crt \
    && update-ca-trust extract

RUN mkdir /etc/ipa && curl -o /etc/ipa/ca.crt https://password.corp.redhat.com/ipa.crt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN pip3 install . --no-deps