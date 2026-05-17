from diagrams import Diagram, Cluster, Edge
from diagrams.k8s.compute import Deployment, Pod, StatefulSet
from diagrams.k8s.network import Ingress, Service
from diagrams.k8s.rbac import ServiceAccount
from diagrams.k8s.podconfig import ConfigMap, Secret
from diagrams.k8s.clusterconfig import HPA
from diagrams.k8s.controlplane import APIServer
from diagrams.onprem.gitops import Argocd
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.network import Istio
from diagrams.onprem.client import Users

graph_attr = {
    "fontsize": "18",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
    "rankdir": "LR",
}

with Diagram(
    "dispatch-hub — Kubernetes Workload View (per region)",
    filename="out-deployment-k8s",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    users = Users("External\ntraffic")

    with Cluster("namespace: gateway"):
        ing = Ingress("ALB Ingress\n(Kong)")

    with Cluster("namespace: domain-tx"):
        order = Deployment("order-svc")
        dispatch = Deployment("dispatch-svc")
        assignment = Deployment("assignment-svc")
        pricing = Deployment("pricing-svc")
        billing = Deployment("billing-svc")
        hpa_tx = HPA("HPA + KEDA\n(Kafka lag)")

    with Cluster("namespace: domain-driver"):
        rider = Deployment("rider-svc")
        notif = Deployment("notification-svc")
        hpa_drv = HPA("HPA + KEDA")

    with Cluster("namespace: domain-tracking"):
        tracking = Deployment("tracking-svc\n(gRPC stream)")
        hpa_trk = HPA("HPA (CPU)")

    with Cluster("namespace: ml"):
        triton = Deployment("routing-ml-svc\n(Triton)")
        model_cm = ConfigMap("model-registry")

    with Cluster("namespace: obs"):
        prom = Prometheus("Prometheus")
        graf = Grafana("Grafana")

    with Cluster("namespace: argo"):
        argo = Argocd("ArgoCD")

    mesh = Istio("Istio mesh\n(mTLS, traffic shift)")

    users >> ing
    ing >> [order, dispatch, tracking]
    dispatch >> Edge(label="gRPC") >> rider
    dispatch >> Edge(label="gRPC") >> triton
    notif >> Edge(style="dashed", label="FCM/APNs") >> users

    [order, dispatch, assignment, pricing, billing] >> Edge(style="dotted") >> hpa_tx
    [rider, notif] >> Edge(style="dotted") >> hpa_drv
    tracking >> Edge(style="dotted") >> hpa_trk

    argo >> Edge(style="dashed") >> [order, dispatch, assignment, pricing, billing, rider, notif, tracking, triton]
    [order, dispatch, rider, tracking, triton] >> Edge(style="dotted") >> prom
    prom >> graf
