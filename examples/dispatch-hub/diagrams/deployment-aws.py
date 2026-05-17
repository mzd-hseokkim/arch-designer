from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import Route53, ALB, CloudFront
from diagrams.aws.compute import EKS, EC2
from diagrams.aws.database import RDS, ElastiCache, Dynamodb
from diagrams.aws.analytics import ManagedStreamingForKafka as MSK
from diagrams.aws.analytics import Glue
from diagrams.aws.storage import S3
from diagrams.aws.security import Cognito, SecretsManager, KMS
from diagrams.aws.ml import Sagemaker
from diagrams.aws.management import Cloudwatch
from diagrams.onprem.client import Users

graph_attr = {
    "fontsize": "18",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
    "rankdir": "LR",
}

with Diagram(
    "dispatch-hub — AWS Deployment (KR + JP active-active, analytics lake in us-west-2)",
    filename="out-deployment-aws",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    ec_clients = Users("EC 기업\n(KR/JP)")
    riders = Users("라이더 (mobile)")

    dns = Route53("Route 53\nlatency + geo-fence")

    def region_stack(label):
        with Cluster(label):
            alb = ALB("ALB\n+ Kong Ingress")
            cognito = Cognito("Cognito\n(OIDC + API Key)")

            with Cluster("EKS cluster"):
                eks = EKS("EKS 1.30\n+ Karpenter (Spot)")

            with Cluster("Event backbone"):
                msk = MSK("MSK 3-broker\nMulti-AZ")
                glue = Glue("Glue Schema\nRegistry")

            with Cluster("Datastores (4)"):
                tx = RDS("tx-pg\nAurora Multi-AZ")
                drv = RDS("driver-pg\nAurora Multi-AZ")
                ddb = Dynamodb("tracking-store\non-demand, TTL 90d")
                redis = ElastiCache("feature-redis\ncluster mode")

            with Cluster("Storage / Ops"):
                s3 = S3("Events archive\n(region-local)")
                sm = SecretsManager("Secrets")
                kms = KMS("KMS")
                cw = Cloudwatch("CW / Prom-on-EKS")

            return alb, cognito, eks, msk, glue, tx, drv, ddb, redis, s3, cw

    kr = region_stack("ap-northeast-2 (KR)")
    jp = region_stack("ap-northeast-1 (JP)")

    with Cluster("Global analytics (us-west-2, non-operational)"):
        lake = S3("Lake (Iceberg)")
        glue_g = Glue("Glue Catalog")
        sm_train = Sagemaker("SageMaker\ntraining")

    ec_clients >> Edge(label="HTTPS") >> dns
    riders >> Edge(label="gRPC") >> dns
    dns >> Edge(label="KR") >> kr[0]
    dns >> Edge(label="JP") >> jp[0]

    for stack in (kr, jp):
        alb, cognito, eks, msk, glue, tx, drv, ddb, redis, s3, cw = stack
        alb >> eks
        eks >> Edge(label="produce/consume") >> msk
        msk >> Edge(style="dashed") >> glue
        eks >> tx
        eks >> drv
        eks >> Edge(label="50K/s") >> ddb
        eks >> redis
        msk >> Edge(style="dashed", label="S3 sink") >> s3
        eks >> Edge(style="dotted") >> cw
        eks >> Edge(style="dotted") >> cognito

    kr[9] >> Edge(style="dashed", label="anonymized") >> lake
    jp[9] >> Edge(style="dashed", label="anonymized") >> lake
    lake >> glue_g >> sm_train
