---
title: "Phased Kubernetes Curriculum for Production EKS"
category: "Infrastructure"
description: "26-week phased EKS curriculum (MVP → production hardening → platform-engineering depth → optional CKA/CKAD) for a mid-level Spring Boot engineer, with opinionated stack defaults (Pod Identity, Karpenter, AWS LB Controller, Argo CD, Kyverno) and Korean + global engineering-blog resources interleaved."
---

# A Phased Kubernetes Curriculum for a Mid-Level Spring Boot Backend Engineer Targeting Production EKS

## TL;DR

- **Phase 1 (Weeks 1–5, "Minimum Viable EKS")** gets you from zero to productively running Spring Boot microservices on EKS with Helm, GitHub Actions, Datadog/Prometheus hookup, and a real Aurora/Redis/Kafka-backed app. Phase 2 (Weeks 6–13) hardens that into production: IRSA/Pod Identity, Karpenter, network policies, EKS upgrades, JVM-in-container tuning, and on-call patterns. Phase 3 (Weeks 14–22) is platform engineering depth — Argo CD GitOps, Istio vs Linkerd, custom controllers in Go, Kyverno/Gatekeeper, multi-tenancy. Optional Phase 4 (Weeks 23–26) is CKA + CKAD if you decide to certify.
- **Opinionated defaults for your stack:** Spring Boot 3 graceful shutdown + preStop sleep + `terminationGracePeriodSeconds=60`; `-XX:MaxRAMPercentage=75`, container-aware JVM, separate `/actuator/health/liveness` and `/actuator/health/readiness` (never tie liveness to DB/Redis/Kafka health); Karpenter over Cluster Autoscaler; Pod Identity over IRSA for new clusters; AWS Load Balancer Controller over Ingress NGINX on EKS; Argo CD over Flux; Kyverno over OPA Gatekeeper for Kubernetes-only policy; managed services (MSK, ElastiCache, Aurora) over self-hosted Kafka/Redis/MySQL on Kubernetes — at least until you have a dedicated platform team.
- **Korean + global resources are interleaved throughout.** Heavy use of Toss/Kakao/우아한형제들/당근/Coupang/Kurly engineering blogs and if(kakao)/DEVIEW/AWSKRUG talks for production realism, paired with Lukša's *Kubernetes in Action*, Ibryam's *Kubernetes Patterns*, the AWS EKS Best Practices Guide, KubeCon talks, the canonical `k8s.af` failure-stories collection, and TechWorld with Nana / Anton Putra / Marcel Dempers on YouTube.

---

## Key Findings

1. **The fastest productive path on EKS is not "learn all of Kubernetes first."** A Spring Boot engineer with Terraform/Helm/Actions experience can ship a real production-shaped service to EKS in 4–5 weeks if Phase 1 is sequenced as: containers → core K8s objects → kubectl fluency → Helm packaging → EKS-specific networking (ALB Controller, IRSA) → CI/CD → observability hookup. Diving into operators, service mesh, or CRDs early is wasted effort.
2. **Several EKS choices have changed materially in 2024–2026 and most older tutorials are wrong.** Karpenter 1.0 GA, EKS Pod Identity (re:Invent 2023) replacing IRSA for most new use cases, EKS Auto Mode (re:Invent 2024) which bakes in Karpenter + ALB Controller + EBS CSI, and the deprecation of dockershim/Pod Security Policies all mean a curriculum written before 2024 will mislead you. Phase 2 should explicitly address these.
3. **JVM-on-Kubernetes mistakes account for a disproportionate share of Spring Boot incidents.** The four recurring failure modes are (a) JVM not container-aware → OOMKilled (fixed pre-JDK 10, but still seen with custom images and `-Xmx` hardcoded); (b) liveness probe tied to DB/Redis health → cascading restarts when a dependency blips; (c) no preStop sleep → 503s on rolling deploy because kube-proxy/ALB target deregistration is asynchronous with SIGTERM; (d) HPA + VPA on the same CPU metric → fight loop. Phase 1 must teach these explicitly.
4. **Korean tech companies have published unusually high-quality production K8s content.** Kakao's KubeCon EU 2024 Cilium talk (7,000+ clusters, 120,000+ nodes, kube-proxy replacement), 당근마켓's Elasticsearch-on-ECK migration, 우아한형제들's testing-environment-on-K8s post, Toss's SLASH talks on EKS multi-cluster, and Coupang/Kurly's AWSKRUG sessions are all relevant; if(kakao) 2020 alone has ~10 hours of K8s talks (k8s-native datacenter, MySQL-on-K8s, Redis cache farm, Kubernetes Live Upgrade API).
5. **The "Minimum Viable" phase deliberately defers a lot.** It postpones service mesh, operators/CRDs, multi-cluster, GitOps with progressive delivery, policy engines, Pod Security Admission deep-dives, custom schedulers, and CKA exam prep. Each of these lands later when there is concrete need.

---

## Details

### How to use this curriculum

- Total length: **22 weeks core** (Phases 1–3) + **4 optional weeks** for certification. Adjust pace freely; with a full-time job, plan ~10–12 hours/week.
- **Each week has the same shape:** (1) 1–2 reading anchors (book chapters / official docs), (2) 1 video lecture or conference talk, (3) one Korean engineering blog post for production framing, (4) a hands-on lab on your own EKS cluster, (5) a Friday "war story" post-mortem read.
- **Persistent project across all phases:** "Mart-Kit" — a 4-service Spring Boot 3.x / Kotlin / Gradle KTS microservices system: `order-service` (REST + JPA on Aurora PostgreSQL), `inventory-service` (REST + Redis cache via Lettuce), `notification-service` (Kafka consumer), and `bff-gateway` (Spring Cloud Gateway). You will deploy this stack to EKS and progressively harden it. By Week 22 it will run on Argo CD with Istio mTLS, Karpenter-managed nodes, Kyverno policies, a custom CRD/operator, and full Datadog + Prometheus observability.
- **Depth-first rule:** before adopting any abstraction (Helm, Argo CD, Istio, Kyverno, Operator SDK), you spend at least one day building the primitive it abstracts. E.g., write a raw Kustomize overlay before using Helm, write a Bash reconcile loop before using controller-runtime, write a `MutatingAdmissionWebhook` from scratch before using Kyverno.

### Tooling baseline to install in Week 1

`kubectl` (with `krew` plus `neat`, `ctx`, `ns`, `tree`, `view-secret`, `images`), `helm`, `kind`, `k9s`, `stern`, `kubectx`/`kubens`, `eksctl`, `awscli` v2, `kubeseal`, `kustomize`, `dive` (image inspector), `trivy`, `kube-score`, `kubeval`/`kubeconform`. Set up shell aliases (`k=kubectl`, `kgp`, `kgs`, etc.) — speed matters in incidents and on the CKA.

