from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import CloudFront, Route53, ALB, NATGateway, VPC
from diagrams.aws.compute import ECS, Fargate
from diagrams.aws.database import RDSInstance
from diagrams.aws.storage import S3
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.security import Cognito, SecretsManager, KMS
from diagrams.aws.management import Cloudwatch
from diagrams.aws.devtools import Codebuild
from diagrams.aws.engagement import SimpleEmailServiceSes  # placeholder; SNS Mobile
from diagrams.onprem.client import Users
from diagrams.onprem.vcs import Github

graph_attr = {
    "fontsize": "20",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
    "rankdir": "LR",
}

with Diagram(
    "Order Service — AWS Deployment (ap-northeast-2, Multi-AZ)",
    filename="out-deployment-aws",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    seller = Users("Seller\n(web/mobile)")
    gh = Github("GitHub Actions")

    with Cluster("ap-northeast-2"):
        dns = Route53("DNS")
        cdn = CloudFront("CloudFront\n+ S3 (SPA)")
        cognito = Cognito("User Pool\n(MFA, RBAC)")

        with Cluster("VPC"):
            with Cluster("Public Subnets (3 AZ)"):
                alb = ALB("ALB")
                nat = NATGateway("NAT")

            with Cluster("Private Subnets (3 AZ) — ECS Fargate"):
                api = Fargate("api-gateway-svc")
                with Cluster("Channel Adapters"):
                    naver = Fargate("naver-adapter")
                    coupang = Fargate("coupang-adapter")
                    ownsite = Fargate("ownsite-adapter")
                ingest = Fargate("order-ingest")
                notif = Fargate("notification-worker")

            with Cluster("Isolated Subnets (Multi-AZ)"):
                db = RDSInstance("Aurora PG\nServerless v2")
                cache = RDSInstance("ElastiCache\nRedis")

        with Cluster("Messaging"):
            q1 = SQS("sqs-naver")
            q2 = SQS("sqs-coupang")
            q3 = SQS("sqs-ownsite")
            dlq = SQS("sqs-dlq")
            push = SNS("SNS Mobile\nPush → FCM")

        with Cluster("Cross-cutting"):
            cw = Cloudwatch("CloudWatch\n+ Container Insights")
            sm = SecretsManager("Secrets Manager")
            kms = KMS("KMS")
            export_s3 = S3("Exports (KMS)")

    seller >> Edge(label="HTTPS") >> dns >> cdn
    cdn >> Edge(label="/api") >> alb >> api
    api >> Edge(label="verify") >> cognito
    api >> cache
    api >> db
    api >> export_s3

    naver >> q1
    coupang >> q2
    ownsite >> q3
    [q1, q2, q3] >> ingest
    ingest >> Edge(style="dashed", color="red") >> dlq
    ingest >> db
    ingest >> Edge(label="OrderCreated") >> notif
    notif >> push
    push >> Edge(style="dashed", label="push") >> seller

    naver >> Edge(style="dashed") >> nat
    coupang >> Edge(style="dashed") >> nat
    ownsite >> Edge(style="dashed") >> nat

    gh >> Edge(style="dashed", label="deploy") >> [api, ingest, notif, naver, coupang, ownsite]
    [api, ingest, notif] >> Edge(style="dotted") >> cw
    [api, ingest, notif] >> Edge(style="dotted") >> sm
