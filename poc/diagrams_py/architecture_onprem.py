from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.network import Nginx, Haproxy
from diagrams.onprem.compute import Server
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Kafka
from diagrams.onprem.storage import Ceph
from diagrams.onprem.identity import Dex

graph_attr = {
    "fontsize": "20",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
}

with Diagram(
    "Order Service — On-Prem Container View",
    filename="out-onprem",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    user = Users("Customer")

    with Cluster("Edge / DMZ"):
        lb = Haproxy("Load Balancer")
        web = Nginx("Web App\n(React SPA static)")

    with Cluster("API Layer"):
        gw = Nginx("API Gateway")
        auth = Dex("Auth (OIDC)")

    with Cluster("Application (Docker Hosts)"):
        order = Docker("Order Service\n(Spring Boot)")
        notif = Server("Notification\nWorker")

    with Cluster("Data Layer"):
        cache = Redis("Redis")
        db = PostgreSQL("PostgreSQL\n(Primary + Replica)")
        store = Ceph("Object Storage\n(MinIO)")

    with Cluster("Messaging"):
        kafka = Kafka("Kafka")

    user >> Edge(label="HTTPS") >> lb
    lb >> web
    lb >> gw
    gw >> Edge(label="verify") >> auth
    gw >> Edge(label="REST") >> order
    order >> Edge(label="session") >> cache
    order >> Edge(label="persist") >> db
    order >> Edge(label="upload") >> store
    order >> Edge(label="OrderCreated") >> kafka
    kafka >> notif
    notif >> Edge(style="dashed", label="email/push") >> user