---

## PHASE 1 — Minimum Viable EKS (Weeks 1–5)

**Goal:** ship Mart-Kit (4 Spring Boot services + Aurora + ElastiCache + MSK) to a real EKS cluster with CI/CD, sane probes, graceful shutdown, observability, and rolling updates. By the end you can debug a CrashLoopBackOff in under 10 minutes.

**Prerequisites:** Docker fluency, Linux basics (cgroups/namespaces conceptually), Terraform basics (you have these), HTTP/TCP fundamentals.

**Phase deliverable:** Mart-Kit running on a dev EKS cluster, deployed via GitHub Actions on every merge to `main`, with Datadog APM + Prometheus metrics + structured logs to CloudWatch, exposed via ALB on a real domain via ACM + ExternalDNS, and a runbook for one failed deploy.

### Week 1 — Containers, OCI, and the JVM-in-container truth

- **Concepts:** Linux namespaces, cgroups v2, OCI image spec, layers, multi-stage builds, distroless vs Alpine vs Amazon Linux 2023 (AL2023), JVM container awareness (`UseContainerSupport` enabled by default since JDK 10), `MaxRAMPercentage`, JIT vs AOT, AppCDS, Class Data Sharing.
- **Read:** Lukša *Kubernetes in Action* 2e Ch. 1–2; Datadog "Java on containers: a guide to efficient deployment"; Pretius "JVM Kubernetes: Optimizing Kubernetes for Java Developers."
- **Watch:** TechWorld with Nana — "Docker Tutorial for Beginners" (only the second half on multi-stage); "Java in containers: pitfalls and best practices" (Devoxx).
- **Korean read:** 우아한형제들 기술블로그 "쿠버네티스를 이용한 테스팅 환경 구현" (역사적 배경용).
- **Lab:** containerize `order-service`. Three Dockerfile variants — naïve `FROM eclipse-temurin:21`, multi-stage with distroless, and a Spring Boot layered jar (`bootBuildImage`) using Paketo buildpacks. Compare image size with `dive`. Run each with `--memory=512m` and prove with `jcmd` or `Native Memory Tracking` that `MaxRAMPercentage=75` keeps heap under the cgroup limit. Reproduce an OOMKill by setting `-Xmx768m` inside a 512 MiB container.
- **War story Friday:** read Zalando's "A Million Ways to Crash Your Cluster" deck (Docker daemon hangs, CPU CFS quota throttling).
- **Trade-off note — when *not* to optimize images:** if your build is the bottleneck and your security team mandates AL2023 with patched packages, distroless adds debugging pain (no shell). For most Korean fintech/commerce teams, AL2023 + JRE-only base is the pragmatic default.

### Week 2 — Core Kubernetes objects, the hard way

- **Concepts:** Pod, ReplicaSet, Deployment, Service (ClusterIP/NodePort/LoadBalancer), Endpoints/EndpointSlices, Namespace, ConfigMap, Secret, the control loop pattern, declarative vs imperative `kubectl`.
- **Read:** Lukša Ch. 3–5; Kubernetes official "Concepts → Workloads."
- **Watch:** TechWorld with Nana "Kubernetes Crash Course" (skip basics you know, focus on probes and Services).
- **Korean read:** 카카오 i 클라우드팀 if(kakao)dev2022 "모든 것이 쿠버네티스인 세상에서 안전하게 배포하기."
- **Lab:** spin up `kind` locally with 3 worker nodes. Hand-write *raw YAML* (no Helm) for `order-service`: Deployment, Service, ConfigMap, Secret. Practice imperative→declarative: `kubectl run … --dry-run=client -o yaml`, then save and `kubectl apply`. Force kill pods with `kubectl delete pod` and watch the ReplicaSet recreate them. Read every field in `kubectl get pod -o yaml`.
- **Trade-off note — when *not* to use Deployments:** for stateful services like Kafka/ZooKeeper/Redis Cluster you use StatefulSets; for daemons (Datadog Agent, Fluent Bit) you use DaemonSets; for batch work, Job/CronJob. Don't use Deployment for everything by reflex.

### Week 3 — kubectl fluency, debugging, probes, graceful shutdown

- **Concepts:** liveness vs readiness vs startup probes; Spring Boot Actuator's `/actuator/health/liveness` and `/actuator/health/readiness` (since Spring Boot 2.3, the design Spring Boot 3 keeps); SIGTERM lifecycle, `terminationGracePeriodSeconds`, preStop hooks; `kubectl describe`, `kubectl logs --previous`, `kubectl debug`, ephemeral containers.
- **Read:** Spring Boot reference "Production-ready features → Kubernetes Probes"; Baeldung "Liveness and Readiness Probes in Spring Boot"; Thoughtworks "Graceful Shutdown Services in Kubernetes"; MobiLab "A Proper Kubernetes Readiness Probe with Spring Boot Actuator" (the canonical "do not tie liveness to DB" article).
- **Watch:** Marcel Dempers "Debugging Kubernetes" series.
- **Korean read:** 트렌디욜 / 한국어 번역 "쿠버네티스에서 Spring Boot 우아한 종료" (or `meirong.dev` "Spring Boot3 graceful shutdown in Kubernetes").
- **Lab:** add to `order-service`:
  - `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase=25s`.
  - `management.endpoint.health.probes.enabled=true`, separate liveness (process-only) and readiness (DB + Redis dependency check, but only as readiness).
  - Deployment manifest with `livenessProbe` → `/actuator/health/liveness` (initialDelay 30, period 15, failureThreshold 5), `readinessProbe` → `/actuator/health/readiness` (period 4, failureThreshold 3), `startupProbe` → `/actuator/health/liveness` with high `failureThreshold` to handle slow JVM warmup.
  - `lifecycle.preStop.exec.command: ["sh","-c","sleep 10"]` and `terminationGracePeriodSeconds: 60`.
  - Run `hey` or `k6` against the service while doing `kubectl rollout restart` and prove zero 5xx.
- **Anti-patterns to demo deliberately (and then remove):** liveness pointing at `/actuator/health` (hits DB) → induce DB outage and watch every pod restart-loop; preStop missing → see ALB target group serving 503s during rolling deploy.
- **War story:** Monzo 2017 outage (Linkerd + etcd + services-without-endpoints) — read the public postmortem.

### Week 4 — Helm, Kustomize, and your first EKS cluster

