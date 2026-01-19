# Mastery-Level Kubernetes Learning Plan for Spring Boot Developers

A developer with containerization familiarity, AWS experience, and Terraform skills can achieve Kubernetes proficiency through **five progressive phases** spanning **20-24 weeks**. This plan prioritizes deep understanding over speed, building from platform-agnostic fundamentals to production-grade EKS operations with GitOps workflows.

The learning journey follows a deliberate progression: master core Kubernetes concepts first, then specialize in Spring Boot optimization, layer in AWS EKS specifics, and finally integrate modern deployment workflows. Each phase includes clear milestones, practical projects, and progression criteria before advancing.

---

## Phase 1: Kubernetes fundamentals (Weeks 1-6)

**Goal**: Develop solid mental models of core Kubernetes concepts through hands-on practice, achieving CKAD-level application deployment competency.

### Week 1-2: Core architecture and basic objects

**Learning objectives**:
- Understand Kubernetes architecture (control plane, data plane, API server, etcd, scheduler, kubelet)
- Master pod lifecycle, resource specifications, and container runtime interaction
- Deploy applications using Deployments, ReplicaSets, and Services

**Resources**:
| Type | Resource | Focus |
|------|----------|-------|
| Book | *Kubernetes in Action, 2nd Edition* (Lukša) - Chapters 1-6 | Best explanation of internals, excellent ConfigMap coverage |
| Video | TechWorld with Nana - Kubernetes Crash Course (free, YouTube) | 3-hour visual overview with clear diagrams |
| Hands-on | kubernetes.io official tutorials | Browser-based interactive basics |

**Daily practice**: Set up **minikube** or **kind** locally. Minikube offers closer production simulation with add-ons; kind excels for multi-node testing with Docker.

```bash
# Quick start with minikube
minikube start --driver=docker
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=NodePort
minikube service nginx
```

**Milestone project**: Deploy a multi-tier application (frontend + backend + database) using Deployments and Services. Configure inter-service communication via ClusterIP services.

### Week 3-4: Configuration, storage, and networking

**Learning objectives**:
- Externalize configuration using ConfigMaps and Secrets
- Understand Persistent Volumes, Claims, and StorageClasses
- Master Service types (ClusterIP, NodePort, LoadBalancer) and Ingress fundamentals
- Configure basic network policies

**Resources**:
- *Kubernetes in Action* - Chapters 7-10 (best ConfigMaps explanation available)
- *The Kubernetes Book, 2025 Edition* (Poulton) - Dedicated security chapters
- Killercoda interactive scenarios (free, same environment as CKA/CKAD exams)

**Hands-on exercises**:
1. Create ConfigMaps from literal values, files, and directories
2. Mount Secrets as volumes vs environment variables (understand security implications)
3. Deploy StatefulSet with persistent storage
4. Configure Ingress with path-based routing using NGINX Ingress Controller

**Milestone**: Modify Week 1-2 project to externalize all configuration. Database credentials should be in Secrets, application config in ConfigMaps.

### Week 5-6: RBAC, security, and operational basics

**Learning objectives**:
- Implement Role-Based Access Control (Roles, ClusterRoles, Bindings)
- Understand ServiceAccounts and pod security context
- Configure resource requests and limits
- Implement basic troubleshooting workflows

**Resources**:
- *Kubernetes Security* (Rice, Hausenblas) - O'Reilly
- *The Kubernetes Book* - Security chapters (threat modeling, real-world security)
- KodeKloud CKA course - Security module with hands-on labs

**Hands-on**:
```yaml
# Example: Restrict namespace access
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer-role
rules:
- apiGroups: ["", "apps"]
  resources: ["pods", "deployments", "services"]
  verbs: ["get", "list", "create", "update"]
```

**Milestone project**: Create a multi-tenant namespace structure with isolated RBAC. Each namespace should have different ServiceAccounts with appropriate permissions.

### Phase 1 progression criteria
- [ ] Deploy applications without referencing documentation for basic objects
- [ ] Troubleshoot common issues (CrashLoopBackOff, ImagePullBackOff, Pending pods)
- [ ] Explain the request flow from kubectl command to pod creation
- [ ] Complete Killercoda CKAD scenarios with 80%+ success rate

### Recommended investment for Phase 1

| Resource | Cost | Notes |
|----------|------|-------|
| *Kubernetes in Action, 2nd Ed* | ~$50-60 | Use discount code `au35luk` at Manning for 35% off |
| *The Kubernetes Book, 2025 Ed* | ~$30-40 | Annual updates, strong security focus |
| KodeKloud Standard (1 month) | $39/month | Integrated labs, or use Mumshad's Udemy course (~$15-25 on sale) |
| Killercoda | Free | CKA/CKAD exam-identical environments |

---

## Phase 2: Spring Boot Kubernetes optimization (Weeks 7-10)

