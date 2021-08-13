# Base python image Build
FROM python:3.8-buster


RUN git clone https://github.com/eubinecto/wisdomify
WORKDIR /wisdomify
RUN git checkout feature_52
RUN pip install --upgrade pip
#RUN pip install -r requirements.txt

RUN pip install 'dvc[gdrive]'
RUN ls -al
RUN dvc pull

#RUN mkdir ./data
#RUN mkdir ./data/lightning_logs

#RUN curl -L -sS https://www.dropbox.com/s/dl/tw491n5dnk8195c/version_0.zip > ./version_0.zip
#RUN unzip ./version_0.zip -d ./data/lightning_logs/
#RUN rm ./version_0.zip
#
#RUN curl -L -sS https://www.dropbox.com/s/9xea2ia1r0u0c1a/version_1.zip?dl=1 > ./version_1.zip
#RUN unzip ./version_1.zip -d ./data/lightning_logs/
#RUN rm ./version_1.zip

# Deploy
EXPOSE 5000
CMD ["python", "-m", "wisdomify.main.deploy"]