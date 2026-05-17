from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import APIGateway, CloudFront, Route53
from diagrams.aws.compute import ECS, Lambda
from diagrams.aws.database import RDS, ElastiCache
from diagrams.aws.integration import SQS
from diagrams.aws.analytics import ManagedStreamingForKafka as MSK
from diagrams.aws.storage import S3
from diagrams.aws.security import Cognito
from diagrams.onprem.client import Users

graph_attr = {
    "fontsize": "20",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
}

with Diagram(
    "Order Service — AWS Container View",
    filename="out-aws",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    user = Users("Customer")

    with Cluster("Edge"):
        dns = Route53("DNS")
        cdn = CloudFront("Web App\n(React SPA)")

    with Cluster("API Layer"):
        api = APIGateway("API Gateway")
        auth = Cognito("Auth")

    with Cluster("Services (ECS Fargate)"):
        order = ECS("Order Service\n(Spring Boot)")
        notif = Lambda("Notification\nWorker")

    with Cluster("Data Layer"):
        cache = ElastiCache("Redis")
        db = RDS("PostgreSQL\n(Aurora)")
        bucket = S3("Invoices")

    with Cluster("Messaging"):
        kafka = MSK("Kafka")
        dlq = SQS("DLQ")

    user >> Edge(label="HTTPS") >> dns >> cdn >> api
    api >> Edge(label="verify") >> auth
    api >> Edge(label="REST") >> order
    order >> Edge(label="session") >> cache
    order >> Edge(label="persist") >> db
    order >> Edge(label="upload") >> bucket
    order >> Edge(label="OrderCreated") >> kafka
    kafka >> notif
    notif >> Edge(style="dashed", label="email/push") >> user
    notif >> Edge(style="dashed", color="red") >> dlq