**Goal**: Master containerization best practices for JVM applications and configure Spring Boot for Kubernetes-native deployment.

### Week 7-8: Container image optimization

**Learning objectives**:
- Build optimized container images using layered JARs
- Compare Dockerfile, Jib, and Cloud Native Buildpacks approaches
- Select appropriate base images and configure JVM memory settings

**Containerization approaches compared**:

| Approach | Docker Required | Dockerfile Needed | Build Speed | Best For |
|----------|-----------------|-------------------|-------------|----------|
| Multi-stage Dockerfile | Yes | Yes | Medium | Full control, complex requirements |
| Google Jib | No | No | Fastest | Kotlin/Gradle projects, CI/CD simplicity |
| Paketo Buildpacks | Yes | No | Slower | Zero-config, automatic security patching |

**Jib configuration for Kotlin/Gradle** (recommended for your stack):

```kotlin
// build.gradle.kts
plugins {
    id("com.google.cloud.tools.jib") version "3.4.0"
}

jib {
    from {
        image = "eclipse-temurin:21-jre-jammy"
    }
    to {
        image = "your-registry/spring-boot-app"
        tags = setOf("${version}", "latest")
    }
    container {
        ports = listOf("8080")
        jvmFlags = listOf(
            "-XX:MaxRAMPercentage=75.0",
            "-XX:+UseG1GC",
            "-XX:+UseContainerSupport"
        )
    }
}
```

**JVM memory configuration** is critical. The default `MaxRAMPercentage` of 25% is too conservative. Set **70-80%** for heap, reserving the remainder for Metaspace, code cache, and native memory.

**Milestone project**: Containerize an existing Spring Boot application using all three methods. Compare image sizes, build times, and layer efficiency.

### Week 9-10: Health checks, graceful shutdown, and configuration

**Learning objectives**:
- Configure liveness, readiness, and startup probes with Spring Actuator
- Implement graceful shutdown for zero-downtime deployments
- Integrate Spring Cloud Kubernetes for native ConfigMap/Secret binding

**Probe configuration best practices**:

```yaml
# Startup probe: Essential for Spring Boot's slow initialization
startupProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 30  # Allows 150s startup time

# Liveness: Keep simple, don't check external dependencies
livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  periodSeconds: 15
  failureThreshold: 5

# Readiness: Can check critical dependencies
readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  periodSeconds: 5
  failureThreshold: 3
```

**Graceful shutdown configuration**:

```yaml
# application.yml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s

# Deployment spec - CRITICAL: terminationGracePeriodSeconds > preStop + shutdown timeout
spec:
  terminationGracePeriodSeconds: 60
  containers:
    - lifecycle:
        preStop:
          exec:
            command: ["/bin/sh", "-c", "sleep 10"]
```

The **preStop sleep** allows Kubernetes endpoint removal to propagate before the application starts rejecting connections.

**Resources**:
- Spring Boot Container Images Guide: docs.spring.io/spring-boot/reference/packaging/container-images/
- Spring Cloud Kubernetes documentation
- Piotr Minkowski's blog: "Best Practices for Java Apps on Kubernetes"

**Milestone project**: Deploy Spring Boot microservice with proper probes, graceful shutdown, and externalized configuration via ConfigMaps. Verify zero-downtime during rolling updates.

### Phase 2 progression criteria
- [ ] Build container images without Docker daemon using Jib
- [ ] Explain probe types and when each triggers
- [ ] Configure JVM memory appropriately for container limits
- [ ] Achieve zero-downtime deployments with `kubectl rollout restart`

---

## Phase 3: AWS EKS deployment (Weeks 11-15)

**Goal**: Deploy production-ready EKS clusters using Terraform and integrate with AWS services.

### Week 11-12: EKS architecture and cluster provisioning

**EKS architecture understanding**:
- **Control plane**: AWS-managed, minimum 2 API server nodes across AZs, 3 etcd nodes
- **Data plane options**: Managed node groups (recommended), self-managed, or Fargate
- **Cost**: $0.10/hour per cluster plus EC2/Fargate compute

**Terraform EKS setup** using terraform-aws-modules/eks:

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "my-cluster"
  cluster_version = "1.31"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni    = {}
    aws-ebs-csi-driver = {
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }
  }

  eks_managed_node_groups = {
    default = {
      instance_types = ["m5.large"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3
    }
  }

  enable_cluster_creator_admin_permissions = true
}
```

**Resources**:
- EKS Workshop (eksworkshop.com) - Comprehensive hands-on labs
- AWS EKS Best Practices Guide
- HashiCorp Terraform EKS Tutorial

**Milestone**: Provision EKS cluster with Terraform, including VPC, managed node groups, and core add-ons.

### Week 13-14: IAM integration and networking

**IRSA (IAM Roles for Service Accounts)** enables pod-level AWS permissions:

```yaml
# ServiceAccount with IRSA annotation
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/my-role
```

**EKS Pod Identity** (newer, simpler alternative launched 2023):
- Single trust policy works across clusters
- No OIDC provider limits
- Requires `eks-pod-identity-agent` add-on

**AWS Load Balancer Controller setup**:

```bash
# Install via Helm with IRSA
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**Key Ingress annotations**:
```yaml
annotations:
  alb.ingress.kubernetes.io/scheme: internet-facing
  alb.ingress.kubernetes.io/target-type: ip
  alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
  alb.ingress.kubernetes.io/group.name: my-group  # Share ALB across Ingresses
```

