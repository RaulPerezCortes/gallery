FROM nginx:alpine

COPY index.html /usr/share/nginx/html/
COPY manifest.js /usr/share/nginx/html/
COPY favicon.ico /usr/share/nginx/html/
COPY media_web/ /usr/share/nginx/html/media_web/

EXPOSE 80
