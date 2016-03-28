FROM python:2-onbuild

ADD . .

EXPOSE 8080

CMD ["python", "-u", "server.py", "--logging", "debug"]
