# certs

Server certificates for a private, self-signed `CLUSTER_BASE_URL`.

Drop the certificate here and point the backend at the mounted path:

    CLUSTER_CA_BUNDLE=/certs/cluster_ca.pem

The directory is mounted read-only into the backend container
(`./certs:/certs:ro`, see `docker-compose.yml`). Fetch a certificate with:

    python -c "import ssl; print(ssl.get_server_certificate(('HOST', PORT)))"

A server certificate is public information, but it is not tracked here by
default so nobody checks in the wrong file by accident.
