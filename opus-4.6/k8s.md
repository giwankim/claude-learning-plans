---
title: "Kubernetes Mastery for EKS"
category: "Infrastructure"
description: "24-week curriculum from K8s fundamentals to production EKS mastery with CKAD, CKA, and CKS certification milestones for Spring Boot engineers"
---

# Kubernetes mastery plan for Spring Boot engineers on EKS

**This 24-week curriculum takes a Kotlin/Spring Boot backend engineer from conceptual understanding to production mastery across operations, developer workflow, internals, and security — with CKAD, CKA, and CKS certifications as concrete milestones.** The plan assumes 10–15 hours per week of dedicated study and hands-on practice. Each phase builds on the last, interleaving theory, certification prep, and real-world project work specific to Spring Boot microservices on AWS EKS. Korean tech company case studies are woven throughout to ground each phase in production reality.

---

## Phase 1: Container fundamentals and Kubernetes architecture (Weeks 1–3)

**Goal**: Build a rock-solid mental model of containers, Kubernetes architecture, and the core API objects. Everything that follows depends on this foundation being deep, not superficial.

**Books to read in this phase**:
- *The Kubernetes Book* by Nigel Poulton (2025 Edition, ~300 pages) — read cover to cover. Updated annually and covers architecture, pods, deployments, services, RBAC, and troubleshooting. The single best starting book.
- *Kubernetes: Up and Running, 3rd Edition* by Burns, Beda, Hightower, Evenson (O'Reilly, 2022) — chapters 1–8. Written by Kubernetes co-creators, this provides the authoritative conceptual foundation.

**Course**: Begin KodeKloud's CKA course by Mumshad Mannambeth (Udemy, ~$15 on sale, 4.7/5, 200K+ students). Complete the first 30% covering cluster architecture, core concepts (pods, ReplicaSets, deployments, services, namespaces), and kubectl fundamentals. The browser-based labs are essential — do every single one.

**Hands-on project**: Set up a local learning environment using **kind** (Kubernetes in Docker) for fast cluster creation and **Minikube** for full-feature exploration with add-ons. Deploy a simple Spring Boot Kotlin application manually: write the Dockerfile (multi-stage build with `eclipse-temurin:21-jre-alpine`), create pod, deployment, service, and ConfigMap manifests by hand, and practice `kubectl` commands until they feel natural.

**Supplementary resources**: Watch TechWorld with Nana's free 3-hour Kubernetes crash course on YouTube for visual reinforcement. Read the first two parts of KakaoPay's "쓰기만 했던 개발자가 궁금해서 찾아본 쿠버네티스 내부" blog series, which explains K8s internals using a restaurant analogy — excellent for building intuition.

**Success indicators**: You can explain the roles of the API server, etcd, scheduler, controller manager, and kubelet from memory. You can create deployments, expose services, and debug basic pod failures using `kubectl describe` and `kubectl logs` without consulting documentation.

---

## Phase 2: Workload patterns and developer workflow (Weeks 4–6)

**Goal**: Master the full spectrum of Kubernetes workload types and establish a productive local development workflow for Spring Boot microservices.

**Books**:
- Continue *Kubernetes: Up and Running* — chapters 9–18 (DaemonSets, Jobs, ConfigMaps, Secrets, RBAC introduction, storage).
- Begin *Kubernetes Patterns, 2nd Edition* by Ibryam and Huß (O'Reilly, 2023) — Part I: Foundational Patterns and Part II: Behavioral Patterns. This book is available as a free e-book from Red Hat Developer and teaches you to think in Kubernetes-native design patterns. The 2nd edition adds security patterns and covers K8s 1.26+.

**Course**: Continue KodeKloud CKA course through the 60% mark, covering scheduling, monitoring, application lifecycle management, and cluster maintenance. Simultaneously start the KodeKloud CKAD course sections on pod design, configuration, and multi-container patterns.

**Spring Boot integration deep dive**: This is where your backend expertise meets Kubernetes.

Configure **Spring Boot Actuator health probes** properly. Add `spring-boot-starter-actuator`, enable liveness and readiness probe endpoints (`/actuator/health/liveness`, `/actuator/health/readiness`), and configure Kubernetes manifests with a **startup probe** (essential for JVM's slow startup — use `failureThreshold: 30, periodSeconds: 5` for a 150-second window), a liveness probe that checks only internal state (never external dependencies), and a readiness probe that can check critical dependencies. Run the actuator on a separate management port (8081) for security.

Set up **JVM container-aware settings**: Use `-XX:MaxRAMPercentage=75.0` with `-XX:ActiveProcessorCount` set explicitly (JVM CPU detection is unreliable when requests differ from limits). Set memory requests equal to limits (memory is incompressible — exceeding limits triggers OOMKill), but consider omitting CPU limits to avoid throttling or setting them much higher than requests.

Configure **graceful shutdown**: Set `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase=30s` in Spring Boot. Add a `preStop` lifecycle hook with `sleep 10` to handle the race condition between endpoint removal and SIGTERM delivery. Set `terminationGracePeriodSeconds` to at least 45 seconds (preStop sleep + shutdown timeout + buffer).

**Container image building**: Implement **Jib** (Google) in your `build.gradle.kts` — it builds optimized OCI images without a Docker daemon, creates efficient layers separating dependencies/resources/classes, and pushes directly to registries. Compare with Spring Boot's built-in **Buildpacks** (`./gradlew bootBuildImage`) — Jib produces smaller images (~127–214MB vs ~274MB) and builds faster, while Buildpacks offer an auto-tuned memory calculator and CDS support. Choose Jib for CI/CD speed; Buildpacks for zero-config convenience.

**Development workflow**: Set up **Skaffold** with Jib integration for a continuous build-deploy loop (`skaffold dev`). Try **Telepresence** for intercepting a single service locally while connected to cluster services — invaluable for debugging with your IDE.

**Korean case study**: Read Kakao's landmark 2018 post "kubernetes를 이용한 서비스 무중단 배포" on zero-downtime deployments — it covers the exact traffic flow through ingress → service → pods and the timing issues between pod termination and ingress updates that the preStop hook addresses.

**Success indicators**: You have a Spring Boot Kotlin microservice with properly configured health probes, graceful shutdown, and JVM container settings, building with Jib and deploying to a local kind cluster via Skaffold. You understand the difference between startup, liveness, and readiness probes and can explain why misconfigured liveness probes cause cascading restart storms.

---

## Phase 3: CKAD certification sprint (Weeks 7–9)

**Goal**: Pass the CKAD exam. The developer-focused certification solidifies your workload-level Kubernetes skills and gives you confidence before tackling administration.

**Primary prep resources**:
- Complete the **KodeKloud CKAD course** — finish all remaining sections, Lightning Labs, and all 3 mock exams.
- *Certified Kubernetes Application Developer (CKAD) Study Guide, 2nd Edition* by Benjamin Muschko (O'Reilly, 2024) — covers all exam objectives including deployment strategies, CRDs, Helm basics, and container image building. Work through every hands-on exercise.

**Exam details**: The CKAD is a 2-hour, online proctored, 100% performance-based exam (command-line tasks only, no multiple choice). Passing score is **66%**. It costs **$445** and includes 1 free retake plus **2 Killer.sh simulator sessions** (36 hours of access each). Current K8s version tested is v1.35.

**Practice strategy**: Complete KodeKloud mock exams first. Activate your first **Killer.sh** session 2 weeks before the exam — questions are deliberately harder than the real exam, which builds readiness. Use the second Killer.sh session 2–3 days before. Practice on **KillerCoda** (free, browser-based, created by the same team as Killer.sh — kubernetes.io itself migrated tutorials here after Katacoda shut down). Focus on speed: you need to solve ~17 questions in 120 minutes.

**Critical exam skills**: Master `kubectl` imperative commands (`kubectl run`, `kubectl create`, `kubectl expose`, `--dry-run=client -o yaml`), YAML editing speed with vim/nano, and Kubernetes documentation navigation (docs.kubernetes.io is allowed during the exam).

**Hands-on projects during prep**: Deploy a multi-service Spring Boot application with ConfigMaps, Secrets, resource limits, network policies, and Jobs/CronJobs. Practice Helm chart creation for your application.

**Success indicator**: Pass CKAD on first attempt. Typical preparation for developers with some K8s experience is 4–6 weeks; with the foundation from Phases 1–2, 3 weeks of focused prep is achievable.

---

## Phase 4: Cluster administration, networking internals, and CKA prep (Weeks 10–14)

**Goal**: Understand how Kubernetes works under the hood — scheduler, networking, storage, cluster lifecycle — and pass the CKA exam.

**Books**:
- *Kubernetes in Action, 2nd Edition* by Marko Lukša (Manning, ~704 pages) — the "Kubernetes Bible." The 2nd edition covers architecture deep dives, monitoring, tuning, scaling, and zero-downtime updates. Read Part II (core concepts deep dive) and Part III (advanced topics). This is the single most comprehensive Kubernetes book available.
- *Core Kubernetes* by Jay Vyas and Chris Love (Manning, October 2024, ~424 pages) — specifically dives into API server internals, etcd, scheduler algorithms, and controller manager mechanics. Essential for understanding the "why" behind Kubernetes behavior.
- *CKA Study Guide, 2nd Edition* by Benjamin Muschko (O'Reilly, 2025) — updated for the February 2025 curriculum changes that added Gateway API, Helm, Kustomize, CRDs/Operators, and expanded troubleshooting.

**Course**: Complete the KodeKloud CKA course (remaining 40%), focusing on cluster installation with kubeadm, networking (CNI, DNS, ingress), storage (PV/PVC, StorageClasses), troubleshooting, and the new 2025 topics (Gateway API, Helm/Kustomize, CRDs).

**Deep internals study**: This phase is where you go beyond "user" to "operator."

**Networking**: Understand the pod networking model (every pod gets a routable IP), how CNI plugins work (Calico uses BGP routing with iptables; Cilium uses eBPF for kernel-level packet processing), Service networking (kube-proxy modes: iptables vs IPVS), DNS resolution (`service-name.namespace.svc.cluster.local`), and Network Policies. Study the VPC CNI plugin specifically for EKS — it assigns VPC IP addresses directly to pods, enabling native VPC networking.

**Scheduler**: Study how the scheduler selects nodes (filtering → scoring → binding), node affinity/anti-affinity, taints and tolerations, pod topology spread constraints, and priority/preemption. Read the scheduler source code's algorithm overview.

**CRI/CNI/CSI**: Understand the plugin interfaces — Container Runtime Interface (containerd), Container Network Interface (CNI plugins), and Container Storage Interface (CSI drivers like EBS CSI).

**Landmark hands-on exercise**: Complete **Kubernetes the Hard Way** by Kelsey Hightower (GitHub, 46.5K stars, updated to K8s v1.32). This walks you through manually bootstrapping a cluster: generating TLS certificates, creating kubeconfig files, setting up etcd, control plane components, and worker nodes. It transforms your understanding from abstract to concrete. Use the iximiuz Labs pre-built playground if you want to explore the end-state interactively.

**CKA exam details**: 2-hour performance-based exam, passing score **66%**, ~15–17 questions. The **February 2025 curriculum update** significantly changed the exam — troubleshooting is now 30% of the score, and questions require SSHing into separate nodes. New topics include Gateway API, Helm, Kustomize, CRDs/Operators, and Cilium network policies.

**CKA exam domains and weights**:
- Troubleshooting — **30%**
- Cluster Architecture, Installation & Configuration — **25%**
- Services & Networking — **20%**
- Workloads & Scheduling — **15%**
- Storage — **10%**

**Korean case studies for this phase**:
- Kakao's "쿠버네티스 프로비저닝 툴과의 만남부터 헤어짐까지" — details their in-house KaaS (DKOS) and why they moved from Kubespray to a hard-way-style approach. Rich operational insights.
- Kakao's "Kubernetes 운영을 위한 etcd 기본 동작 원리의 이해" — deep dive into etcd for K8s operations, covering Raft consensus and cluster maintenance.
- LINE's "Building Large Kubernetes Clusters" — tested 1,019 nodes with 50,000 pods, covering etcd performance issues, scheduling problems, and cilium challenges.

**Success indicators**: Pass CKA on first attempt. You can bootstrap a cluster from scratch, troubleshoot node failures and networking issues, and explain how a pod goes from `kubectl apply` to running containers (API server → etcd → scheduler → kubelet → CRI → CNI).

---

## Phase 5: Production operations on EKS — GitOps, observability, and autoscaling (Weeks 15–19)

**Goal**: Build production-grade operational capabilities for Spring Boot microservices on AWS EKS, covering the full deployment pipeline, monitoring stack, and autoscaling.

**Books**:
- *Production Kubernetes* by Rosso, Lander, Brand, Harris (O'Reilly, 2021, 506 pages) — the definitive guide to running K8s in production at enterprise scale. Covers platform building, networking, security, policy management, and multi-cluster operations. Written by four VMware/Heptio engineers with real-world experience.
- *Cloud Native DevOps with Kubernetes, 2nd Edition* by Arundel and Domingus (O'Reilly, 2022) — excellent for the CI/CD and operational practices context.

### EKS mastery

**Essential resources**: Work through the **AWS EKS Workshop** (eksworkshop.com) — modular hands-on labs covering cluster setup, networking, autoscaling, observability, GitOps, and security. Study the **EKS Best Practices Guide** (aws/aws-eks-best-practices on GitHub, also at docs.aws.amazon.com) — covers security, reliability, networking, cost optimization, and Karpenter-specific guidance. Use the `hardeneks` CLI tool to audit your clusters against these recommendations.

**Cluster provisioning**: Learn **eksctl** (the official EKS CLI, using CloudFormation under the hood) for quick cluster creation, and **EKS Blueprints** (available in CDK and Terraform) for production-grade IaC with 50+ supported add-ons including Karpenter, ArgoCD, Prometheus, and the AWS Load Balancer Controller. The Blueprints framework implements security, HA, and scalability best practices by default.

**Key EKS components to master**:
- **AWS Load Balancer Controller**: Provisions ALBs via Ingress resources (Layer 7, path/host routing, WAF integration) and NLBs via Service type LoadBalancer (Layer 4). Since v2.14.0, it also supports Gateway API. Use IngressGroups to share ALBs across services and reduce costs.
- **Karpenter** (CNCF project): Provisions best-fit EC2 instances in real-time by talking directly to the EC2 API — bypassing ASGs entirely. Uses NodePool and EC2NodeClass CRDs. Typical results: **15–30% cost reduction** and scale-up latency dropping from minutes to tens of seconds. It handles node consolidation automatically (empty-node, multi-node, and single-node strategies). EKS Auto Mode (December 2024) is built on Karpenter.
- **EKS Pod Identity** (launched re:Invent 2023, "IRSA v2"): Simplified IAM role binding for pods without OIDC provider setup. Use for new clusters; IRSA remains valid for cross-platform needs.
- **EKS add-ons**: Manage CoreDNS, kube-proxy, VPC CNI, EBS CSI Driver, and Pod Identity Agent as managed add-ons for automatic updates.

**Architecture pattern**: Use a small stable managed node group (e.g., Graviton `c7g.medium`) for system workloads (CoreDNS, monitoring, ArgoCD) plus Karpenter for dynamic application workloads. This hybrid approach is the industry standard.

### GitOps with ArgoCD

**ArgoCD** is the recommended GitOps tool (CNCF Graduated, 20K+ GitHub stars). It provides a rich web UI with real-time application topology visualization, supports Helm/Kustomize/plain YAML, and manages multi-cluster deployments from a single instance. Key features to learn:
- **ApplicationSets**: Auto-generate ArgoCD Applications from templates using generators (Git directory, cluster, pull request). Essential for managing dozens of microservices.
- **ArgoCD Image Updater**: Monitors ECR for new image versions and commits updated tags to your Git repository (use the `git` write-back method in production).
- **Argo Rollouts**: Progressive delivery with canary and blue-green strategies. The Rollout CRD replaces standard Deployments, providing weighted traffic shifting, automated analysis (querying Prometheus metrics), and manual promotion gates. Integrates with AWS ALB for traffic splitting.

**Helm vs Kustomize**: Use Helm (~75% industry adoption) for packaging applications as distributable charts with full lifecycle management (install, upgrade, rollback). Use Kustomize (built into kubectl) for environment-specific overlays on top of Helm output. Using both together is increasingly common: Helm for packaging, Kustomize for environment customization, ArgoCD for GitOps delivery.

**CI/CD pipeline pattern**: GitHub Actions handles CI (build → test → Jib image build → push to ECR → update image tag in Git manifest repo) → ArgoCD handles CD (detects Git change → syncs to cluster → Argo Rollouts manages progressive delivery).

### Observability stack

Build a comprehensive monitoring stack for Spring Boot on EKS:

**Metrics**: Deploy the **kube-prometheus-stack** Helm chart (bundles Prometheus, Grafana, Alertmanager, kube-state-metrics, node-exporter). Spring Boot exposes metrics via **Micrometer** at `/actuator/prometheus`. Prometheus 3.0 (released at KubeCon NA 2024) adds native OpenTelemetry compatibility.

**Tracing**: Use **OpenTelemetry** — the 2nd most active CNCF project with all three signals (traces, metrics, logs) now stable. The OpenTelemetry Spring Boot Starter reached stable in 2024, providing out-of-the-box instrumentation for Spring MVC, WebFlux, JDBC, and HTTP clients. For the backend, **Grafana Tempo** stores traces in object storage (S3) without indexing — dramatically cheaper than Jaeger at scale. Spring Boot 4 will ship `spring-boot-starter-opentelemetry` as a single dependency for auto-instrumentation.

**Logging**: Use the **PLG stack** (Grafana Alloy + Loki + Grafana) over EFK for Kubernetes. Loki indexes only labels (not content), uses cheap S3 storage, and integrates natively with Prometheus metrics in Grafana dashboards. Note that Promtail was deprecated in February 2025 (EOL March 2026) — **Grafana Alloy** is the replacement collection agent and is 100% OTLP-compatible.

**AWS-managed alternatives**: Amazon Managed Prometheus (AMP) + Amazon Managed Grafana (AMG) provide serverless, fully managed alternatives. CloudWatch Container Insights adds EKS-specific network observability. Consider combining CloudWatch for operational alarms and AWS service integration with AMP/AMG for deep PromQL analytics.

**Korean case studies**:
- Woowahan's "우아한형제들의 Data on EKS 중심의 데이터 플랫폼 구축 사례" — comprehensive EKS platform with Karpenter, KEDA, Helm Operator, and Apache Yunikorn scheduler.
- LINE's "Who murdered my lovely Prometheus container in Kubernetes cluster?" — troubleshooting OOM kills on Prometheus in K8s, covering oom_score_adj, kubelet resource management, and memory estimation.
- Toss's "Kubernetes CPU 알뜰하게 사용하기" — practical CPU optimization achieving 2x traffic handling without additional servers.
- Toss's MSA observability post using K8s conntrack DaemonSets to map Kafka broker connections to pod names.

**Hands-on project**: Deploy a full Spring Boot MSA (3–5 services) on EKS with ArgoCD GitOps, Karpenter autoscaling, kube-prometheus-stack monitoring, Loki logging, Tempo tracing, and Argo Rollouts canary deployments. This single project integrates everything from this phase.

**Success indicators**: You can provision a production-grade EKS cluster with IaC, deploy microservices via ArgoCD with canary rollouts, diagnose performance issues using correlated metrics/traces/logs in Grafana, and right-size workloads using Karpenter and HPA.

---

## Phase 6: Security, advanced topics, and CKS certification (Weeks 20–24)

**Goal**: Master Kubernetes security, build custom operators, understand advanced scheduling, and optionally pass the CKS exam.

**Books**:
- *Certified Kubernetes Security Specialist (CKS) Study Guide* by Benjamin Muschko (O'Reilly, 2023) — covers all six exam domains with hands-on exercises.
- *Kubernetes Best Practices* by Burns, Villalba, Strebel, Evenson (O'Reilly, 2019) — patterns for monitoring, securing, managing upgrades, and rollouts.
- *Kubernetes Security and Observability* by Creane and Gupta (O'Reilly, 2021) — security posture and observability. Supplement with *Hacking Kubernetes* by Martin and Hausenblas for offensive/defensive perspectives.

### Security deep dive

**RBAC hardening**: Implement least-privilege service accounts for every microservice. Disable SA auto-mounting (`automountServiceAccountToken: false`) where not needed. Audit permissions with `kubectl auth can-i` and `rbac-lookup`. Per Red Hat's 2024 report, **67% of organizations delay deployments due to security misconfigurations** — most are RBAC-related.

**Network Policies**: Implement default-deny ingress/egress policies per namespace, then allow only required communication paths. On EKS, **Cilium** (CNCF Graduated 2024) provides L3/L4 + native L7 policies (HTTP, gRPC, DNS) with eBPF-based enforcement and **Hubble** for network flow visualization. Calico remains excellent for environments needing BGP integration.

**Pod Security Standards**: Apply `restricted` Pod Security Admission (PSA) to production namespaces (`pod-security.kubernetes.io/enforce=restricted`). PSA replaced the deprecated PodSecurityPolicy (removed in K8s v1.25) and enforces three levels: Privileged, Baseline, and Restricted.

**Policy-as-code**: Deploy **Kyverno** (CNCF Graduated 2024) for Kubernetes-native policy enforcement using pure YAML — lower barrier than OPA/Gatekeeper's Rego language. Kyverno validates, mutates, generates, and cleans up resources. It has built-in Cosign/Sigstore image verification. Use OPA/Gatekeeper if you need cross-platform policy (Terraform, Envoy, CI/CD pipelines).

**Runtime security**: Deploy **Falco** (CNCF Graduated 2024) as a DaemonSet for real-time syscall monitoring via eBPF. It detects container escapes, unexpected shell spawning, suspicious network connections, and privilege escalation with **<2.5% CPU overhead**. Route alerts via Falcosidekick to Slack or PagerDuty.

**Supply chain security**: Integrate **Trivy** (Aqua Security) into CI/CD pipelines for image vulnerability scanning (`trivy image myapp:latest` — exits non-zero on critical findings to fail builds). Deploy the Trivy Operator in-cluster for continuous scanning of running workloads. Implement **Cosign** (Sigstore) for container image signing in your build pipeline, and enforce signature verification at admission time with Kyverno policies.

**Secrets management**: Deploy **External Secrets Operator** to sync secrets from AWS Secrets Manager into native K8s Secrets with configurable refresh intervals. This works on both EC2 nodes and Fargate (unlike the Secrets Store CSI Driver). Encrypt etcd at rest.

**CIS benchmarks**: Run **kube-bench** (Aqua Security) as a Kubernetes Job to automate CIS benchmark compliance checks on worker nodes (cannot inspect managed EKS control plane). Integrate into CI/CD for continuous compliance auditing.

**Korean case study**: Toss's "경계 보안부터 제로트러스트 보안까지" post details their security journey using Falco for container runtime security in their IDC, GuardDuty for EKS container security monitoring, and their zero-trust architecture implementation.

### Advanced topics

**Custom operators**: Build a Kubernetes operator using the **Fabric8 Kubernetes Client** with Kotlin. Start with a simple operator that watches a custom CRD and reconciles state (e.g., a CRD that provisions Spring Boot microservice infrastructure). This is the capstone skill that distinguishes K8s power users.

**Scheduler deep dive**: Study the scheduling framework's extension points (QueueSort, Filter, Score, Reserve, Bind), implement a custom scheduler plugin, and understand how Karpenter's "schedule-then-provision" model inverts the traditional "provision-then-schedule" approach.

**Spring Cloud Kubernetes**: Evaluate whether you need it. For most teams, native K8s service discovery via DNS (`http://service-name:port`) is sufficient. Spring Cloud Kubernetes's primary value is **hot ConfigMap/Secret reload without pod restarts** and smooth migration from Spring Cloud Netflix (Eureka). If you use a service mesh (Istio, Linkerd), let infrastructure handle load balancing.

**Production incident response**: Develop runbooks for common K8s failures: CrashLoopBackOff diagnosis, OOMKilled analysis, node NotReady debugging, certificate expiration, etcd compaction issues, and stuck namespace deletion. Practice these scenarios in a dedicated chaos engineering environment.

### CKS certification (stretch goal)

**Prerequisites**: Must hold valid CKA certification. The CKS is 2 hours, 15–20 performance-based tasks, **67% passing score**, $445 (includes 1 retake + 2 Killer.sh sessions). The October 2024 curriculum refresh added SBOM generation and Cilium network policies.

**Six exam domains**: Cluster Setup (15%), Cluster Hardening (15%), System Hardening (15%), Minimize Microservice Vulnerabilities (20%), Supply Chain Security (20%), Monitoring/Logging/Runtime Security (15%). You must be hands-on comfortable with Falco, Trivy, AppArmor, Seccomp, audit logging, and OPA/Gatekeeper or Kyverno.

**Prep**: KodeKloud CKS course + Killer.sh simulator + KillerCoda practice scenarios. Typical preparation after CKA is 4–6 weeks.

**Success indicators**: You can implement defense-in-depth across the entire stack (build-time scanning → admission control → runtime detection → network segmentation → secrets encryption). You can build custom operators. You can lead production incident response for Kubernetes-based systems.

---

## Certification timeline at a glance

| Week | Milestone | Certification |
|------|-----------|--------------|
| 1–3 | Foundation: architecture, core objects, local cluster | — |
| 4–6 | Workloads, Spring Boot integration, dev workflow | — |
| 7–9 | **CKAD exam** (developer-focused, take Week 9) | **CKAD** ✓ |
| 10–14 | Administration, networking, internals, K8s the Hard Way | — |
| 13–14 | **CKA exam** (administrator-focused, take Week 14) | **CKA** ✓ |
| 15–19 | EKS production ops, GitOps, observability | — |
| 20–24 | Security, advanced topics, operator development | — |
| 22–24 | **CKS exam** (security specialist, take Week 24) | **CKS** ✓ (stretch) |

Note that certification validity changed to **2 years** (down from 3) for certs earned after April 2024. All exams include 1 free retake and 2 Killer.sh simulator sessions.

---

## Essential book progression

| Phase | Book | Level | Why it matters |
|-------|------|-------|----------------|
| 1 | *The Kubernetes Book* (Poulton, 2025 Ed.) | Beginner | Fastest on-ramp, updated annually |
| 1–2 | *Kubernetes: Up and Running, 3rd Ed.* (Burns et al., 2022) | Beginner–Intermediate | Written by K8s creators, authoritative concepts |
| 2 | *Kubernetes Patterns, 2nd Ed.* (Ibryam/Huß, 2023) | Intermediate | Design pattern thinking, free from Red Hat |
| 3 | *CKAD Study Guide, 2nd Ed.* (Muschko, 2024) | Intermediate | Exam-aligned exercises |
| 4 | *Kubernetes in Action, 2nd Ed.* (Lukša, Manning) | Intermediate | The "K8s Bible" — 704 pages, most comprehensive |
| 4 | *Core Kubernetes* (Vyas/Love, 2024) | Intermediate | Internals: API server, etcd, scheduler |
| 4 | *CKA Study Guide, 2nd Ed.* (Muschko, 2025) | Intermediate | Updated for Feb 2025 curriculum |
| 5 | *Production Kubernetes* (Rosso et al., 2021) | Advanced | Enterprise operations, the production bible |
| 6 | *CKS Study Guide* (Muschko, 2023) | Advanced | Security certification prep |

---

## Course and platform recommendations ranked by purpose

**For certification prep** (highest priority): KodeKloud courses by Mumshad Mannambeth are the undisputed gold standard. The CKA course on Udemy ($15 on sale, 4.7/5, 200K+ students) with integrated browser-based labs and mock exams has the highest documented pass rate. Pair with Killer.sh (included with exam registration) and KillerCoda (free).

**For deep understanding**: *Kubernetes Mastery* by Bret Fisher and Jérôme Petazzoni on Udemy ($15 on sale) focuses on practical deep understanding rather than exam prep. The Linux Foundation's LFS258/LFD259 courses ($299 each, or $645 bundled with exam) are official training with in-browser labs — best when employer-funded.

**For hands-on practice**: KillerCoda provides free browser-based K8s environments (Katacoda's spiritual successor). Use kind/k3d locally for fast iteration. Complete Kubernetes the Hard Way (GitHub, Kelsey Hightower) during Phase 4 — still the best way to understand internals, now updated to K8s v1.32 with ARM64 support.

**For free introduction**: Linux Foundation's LFS158x on edX (free audit) provides a solid starting point. TechWorld with Nana and KodeKloud YouTube channels offer excellent free video content.

---

## Korean tech company blog reading list

These posts provide invaluable production experience that textbooks cannot replicate. Read them alongside the relevant phase:

**Woowahan (배민)**: "쿠버네티스를 이용해 테스팅 환경 구현해보기" (EKS adoption, Helm, Jenkins CI/CD) and the AWS Korea blog post on their Data on EKS platform (Karpenter, KEDA, Yunikorn scheduler) — both essential for understanding Korean-scale EKS operations.

**Kakao**: Three must-reads — "kubernetes를 이용한 서비스 무중단 배포" (zero-downtime deployments, the definitive Korean reference), "Kubernetes 운영을 위한 etcd 기본 동작 원리의 이해" (etcd deep dive for operations), and "쿠버네티스 프로비저닝 툴과의 만남부터 헤어짐까지" (their DKOS KaaS platform journey).

**Toss**: "Kubernetes CPU 알뜰하게 사용하기" (CPU resource optimization) and "경계 보안부터 제로트러스트 보안까지" (Falco + GuardDuty + zero-trust architecture on K8s).

**LINE**: "Building Large Kubernetes Clusters" (1,019 nodes / 50,000 pods stress testing) and the Prometheus OOMKill investigation — both reveal issues you only encounter at scale.

**Community**: Join **Cloud Native Seoul** (CNCF chapter, regular meetups at Google Startup Campus) and attend **KCD Seoul** (annual conference, 2025 edition on May 22 at Spigen HQ). The Korean K8s community grew from ~10 meetup attendees in 2016 to hundreds of conference participants today.  Follow **44bits.io** (Subicura and team) for Korean-language container/K8s tutorials, and consider the **Inflearn roadmap** "44bits와 함께하는 DevOps 워크숍: 도커부터 쿠버네티스까지." The Korean-language book "컨테이너 인프라 환경 구축을 위한 쿠버네티스/도커" by 조훈 et al. (GitHub: sysnet4admin/_Book_k8sInfra) provides excellent hands-on labs.

---

## Ongoing learning infrastructure

**Newsletters**: Subscribe to **KubeWeekly** (CNCF's official weekly digest), **LWKD** (Last Week in Kubernetes Development — code-level changes, deprecations, release schedules), and **DevOps Weekly** for broader context.

**Podcasts**: **Kubernetes Podcast from Google** (biweekly, K8s news and community interviews), **Ship It!** (Changelog — everything after `git push`), and **KubeFM** (deep dives and expert interviews).

**YouTube**: **CNCF channel** (all KubeCon recordings posted free within days of each event), **TechWorld with Nana** (clear animations for complex topics), **Viktor Farcic / DevOps Toolkit** (opinionated deep dives and tool comparisons), and **Jeff Geerling** (K8s on Raspberry Pi, K8s 101 series).

**Community**: Join the **Kubernetes Slack** (slack.k8s.io — 170+ channels, most active K8s community), subscribe to **r/kubernetes** on Reddit, and browse **discuss.kubernetes.io** for contributor-level discussions.

---

## Conclusion

The most important insight in this plan is sequencing: **CKAD before CKA before CKS mirrors the natural learning gradient** from application-level concerns to infrastructure to security. Each certification serves as both a milestone and a forcing function that ensures no knowledge gaps. The Spring Boot integration work in Phase 2 is the highest-leverage phase for a Kotlin backend engineer — properly configured health probes, JVM container settings, and graceful shutdown prevent the most common production incidents. Korean tech companies' blog posts reveal that the gap between "running on Kubernetes" and "running well on Kubernetes" is primarily about resource tuning (Toss's CPU optimization), zero-downtime deployment mechanics (Kakao's SIGTERM timing), and observability depth (LINE's Prometheus debugging). Master these operational details alongside the certifications, and you will be equipped to own Spring Boot microservices on EKS from commit to production incident resolution.