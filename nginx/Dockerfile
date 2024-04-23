FROM nginx:1.19.0-alpine

RUN rm /etc/nginx/conf.d/default.conf
EXPOSE 443 80 8080
COPY nginx.conf /etc/nginx/conf.d
COPY nginx.conf /etc/nginx/conf
COPY certs/ft_transcendence.com.pem /etc/nginx/certs/
COPY certs/ft_transcendence.com-key.pem /etc/nginx/certs/