- **Concepts:** Helm 3 templating, `values.yaml` per env, chart dependencies (`umbrella charts`); Kustomize overlays; when to choose which (Kustomize for env diffs of internal apps, Helm for distributing to others); EKS cluster creation with Terraform `terraform-aws-modules/eks/aws`; managed node groups; `aws-auth` ConfigMap → access entries (the new model since 2024).
- **Read:** Helm docs "Chart Template Guide"; AWS EKS User Guide "Get started with Amazon EKS – eksctl"; AWS EKS Best Practices Guide (skim Compute & Networking sections).
- **Watch:** Anton Putra "Helm Tutorial for Beginners"; AWS re:Invent CON406 (current year) "Amazon EKS under the hood."
- **Korean read:** Toss SLASH 22/23 발표 "EKS에서 안전하게 배포하기."
- **Lab:** with Terraform, provision a small EKS 1.31+ cluster (2 t3.medium managed nodes, public+private subnets, single NAT for cost), VPC CNI add-on, CoreDNS, kube-proxy, EBS CSI driver, EKS Pod Identity Agent. Convert your raw YAML from Week 3 into a Helm chart `mart-kit-app` with values for image tag, env, replicas, resources. Deploy `order-service` via `helm upgrade --install`. Then make a Kustomize overlay variant (`base/`, `overlays/{dev,prod}`) and pick one (Helm) for the chart, the other (Kustomize) for env-specific diffs.
- **Trade-off note — when *not* to use Helm:** templating YAML with Go templates is brittle; for simple internal apps, Kustomize alone is often clearer. Use Helm when you need versioned releases, rollback semantics, or distribute to others. Kakao i Cloud's talks repeatedly note that Helm hides too much for platform teams that need to debug fields.

### Week 5 — CI/CD, observability, and Phase 1 capstone