### Week 15: AWS service integration

**RDS connectivity**: Configure security groups to allow EKS node security group access to RDS.

**Secrets management** with External Secrets Operator (recommended over CSI driver for Fargate compatibility):

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-k8s-secret
  data:
    - secretKey: password
      remoteRef:
        key: production/db-credentials
        property: password
```

**CloudWatch Container Insights**: Enable via EKS add-on `amazon-cloudwatch-observability` for integrated monitoring.

**Milestone project**: Deploy Spring Boot application on EKS with ALB Ingress, IRSA for S3 access, RDS connectivity, and secrets from AWS Secrets Manager.

### Phase 3 progression criteria
- [ ] Provision and destroy EKS clusters via Terraform without manual intervention
- [ ] Configure IRSA for pods accessing AWS services
- [ ] Troubleshoot ALB Ingress routing issues
- [ ] Integrate with at least 3 AWS services (RDS, Secrets Manager, ECR, CloudWatch)

---

## Phase 4: Helm and GitOps (Weeks 16-19)

**Goal**: Package applications with Helm and implement GitOps workflows for declarative deployments.

### Week 16-17: Helm mastery

**Chart structure for Spring Boot**:
```
my-spring-boot-app/
├── Chart.yaml          # name, version, appVersion
├── values.yaml         # Default config
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── _helpers.tpl    # Named template definitions
│   └── NOTES.txt
└── values/
    ├── values-dev.yaml
    ├── values-staging.yaml
    └── values-prod.yaml
```

**Environment management**: Use values file overlays, not branches:
```bash
helm install myapp ./chart -f values/values-base.yaml -f values/values-prod.yaml
```

**Database migrations with Helm hooks**:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  annotations:
    "helm.sh/hook": pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
```

**Resources**:
- Official Helm documentation (helm.sh/docs)
- Linux Foundation LFS244 course
- Artifact Hub for example charts

**Milestone**: Create production-ready Helm chart for Spring Boot service with environment-specific values, probes, and migration hooks.

### Week 18-19: GitOps implementation

**ArgoCD vs Flux decision matrix**:

| Factor | Choose ArgoCD | Choose Flux |
|--------|---------------|-------------|
| UI requirements | Need visual dashboard | CLI/API-first acceptable |
| Team background | Transitioning from traditional CI/CD | Kubernetes-native operators |
| Cluster topology | Central management of multiple clusters | One Flux per cluster |
| Secret encryption | External Secrets Operator | Native SOPS integration |

Both are CNCF Graduated projects with production-ready stability.

**Recommended repository structure** (folder-based, not branch-based):
```
gitops-repo/
├── apps/
│   ├── base/
│   │   └── myapp/
│   ├── dev/
│   ├── staging/
│   └── production/
├── infrastructure/
│   ├── base/
│   └── production/
└── clusters/
    ├── dev-cluster/
    └── prod-cluster/
```

**ArgoCD Application definition**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-production
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/gitops-repo
    targetRevision: main
    path: apps/production/myapp
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
  syncPolicy:
    automated:
      prune: true      # Remove deleted resources
      selfHeal: true   # Revert manual changes
```

**Secrets in GitOps**: Use External Secrets Operator to reference AWS Secrets Manager, avoiding secrets in Git entirely.

**Resources**:
- *GitOps and Kubernetes* (Manning)
- Codefresh GitOps Fundamentals (free certification)
- flux2-kustomize-helm-example repository

**Milestone project**: Implement GitOps pipeline with ArgoCD, automated image updates via ArgoCD Image Updater, and PR-based promotion from dev → staging → production.

### Phase 4 progression criteria
- [ ] Create Helm charts from scratch with proper templating
- [ ] Explain GitOps pull-based model vs traditional push-based CI/CD
- [ ] Implement drift detection and self-healing
- [ ] Execute environment promotion through Git workflow

---

## Phase 5: CI/CD and operations (Weeks 20-24)

**Goal**: Build complete CI/CD pipelines integrated with GitOps and implement production observability.

### Week 20-21: CI/CD pipeline implementation

**Recommended stack for Spring Boot + EKS**:
- **CI**: GitHub Actions (excellent Marketplace, generous free tier)
- **Image building**: Jib (daemonless, fast incremental builds)
- **Registry**: AWS ECR with immutable tags
- **GitOps CD**: ArgoCD + ArgoCD Image Updater
- **Progressive delivery**: Argo Rollouts (canary deployments)

**GitHub Actions workflow pattern**:
```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT:role/github-actions
          aws-region: us-west-2
      
      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build with Jib
        run: ./gradlew jib -Djib.to.image=$ECR_REGISTRY/myapp:$GITHUB_SHA
      
      - name: Scan image
        run: trivy image --exit-code 1 --severity CRITICAL $ECR_REGISTRY/myapp:$GITHUB_SHA
      
      - name: Update GitOps repo
        run: |
          # Clone gitops repo, update image tag, commit and push
