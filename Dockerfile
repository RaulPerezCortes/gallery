FROM nginx:alpine

# Copiamos los archivos estáticos de la galería al directorio que sirve nginx
COPY index.html /usr/share/nginx/html/
COPY manifest.js /usr/share/nginx/html/
COPY media_web/ /usr/share/nginx/html/media_web/

EXPOSE 80