- **Concepts:** GitHub Actions OIDC → AWS (no long-lived keys); ECR push; Helm chart deploy from Actions; Datadog Operator + APM auto-instrumentation; Prometheus stack via `kube-prometheus-stack`; OpenTelemetry collector sidecar vs DaemonSet; AWS Load Balancer Controller and Ingress (ALB) with ACM + ExternalDNS.
- **Read:** AWS blog "Configure OpenID Connect in AWS to retrieve temporary credentials for GitHub Actions"; AWS Load Balancer Controller docs; Spring Boot reference "Metrics → Prometheus."
- **Watch:** Datadog DASH 2024 "Tracing Spring Boot on Kubernetes."
- **Korean read:** 카카오페이 if(kakao) "MLOps 적용기" (AWS EKS + Argo Workflows; or any 카카오페이 "쿠버네티스 배포 자동화" 글). 당근마켓 "검색 엔진을 쿠버네티스로 운영하기" (Kideok Kim, daangn medium).
- **Lab — Capstone:**
  1. Multi-stage GitHub Actions workflow: build → test (Testcontainers Postgres + Redpanda for Kafka) → build image → push to ECR → `helm upgrade` to EKS dev namespace.
  2. Deploy all 4 Mart-Kit services. Use Aurora PostgreSQL (existing RDS), ElastiCache Redis (existing), MSK (existing) — connect from pods using EKS Pod Identity (you'll harden this in Phase 2; for now, an IAM role for the node group with read-only Secrets Manager works).
  3. Install `kube-prometheus-stack`, the Datadog Cluster Agent, and the AWS Load Balancer Controller (Helm).
  4. Spring Boot Micrometer → Prometheus scrape via `ServiceMonitor`. OpenTelemetry Java agent → Datadog APM.
  5. Ingress with `alb.ingress.kubernetes.io/scheme: internet-facing` + ACM cert + ExternalDNS pointing at Route 53.
- **Phase 1 done when:** you can ship a code change end-to-end in <15 minutes, see traces in Datadog, see custom Micrometer metrics in Grafana, and pass a "rolling restart under load" test with zero 5xx.

---

## PHASE 2 — EKS Production Operations (Weeks 6–13)

**Goal:** turn the dev cluster into something a real on-call rotation could run. Cover IRSA/Pod Identity, Karpenter, autoscaling, network policies, secrets, EKS upgrades, cost, and debugging real incidents.

**Phase deliverable:** a "production" Mart-Kit cluster with Karpenter autoscaling + Spot, Pod Identity for all workloads, NetworkPolicies isolating namespaces, External Secrets Operator pulling from AWS Secrets Manager, HPA on custom metrics, a documented EKS minor-version upgrade you've actually performed in a sandbox, a Kubecost dashboard, and a written runbook covering 5 common incident classes.

### Week 6 — IRSA, EKS Pod Identity, and AWS integration

- **Concepts:** OIDC provider model (IRSA); the `pods.eks.amazonaws.com` service principal model (Pod Identity); when to use which (Pod Identity is the new default for EKS-only workloads since 2024; IRSA still required for Fargate, EKS Anywhere, and ROSA); the projected service account token mechanism; `sts:AssumeRoleWithWebIdentity` vs `eks-auth:AssumeRoleForPodIdentity`.
- **Read:** AWS blog "Amazon EKS Pod Identity: a new way for applications on EKS to obtain IAM credentials"; KubeBlogs "EKS IRSA vs EKS Pod Identity"; AWS EKS Best Practices "Identity and Access Management."
- **Korean read:** AWSKRUG 발표 "EKS Pod Identity 도입기" (search the AWSKRUG YouTube channel).
- **Lab:** migrate your services from node-role IAM to Pod Identity. `order-service` → S3 backup permissions; `notification-service` → SQS DLQ permissions; tag a session with `aws:RequestTag/team` to demonstrate ABAC. Verify with CloudTrail. Then *also* set up one role with IRSA for comparison and feel the OIDC trust-policy pain.
- **Trade-off note — when *not* to use Pod Identity:** Fargate (use IRSA), or if you need cluster-portable trust policies that work outside EKS.

### Week 7 — Networking deep dive: VPC CNI, AWS Load Balancer Controller, NetworkPolicies

- **Concepts:** AWS VPC CNI (each pod gets a real VPC IP), ENI/IP exhaustion (the IPv4 exhaustion problem on dense nodes), prefix delegation, custom networking (separate pod CIDR), IPv6 mode; `kube-proxy` iptables vs IPVS modes; AWS LBC's IP target type vs instance target type; NetworkPolicies (default-deny model), Calico vs Cilium for enforcement; East-West DNS (`coredns`, NodeLocal DNSCache).
- **Read:** AWS EKS Best Practices "Networking"; Calico docs "Adopting a zero-trust network policy"; Kakao CNCF case study (Cilium kube-proxy replacement at 7,000 cluster scale).
- **Watch:** KubeCon EU 2024 "Cilium at Kakao" (Kwang Hun Choi).
- **Korean read:** 카카오 i 클라우드팀 if(kakao) "Multitenancy Network with Kubernetes."
- **Lab:** enable prefix delegation on VPC CNI; install Cilium-style NetworkPolicies (or Calico) and write default-deny per namespace, then explicit allow rules: `inventory` accepts only from `order` and `bff`; `notification` accepts only Kafka egress to MSK CIDR. Switch ALB Ingress from instance to IP target type (the recommended mode with AWS VPC CNI). Break things on purpose: simulate an ENI-exhausted node by overcommitting pods on a t3.small.
- **Trade-off — Ingress NGINX vs AWS LBC:** AWS LBC is the EKS-native default, gives you ALB features (WAF, OIDC at the LB), and removes a hop. Ingress NGINX gives more flexibility (path rewrites, custom Lua, rate limiting) but adds an internal LB hop and an L4 NLB in front. Korean SaaS shops at 우아한형제들/Toss commonly run both: ALB for public, NGINX for complex internal routing.

### Week 8 — Storage: EBS CSI, EFS CSI, and stateful workloads

- **Concepts:** PV/PVC/StorageClass; gp3 vs io2 vs Provisioned IOPS; EBS CSI driver; volume binding modes (`WaitForFirstConsumer` is mandatory for EBS in multi-AZ clusters — common foot-gun); EFS CSI for ReadWriteMany; topology-aware scheduling; the volume-zone-affinity issue with Cluster Autoscaler that Karpenter fixes.
- **Read:** AWS EKS Best Practices "Storage"; AWS blog "Optimize cost and performance for Amazon EBS volumes."
- **Lab:** add an `audit-log-writer` StatefulSet that writes to a gp3 PVC. Crash the node, prove the PVC reattaches. Migrate to EFS for a shared-config use case and measure latency difference.
- **Trade-off — Kafka/Redis/Postgres on Kubernetes vs managed:** for your stack (Aurora, ElastiCache, MSK), the managed services almost always win on TCO, especially in Korea where 카카오/Coupang/Kurly publish data points showing self-hosted Kafka on K8s requires 2–3 dedicated SREs at scale. The exception is multi-tenant internal platforms (Kakao does run MySQL on K8s — see if(kakao)2020 "MySQL on Kubernetes" — but they have a platform team of dozens). Rule: if you can answer "yes" to managed, use managed.

### Week 9 — Karpenter, autoscaling, and cost

- **Concepts:** Cluster Autoscaler vs Karpenter (Karpenter provisions instances directly via EC2 Fleet API in ~60s vs CA's 2–4 minutes via ASG); NodePool, EC2NodeClass, Disruption (consolidation policies `WhenEmpty`, `WhenEmptyOrUnderutilized`); Spot diversification; Karpenter Drift for AMI patching; HPA v2, custom metrics via `prometheus-adapter` and KEDA; VPA in `Recommendation` mode; the HPA-vs-VPA-on-same-metric foot-gun; PodDisruptionBudgets; `topologySpreadConstraints`; Kubecost / OpenCost.
- **Read:** AWS EKS Best Practices "Karpenter" + "Compute" sections; Karpenter docs "Disruption"; the Paytm Money / ZeonEdge case studies showing 30–56% cost reduction with Karpenter + Spot.
- **Watch:** AWS re:Invent CON312 "Optimizing Amazon EKS for performance and cost"; Anton Putra "Karpenter vs Cluster Autoscaler."
- **Korean read:** 우아한형제들 / 토스 / Coupang AWSKRUG 발표 "EKS Karpenter 도입기" (multiple available on AWSKRUG YouTube).
- **Lab:** install Karpenter 1.x. Define two NodePools: `default` (on-demand m5/m6i/m6a, weight 50) and `spot` (Spot, c/m/r 4xlarge–8xlarge, taint `karpenter.sh/spot=true:NoSchedule`). Move stateless services to Spot via toleration; keep `notification-service` Kafka consumer on on-demand (Spot interruption + Kafka rebalance is unpleasant). Add PDBs (`maxUnavailable: 1`) and `topologySpreadConstraints` over zones. Add HPA on `http_server_requests_seconds_count` rate via prometheus-adapter. Install Kubecost; document monthly cost per namespace. Goal: 30%+ reduction vs the Phase 1 baseline.
- **Trade-off — Karpenter vs EKS Auto Mode:** Auto Mode (re:Invent 2024) is "managed Karpenter" + AWS LBC + EBS CSI + Pod Identity Agent baked in. Lower operational toil; per-node management fee on top of EC2; you lose the ability to customize AMIs (must use Bottlerocket). Use Auto Mode if you're a small team without a platform engineering function. Use self-managed Karpenter if you need custom AMIs, Graviton tuning, or AL2023 compliance baselines.

### Week 10 — Secrets, security baseline, Pod Security Admission

- **Concepts:** native Secrets vs External Secrets Operator (ESO) + AWS Secrets Manager / Parameter Store; Sealed Secrets vs ESO trade-off; SOPS with KMS; Pod Security Admission (`restricted`, `baseline`, `privileged` — replacing PSP); securityContext (runAsNonRoot, readOnlyRootFilesystem, drop `ALL` capabilities); EKS audit logging to CloudWatch; GuardDuty for EKS; image scanning with ECR + Trivy in CI; supply-chain basics (signed images, SBOMs).
- **Read:** AWS EKS Best Practices "Security"; Kubernetes docs "Pod Security Standards."
- **Korean read:** 카카오뱅크 if(kakao) "쿠버네티스 보안 강화기"; 토스 보안 블로그 글 (search "Toss SLASH 보안").
- **Lab:** install ESO, sync all secrets from AWS Secrets Manager (DB password, Kafka credentials, Datadog API key). Apply `pod-security.kubernetes.io/enforce: restricted` to your app namespaces. Fix every violation in your charts (drop NET_RAW, run as UID 1000, read-only root FS — Spring Boot needs a writable `/tmp` so use an emptyDir volume). Enable EKS control-plane audit logging → CloudWatch → a metric filter that alerts on `system:anonymous`. Run Trivy in CI as a blocking step on HIGH/CRITICAL CVEs.

### Week 11 — Spring Boot production patterns on Kubernetes

- **Concepts:** Spring Cloud Kubernetes (config from ConfigMaps, service discovery via K8s API — and when *not* to use it: typically you don't, the K8s Service primitive is enough); Testcontainers' Kubernetes module (`k3s` container) for integration testing manifests; HikariCP sizing per pod (max-pool-size × replicas must respect Aurora connection limits — common incident); JFR + heap dumps from a crashed pod (`emptyDir` for `/dump`, `kubectl cp`); Lettuce `ClusterTopologyRefresh` and Redis cluster failover behavior; Kafka rebalance + readiness probes (do *not* mark pod NotReady during a rebalance; it'll cascade).
- **Read:** Spring Boot reference "Kubernetes Probes" (re-read with Phase 2 eyes); Cloud Native Spring in Action (Mauro Vocale) Ch. 5–9; HikariCP wiki "About Pool Sizing."
- **Korean read:** 우아한형제들 "스프링 부트 + 쿠버네티스 운영 경험" (search woowahan.github.io); 카카오페이 "Batch Performance 극한으로 끌어올리기" (대량 처리 + K8s 운영 관점).
- **Lab:** add startup probe with high failureThreshold so JVM warmup never trips liveness; configure HikariCP `maximumPoolSize=10` per replica × 6 replicas = 60, well under Aurora's connection limit; add `JAVA_TOOL_OPTIONS=-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dump`; chaos test by forcing OOM and pulling the dump out. Add Testcontainers k3s integration test that asserts your liveness endpoint stays UP when Redis goes down.

### Week 12 — Debugging, observability under fire, on-call

- **Concepts:** systematic incident triage flow (CrashLoopBackOff → `describe` → `logs --previous` → events → image pull → resource); CPU throttling diagnosis (`container_cpu_cfs_throttled_periods_total`); memory pressure vs OOMKilled vs Evicted; node `NotReady` causes (kubelet, disk pressure, network); kube-state-metrics queries for a runbook dashboard; distributed tracing across Istio-less Spring Boot via OpenTelemetry; the "blameless postmortem" template.
- **Read:** Henning Jacobs' k8s.af failure-stories list — pick 4 to read (Monzo, Preply DNS/conntrack, Grafana Pod Priorities cascading preemption, JW Player crypto miner); Google SRE Book Ch. 14–15.
- **Korean read:** 카카오 1015 데이터센터 화재 회고 if(kakao)dev2022 발표들 (5 sessions on dual-region Kubernetes recovery).
- **Lab:** induce 5 failure modes in your dev cluster and document recovery: (1) DB connection pool exhaustion → readiness flapping; (2) node disk pressure → pod evictions; (3) ALB target-group deregister delay → 503s on rolling deploy (fix with preStop sleep — re-prove your Phase 1 fix still works); (4) NetworkPolicy too tight → DNS fails (Preply postmortem); (5) HPA + memory-mode VPA fight loop. Write a 1-page runbook per incident.

### Week 13 — EKS upgrades and Phase 2 capstone

- **Concepts:** Kubernetes minor versions (one per ~4 months upstream), EKS support matrix (extended support since 2024), control-plane upgrade is one API call but data-plane is yours; deprecated API checks (`kube-no-trouble`/`kubent`, Pluto); Karpenter Drift for AMI rotation; upgrade order (control plane → addons → data plane); blue/green vs in-place; the "21-day max lifetime" Auto Mode pattern as a continuous patching strategy.
- **Read:** AWS EKS docs "Update existing cluster to new Kubernetes version"; AWS EKS Best Practices "Cluster upgrades."
- **Korean read:** 우아한형제들/Coupang/Toss EKS 업그레이드 후기 (multiple AWSKRUG talks).
- **Lab — Phase 2 Capstone:** in a sandbox, perform an actual EKS minor-version upgrade (e.g., 1.31 → 1.32). Run `kubent` first to find deprecated APIs in your charts. Upgrade addons (VPC CNI, CoreDNS, kube-proxy) to the matching minor. Use Karpenter Drift to roll all worker nodes onto new AMIs. Document downtime (should be zero for stateless services, brief blips for stateful). Write a runbook for the production version.
- **Phase 2 done when:** you have a written, tested runbook for upgrades; cost per namespace is visible in Kubecost; PSA `restricted` is enforced; all secrets come from Secrets Manager via ESO; Karpenter has saved you ≥30% on compute; you can reproduce 5 incident classes from memory.

---

## PHASE 3 — Platform Engineering Depth (Weeks 14–22)

**Goal:** move from "I run my services on EKS" to "I build the platform other teams run their services on." GitOps, service mesh, custom controllers, policy, multi-tenancy.

**Phase deliverable:** Mart-Kit running with Argo CD-driven GitOps, Istio mTLS + traffic shifting, a custom CRD `MartKitService` with a controller you wrote in Go, Kyverno policies enforcing image registries and PSA, and a tenant-isolated namespace model with per-team RBAC and resource quotas.

### Week 14 — GitOps with Argo CD

- **Concepts:** push-based CI/CD vs pull-based GitOps; Argo CD architecture (Application controller, repo server, API server); ApplicationSet (multi-cluster, multi-env at scale); App-of-Apps pattern; sync waves and hooks; Argo Rollouts for canary/blue-green; sealed/encrypted secrets in Git; the auto-sync vs manual-sync trade-off in production.
- **Read:** Argo CD docs "Core Concepts"; AWS Prescriptive Guidance "GitOps tools comparison."
- **Watch:** Codefresh / Akuity Argo CD masterclasses; Anton Putra "Argo CD vs Flux."
- **Korean read:** 카카오 / Toss / Kurly Argo CD 도입기 (search 인프런 / 패스트캠퍼스 + AWSKRUG).
- **Lab:** install Argo CD on a separate "platform" cluster; bootstrap with App-of-Apps; move all 4 Mart-Kit services to GitOps (one Git repo for app charts, one for infrastructure). Replace your GitHub Actions deploy step with "render Helm values, commit to env repo." Add Argo Rollouts for `bff-gateway` with a 5%/25%/50%/100% canary based on success rate from Prometheus.
- **Trade-off — Argo CD vs Flux:** Argo CD wins on UI/UX and ApplicationSet maturity (de-facto standard in 2024–2026 with ~62% market share); Flux wins on lightweight CLI, OCI-native, deeper Helm integration. For a Korean dev team without a dedicated platform team, Argo CD is the safer default — the UI alone reduces operator load. Choose Flux when you're building tooling on top (e.g., Weaveworks-style).

### Week 15 — Service mesh fundamentals

- **Concepts:** sidecar pattern, Envoy data plane, control plane (istiod), L7 routing (VirtualService, DestinationRule), mTLS (PeerAuthentication), authorization (AuthorizationPolicy), gateways; Linkerd's micro-proxy (Rust) vs Istio's Envoy (C++); resource overhead (Linkerd ~10–20MB per sidecar vs Istio's 40–100MB); ambient mode (Istio 1.22+) which removes sidecars in favor of ztunnel + waypoint proxies.
- **Read:** Istio "Concepts" docs; Buoyant "Linkerd vs Istio"; Solo.io comparison; CNCF 2024 survey data (Istio 62%, Linkerd 28% market share among mesh adopters).
- **Korean read:** 우아한형제들 / Toss 서비스 메시 도입기 (Toss SLASH 발표 "서비스 메시로 안전하게 트래픽 관리하기"); 카카오 if(kakao) Istio 발표.
- **Lab:** install Istio (Helm, profile=demo) on dev cluster. Inject sidecars in Mart-Kit namespace. Enable strict mTLS. Write a VirtualService that routes 10% of `inventory` traffic to a v2 deployment based on a header. Then *uninstall Istio* and install Linkerd; redo the canary; benchmark p50/p99 latency overhead (Linkerd should be ~1–2ms lower at p99).
- **Trade-off — when *not* to use a service mesh:** if you have <20 services and no compliance requirement for mTLS-everywhere, the operational burden often outweighs benefits. The 2024 CNCF data shows Istio adoption requires real platform-team investment. Many Korean mid-sized teams instead achieve mTLS via AWS PrivateLink + ALB OIDC + service-to-service JWT in code. Adopt mesh when you need: (a) zero-trust mTLS across hundreds of services, (b) language-agnostic retries/timeouts/circuit breakers, (c) fine-grained authorization that's hard to enforce in app code.

### Week 16 — Custom controllers and operators (write one from scratch)

- **Concepts:** the controller pattern (informer → workqueue → reconcile loop); CRDs and OpenAPI schemas; finalizers; status subresource; controller-runtime (Go); Kubebuilder vs Operator SDK; kotlin-operator-framework (the Kotlin option, Fabric8); when an operator is the right answer (managing complex stateful systems with domain logic) vs when it's not (Helm + Argo CD is enough for CRUD on K8s objects).
- **Read:** Lukša / Stoneman / Hausenblas *Programming Kubernetes* 2e (the canonical book); Kubebuilder Book (online).
- **Watch:** "Writing your first Kubernetes Operator" (Red Hat / OperatorHub talks); Marcel Dempers operator series.
- **Korean read:** 카카오 i 클라우드 if(kakao) "Kubernetes Controller가 무엇인지 — MyReplicaSet 예제"; 당근마켓 ECK (Elastic Cloud on Kubernetes operator) 운영 경험.
- **Lab:** write a `MartKitService` CRD in Go with Kubebuilder. Spec includes `image`, `replicas`, `kafkaTopics: []`, `databaseSecret`. The controller creates a Deployment + Service + ServiceMonitor + (optionally) creates Kafka topics via the Strimzi `KafkaTopic` CRD. Add a finalizer that drains traffic before delete. Bonus track: rewrite the same operator in Kotlin using Fabric8's operator-framework to compare ergonomics.
- **Trade-off — when *not* to write an operator:** if a Helm chart + Argo CD covers it, don't. Operators add a control plane to maintain. Reserve for: stateful systems, domain-specific lifecycle (DB backup/restore), or platform-as-product internal abstractions where you're hiding K8s from app teams.

### Week 17 — Policy: Kyverno and OPA Gatekeeper

- **Concepts:** admission controllers (validating, mutating); ValidatingAdmissionPolicy (built-in CEL since 1.30, GA 1.30+); Kyverno (YAML-native, Kubernetes-only, validate + mutate + generate + cleanup + image verification); OPA Gatekeeper (Rego, multi-stack); the choice (Kyverno is becoming the default for Kubernetes-only policy due to lower learning curve; Gatekeeper wins when you already use OPA across CI/CD and APIs).
- **Read:** Kyverno docs "Writing Policies"; Nirmata "10 Reasons Kubernetes Users Choose Kyverno."
- **Korean read:** Kakao 클라우드/플랫폼팀 정책 도입 후기 (search tech.kakao.com policy/Kyverno).
- **Lab:** install Kyverno. Write 10 policies: (1) deny `:latest` tag, (2) require labels `app`, `team`, `version`, (3) require resource requests AND limits, (4) require liveness + readiness probes, (5) deny `hostNetwork`, (6) require image registry to be your ECR account, (7) auto-add a default NetworkPolicy on Namespace creation, (8) verify image signatures via cosign, (9) clean up Jobs older than 7 days, (10) require `terminationGracePeriodSeconds >= 30`. Then implement #1, #3, #5 in OPA Gatekeeper using Rego to feel the language difference.

### Week 18 — Multi-tenancy and internal developer platforms

- **Concepts:** soft multi-tenancy (namespaces + RBAC + ResourceQuota + LimitRange + NetworkPolicy + PSA) vs hard (separate clusters); virtual clusters (vCluster); the "Platform-as-a-Product" mindset; internal developer platforms (Backstage); golden paths; self-service via GitOps + templates; the Korean precedent (Kakao DKOS, Toss internal platform, Coupang's container platform).
- **Read:** Manning *Cloud Native Spring in Action*, the platform chapter; Spotify Backstage docs; "Team Topologies" (book — read only the platform-team chapter).
- **Korean read:** 카카오 DKOS (Daum Kakao Container Service) if(kakao) talks; Toss SLASH "내부 개발자 플랫폼 만든 이야기."
- **Lab:** create namespaces `team-orders`, `team-inventory`, each with: ResourceQuota (10 CPU, 20 GiB memory), LimitRange (default 100m/256Mi), default-deny NetworkPolicy, PSA `restricted`, RBAC bindings to OIDC groups via EKS access entries. Bootstrap a Backstage instance on the cluster; build a software template that scaffolds a new Spring Boot service + Helm chart + GitHub Actions workflow + Argo CD Application — all from a single form.

### Week 19 — Observability integration at platform level

- **Concepts:** the three pillars (metrics/logs/traces) + the fourth (events/profiles); OpenTelemetry collector as the single agent; Prometheus federation vs Thanos vs Mimir; Loki vs CloudWatch Logs vs Datadog Logs; sampling strategies (head-based, tail-based); SLO definition (Google SRE workbook); alerting on burn rate.
- **Read:** Google SRE Workbook Ch. 5 "Alerting on SLOs."
- **Korean read:** Toss "관측성 도입기" SLASH 발표; 우아한형제들 "Datadog + Prometheus 운영 경험."
- **Lab:** consolidate to a single OTel Collector DaemonSet → Datadog (traces, logs) + Prometheus remote-write to Grafana Cloud (metrics). Define SLOs for each Mart-Kit service (99.9% availability, p99 < 300ms). Write multi-window multi-burn-rate alerts.

### Week 20 — Progressive delivery, feature flags, chaos

- **Concepts:** Argo Rollouts (canary, blue-green, experiments); flagger; feature flags (LaunchDarkly, Unleash, OpenFeature); chaos engineering with Litmus / Chaos Mesh; game days; the "production readiness review" checklist.
- **Korean read:** 카카오뱅크/토스 카오스 엔지니어링 도입기.
- **Lab:** add Argo Rollouts canary with analysis templates that abort if Datadog error-rate metric exceeds threshold. Run a chaos experiment: kill 30% of `inventory-service` pods every 2 minutes for an hour; verify SLO burn alert fires correctly.

### Week 21 — Multi-cluster and DR

- **Concepts:** federation patterns (Argo CD ApplicationSet across clusters); cluster API; Karmada / Open Cluster Management; cross-region failover; data layer constraints (Aurora Global, MSK MirrorMaker 2, ElastiCache Global Datastore); the 2022 카카오 1015 데이터센터 화재 lessons.
- **Read:** AWS "Disaster Recovery on AWS" whitepaper; Argo CD "Cluster Bootstrapping" docs.
- **Korean read:** 카카오 if(kakao)dev2022 1015 회고 — required reading.
- **Lab:** set up a second EKS cluster in another region; deploy Mart-Kit to both via one ApplicationSet; route traffic 90/10 via Route 53 weighted records; perform a region failover drill.

### Week 22 — Phase 3 capstone & retrospective

- **Capstone deliverable:** Mart-Kit running end-to-end with: Argo CD GitOps, Istio mTLS, Karpenter on Spot+On-Demand mix, ESO + Pod Identity for all credentials, Kyverno enforcing 10 policies, your custom `MartKitService` CRD/operator managing 2 of the 4 services, multi-tenant namespace isolation, Backstage golden-path scaffolding, SLO-based alerting via OTel + Datadog, Argo Rollouts canary, and a documented multi-region failover. Write a 5-page architecture decision record (ADR) bundle covering every major choice and its trade-offs — this is your portfolio.

---

## PHASE 4 (Optional) — Certification Track (Weeks 23–26)

You only need this if your career or employer values it. After Phase 3 you have far more practical skill than a CKA/CKAD demonstrates, but the certs are still a useful forcing function for kubectl-fluency under time pressure.

### Week 23 — CKAD (the easier one, do this first)

- **Resources:** Mumshad Mannambeth's CKAD course on KodeKloud (the de-facto best); the included `killer.sh` simulator (two free sessions with exam registration — these are *harder than the real exam*, by design); kubernetes.io docs; the `theplatformlab/CKA-Certified-Kubernetes-Administrator` GitHub for reference.
- **Plan:** spend 2 weeks. Do all KodeKloud labs at 1.5×; then `killer.sh` twice; then the exam. Aim for 80%+ in `killer.sh` before scheduling.
- **Korean discount:** the Linux Foundation runs Korea-specific 30–40% promo codes via 인프런 announcements and AWSKRUG newsletters periodically. The TTA Academy in Seoul offers the official LF instructor-led course in Korean.

### Week 24–25 — CKA

- **Resources:** Mumshad's CKA course; `killer.sh`; spend extra time on etcd backup/restore, kubeadm cluster bootstrap, network troubleshooting, RBAC. 2026 exam is on Kubernetes 1.32+ and includes Gateway API.
- **Lab discipline:** practice with `vim` keybindings in `kubectl edit`, alias `k=kubectl`, set `export do='--dry-run=client -o yaml'` so `k run nginx --image=nginx $do > pod.yaml` is muscle memory.

### Week 26 — Buffer / CKS optional

CKS (Certified Kubernetes Security Specialist) requires an active CKA and is genuinely useful if you'll specialize in K8s security (Falco, AppArmor, OPA, audit policies, supply chain). For a Spring Boot platform engineer, it's lower priority than continuing to build internal platform features.

---

## Resource Catalog (referenced throughout)

**Books (in priority order):**
1. *Kubernetes in Action*, 2e — Marko Lukša (Manning) — the canonical depth-first intro. Read Phase 1.
2. *Kubernetes Patterns*, 2e — Bilgin Ibryam, Roland Huß (O'Reilly) — design patterns. Read Phase 2.
3. *Cloud Native Spring in Action* — Thomas Vitale (Manning) — for the Spring Boot + K8s integration. Read Phases 1–2.
4. *Programming Kubernetes* — Stoneman & Hausenblas (O'Reilly) — for controllers. Phase 3.
5. *Production Kubernetes* — Josh Rosso et al. (O'Reilly) — for the Phase 2 mindset.
6. *Kubernetes Best Practices*, 2e — Brendan Burns et al.

**Official:**
- AWS EKS User Guide and the AWS EKS Best Practices Guide (`aws.github.io/aws-eks-best-practices`) — *this is the single most underrated resource for your goal*. Read it cover to cover during Phase 2.
- AWS EKS Workshop (`eksworkshop.com`).
- Karpenter docs (`karpenter.sh`).
- Spring Boot reference, "Production-ready features" + "Container images" sections.
- Kubernetes docs at `kubernetes.io/docs` (yes, all of it eventually).

**Courses:**
- KodeKloud Mumshad Mannambeth — CKA, CKAD, CKS (best hands-on). Used in Phase 4 but Phase 1 students benefit too.
- A Cloud Guru — "Amazon EKS Deep Dive" (Phase 2).
- Linux Foundation LFS258/LFD259 — official, but drier than KodeKloud.
- Udemy: Stephane Maarek's MSK course (for Phase 2 Kafka-on-EKS framing).
- 인프런 (Korean): "쉽게 시작하는 쿠버네티스" by 조훈/Ssup2 (입문용); "대세는 쿠버네티스 [초급~중급]" by 일프로 (실무 입문). 패스트캠퍼스 "백엔드 개발자를 위한 쿠버네티스 실전 활용" 강의.

**YouTube channels (subscribe all):**
- TechWorld with Nana — friendliest intros, weak on production depth.
- Anton Putra — best benchmarks, head-to-head comparisons (Karpenter vs CA, Argo CD vs Flux, etc.).
- Marcel Dempers ("That DevOps Guy") — best for self-hosted/from-scratch demos. Use in Phase 3.
- Just me and Opensource — practical infra walkthroughs.
- ContainerSolutions, Learnk8s, Cloud Native Computing Foundation — KubeCon talk archives.
- Korean: 데브원영 (DVWY) 카프카; 일프로 쿠버네티스; AWSKRUG official channel; 토스 SLASH; 우아한테크 / 우아콘.

**Newsletters (subscribe all in Week 1):**
- KubeWeekly (CNCF official).
- Last Week in Kubernetes Development.
- TLDR DevOps.
- AWS What's New (filter for EKS).
- The New Stack daily.

**Conference talk archives to mine:**
- KubeCon + CloudNativeCon (NA, EU, India, Japan) — search YouTube for the year you want.
- AWS re:Invent — the CON track (Containers). CON406 / CON312 / CON403 series each year.
- AWS Summit Seoul — annual, EKS sessions in Korean and English.
- Korean: **if(kakao)** 2018, 2019, 2020, 2021, 2022, 2023, 2025 — Cloud and DevOps tracks have ~30 hours of K8s content; **DEVIEW** (Naver) — annual, search for "쿠버네티스"; **Toss SLASH** — annual, search for EKS/K8s; **AWSKRUG meetups** monthly recordings on YouTube (Container 분과 is the gold one); **우아콘** (우아한형제들) annual; **NHN FORWARD**.

**Korean engineering blogs (RSS subscribe):**
- `toss.tech` — Toss
- `tech.kakao.com`, `tech.kakaopay.com`, `tech.kakaoenterprise.com`, `tech.kakaobank.com` — Kakao group
- `techblog.woowahan.com` (woowabros.github.io legacy) — 우아한형제들/배민
- `medium.com/daangn`, `medium.com/karrotmarket-tech`, `karrotmarket.tech` — 당근마켓
- `medium.com/coupang-engineering` — Coupang
- `helloworld.kurly.com` — 마켓컬리/Kurly
- `d2.naver.com` — Naver D2
- `tech.devsisters.com`, `engineering.linecorp.com/ko`, `engineering.linecorp.com` — LINE

**GitHub repos to study:**
- `aws/karpenter-provider-aws` — read the controller code in Phase 3.
- `kubernetes-sigs/kubebuilder` and the book.
- `argoproj/argo-cd`, `argoproj/argo-rollouts`.
- `kyverno/kyverno`, `open-policy-agent/gatekeeper-library`.
- `aws/eks-charts`, `aws/aws-load-balancer-controller`.
- `external-secrets/external-secrets`.
- `terraform-aws-modules/terraform-aws-eks` — your IaC foundation.
- `aws-ia/terraform-aws-eks-blueprints` — patterns library, especially Karpenter examples.
- `kubernetes-sigs/aws-iam-authenticator` (legacy reading), and Pod Identity Agent code in `aws/eks-pod-identity-agent`.
- `hjacobs/kubernetes-failure-stories` (now on Codeberg) and `k8s.af` — required Phase 2 reading.

**Failure stories / postmortems to read (Phase 2 Week 12 mandatory):**
- Monzo 2017 outage (Linkerd + etcd + missing endpoints).
- Grafana 2019 Cortex outage (Pod Priority cascading preemption).
- Preply 2020 DNS / conntrack postmortem.
- JW Player 2019 cryptominer in their cluster (RBAC lessons).
- Jetstack 2019 admission webhook → cluster outage.
- Reddit's 2023 "Pi Day" outage (CoreDNS, GKE — but lessons transfer).
- Datadog's March 2023 multi-region outage (systemd-networkd interaction, public retro).
- Zalando "A Million Ways to Crash Your Cluster" decks (DevOpsCon Munich 2018, Container Camp UK 2018).
- 카카오 1015 데이터센터 화재 회고 (if(kakao)dev2022 special track) — required for any Korean-context engineer.

---

## Caveats

- **EKS and the surrounding ecosystem move fast.** Pod Identity (re:Invent 2023), Karpenter 1.0 GA (2024), EKS Auto Mode (re:Invent 2024), and the EKS Capabilities announcements (re:Invent 2025, including KRO and tighter Argo CD/ACK integration) all change the "right answer" within 12-month windows. Always cross-check current docs vs the dates in this curriculum; tutorials older than ~18 months are often subtly wrong (dockershim references, aws-auth ConfigMap as the only access model, IRSA-only patterns).
- **The week numbers are estimates.** A working professional with strong Spring Boot fundamentals usually finishes Phase 1 in 4 weeks, Phase 2 in 7–8, Phase 3 in 8–10. A heavier learner load (vacations, ramp-up at a new job) can stretch this to 30 weeks without losing the spine.
- **Some opinionated calls in this curriculum are debatable.** Argo CD over Flux, Kyverno over Gatekeeper, Karpenter over Cluster Autoscaler, and "managed Kafka/Redis/Postgres over self-hosted" are defensible defaults but not universally correct. The trade-off boxes throughout the phases name the conditions under which the opposite choice wins.
- **The CNCF survey numbers and market-share statistics cited (Istio 62% / Linkerd 28% mesh share, 72% of Kubernetes users running a service mesh, etc.) come from third-party blog summaries of CNCF/Datadog 2024 reports.** Treat them as directional rather than precise. The qualitative trade-offs (Linkerd lighter, Istio more flexible) are robust.
- **Korean resource availability shifts.** Toss/Kakao/우아한형제들 publish irregularly; if a specific blog post URL referenced here is gone, search the blog domain for the topic (e.g., `site:toss.tech kubernetes`). The if(kakao) 2018–2025 talk archives at `if.kakao.com` and tech.kakao.com remain stable.
- **CKA/CKAD exam mechanics change.** The 2026 exam runs on Kubernetes v1.32+, includes Gateway API, removed dockershim references long ago, and dropped some legacy security topics that moved to CKS. Always read the official CNCF curriculum PDF before scheduling.
- **The "minimum viable" Phase 1 deliberately omits topics other curricula put first** (etcd internals, kubeadm bootstrap, scheduler internals, multiple container runtimes, networking from scratch with Flannel/Calico). These are CKA topics and Phase 4 territory — they don't help you ship a Spring Boot service to EKS faster. If you skip Phase 4, you may want to read Lukša Ch. 11 ("Understanding Kubernetes internals") in Phase 2 for satisfaction.
- **JVM tuning advice (`MaxRAMPercentage=75`, etc.) is a starting point, not a final answer.** Real tuning requires profiling under your actual load. Use the values as defaults, then iterate with JFR + Datadog JVM dashboards.
- **This curriculum assumes you have, or can easily get, an AWS account with budget for an always-on EKS cluster (~$150–300/month at small scale).** If not, substitute `kind` or `k3d` locally for Weeks 1–3 and provision EKS only when needed (Week 4 onward), tearing it down nightly with `terraform destroy` to control cost.