```

**Image tagging strategy**: Use Git SHA (`app:ba970b9`) for traceability plus semantic version (`app:2.1.3`) for releases. Enable ECR immutable tags.

### Week 22-23: Observability stack

**Monitoring options**:
| Stack | Cost | Best For |
|-------|------|----------|
| kube-prometheus-stack | Free (self-managed) | Full control, PromQL expertise |
| Amazon Managed Prometheus + Grafana | Pay-per-use | AWS integration, managed operations |
| CloudWatch Container Insights | Included | Quick setup, native AWS |

**Recommended**: Start with CloudWatch Container Insights for baseline, add Prometheus for deep analytics.

**Spring Boot metrics configuration**:
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  metrics:
    tags:
      application: ${spring.application.name}
```

**Logging strategy**: Use **Loki + Grafana** for 50-70% cost reduction over Elasticsearch, or CloudWatch Logs for AWS-native integration. Configure structured JSON logging:

```xml
<!-- logback-spring.xml -->
<appender name="json" class="ch.qos.logback.core.ConsoleAppender">
  <encoder class="net.logstash.logback.encoder.LogstashEncoder"/>
</appender>
```

### Week 24: Autoscaling and troubleshooting

**Autoscaling stack**:
- **HPA**: Baseline pod scaling on CPU/memory
- **Karpenter**: Intelligent node provisioning (preferred over Cluster Autoscaler for EKS)
- **KEDA**: Event-driven scaling (queue depth, Kafka lag)

**Karpenter NodePool for cost optimization**:
```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]  # Spot for cost savings
  disruption:
    consolidationPolicy: WhenUnderutilized
```

**Essential troubleshooting commands**:
```bash
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl describe pod <pod-name>
kubectl logs <pod-name> -p  # Previous container logs
kubectl debug -it <pod-name> --image=nicolaka/netshoot --target=<container>
```

**Tools**: K9s for terminal-based fast troubleshooting, Lens for visual multi-cluster management.

### Phase 5 progression criteria
- [ ] Build complete CI/CD pipeline from commit to production
- [ ] Query metrics with PromQL/LogQL
- [ ] Configure HPA with custom metrics
- [ ] Diagnose and resolve common production issues independently

---

## Complete resource summary

### Books (priority order)
1. *Kubernetes in Action, 2nd Edition* - Deep fundamentals ($50-60)
2. *The Kubernetes Book, 2025 Edition* - Updated annually, security focus ($30-40)
3. *GitOps and Kubernetes* (Manning) - GitOps patterns ($45-50)

### Courses and certifications
| Resource | Cost | Time Investment |
|----------|------|-----------------|
| KodeKloud CKA/CKAD courses | $39/month or Udemy ($15-25 sale) | 40-60 hours |
| CKAD Certification | $445 | 1-2 months prep |
| EKS Workshop (eksworkshop.com) | Free | 20-30 hours |
| Codefresh GitOps Fundamentals | Free | 8-10 hours |

### Hands-on environments
- **Local**: minikube (production-like) or kind (Docker-based, fast)
- **Cloud**: Killercoda (free, exam-identical), EKS Workshop environments
- **Practice repos**: github.com/luksa/kubernetes-in-action-2nd-edition

### Total estimated investment
- **Time**: 20-24 weeks at 10-15 hours/week (200-360 hours)
- **Cost**: $200-500 (books + courses) + $445 optional CKAD certification

---

## Final capstone project

Build a complete production deployment pipeline:

1. **Spring Boot microservice** (Kotlin) with Actuator health endpoints
2. **Containerized with Jib**, pushed to ECR with Git SHA tags
3. **Helm chart** with environment-specific values
4. **EKS cluster** provisioned via Terraform with Karpenter
5. **GitOps deployment** via ArgoCD with automated image updates
6. **Observability** with Prometheus metrics, structured logging to CloudWatch
7. **Progressive delivery** with Argo Rollouts canary deployment

This capstone validates mastery across all phases and creates a reference architecture for future projects.