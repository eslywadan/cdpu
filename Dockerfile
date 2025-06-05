FROM python:3.9-buster
#FROM dataservice:latest
#FROM python:3.9-alpine
WORKDIR /app
ENV FLASK_APP=controller
ENV FLASK_RUN_HOST=0.0.0
ENV PYTHONPATH=/app
#RUN apk add --no-cache gcc musl-dev linux-headers
#RUN apk add build-base
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY ./dist/dsbase-250325.164719-py3-none-any.whl dist/dsbase-250325.164719-py3-none-any.whl
RUN pip install ./dist/dsbase-250325.164719-py3-none-any.whl
EXPOSE 8080
WORKDIR /app
#COPY . .

# During debugging, this entry point will be overridden. For more information, refer to https://aka.ms/vscode-docker-python-debug
# CMD

#CMD ["python"]