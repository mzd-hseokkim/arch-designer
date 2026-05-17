from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.network import Nginx
from diagrams.onprem.compute import Server
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Rabbitmq
from diagrams.onprem.identity import Dex
from diagrams.onprem.monitoring import Grafana, Prometheus

graph_attr = {
    "fontsize": "20",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
    "rankdir": "LR",
}

with Diagram(
    "Order Service — On-Prem Deployment (Cold Standby DR)",
    filename="out-deployment-onprem",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    seller = Users("Seller\n(cutover only)")

    with Cluster("On-Prem Datacenter"):
        with Cluster("Edge"):
            nginx = Nginx("Nginx\n(TLS, reverse proxy)")
            keycloak = Dex("Keycloak\n(IdP, pre-provisioned)")

        with Cluster("App (docker-compose)"):
            api = Docker("api-gateway-svc")
            naver = Docker("naver-adapter")
            coupang = Docker("coupang-adapter")
            ownsite = Docker("ownsite-adapter")
            ingest = Docker("order-ingest")
            notif = Docker("notification-worker")

        with Cluster("Data"):
            db = PostgreSQL("PostgreSQL 15\n(logical replica of Aurora)")
            cache = Redis("Redis")

        with Cluster("Messaging"):
            mq = Rabbitmq("RabbitMQ\n(SQS replacement)")

        with Cluster("Ops"):
            prom = Prometheus("Prometheus")
            graf = Grafana("Grafana")

    seller >> Edge(style="dashed", label="DR cutover") >> nginx
    nginx >> api
    nginx >> keycloak

    naver >> mq
    coupang >> mq
    ownsite >> mq
    mq >> ingest
    ingest >> db
    ingest >> Edge(label="OrderCreated") >> notif
    api >> cache
    api >> db

    [api, ingest, notif] >> Edge(style="dotted") >> prom
    prom >> graf
