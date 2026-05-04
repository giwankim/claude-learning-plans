---
title: "Terraform Mastery for a Senior Backend Engineer"
category: "Infrastructure"
description: "Two-track Terraform plan (6-9 month mastery and 8-10 week distilled) for a Kotlin/Spring Boot/Kafka engineer — AWS-first then multi-cloud, anchored on Brikman's Terraform: Up & Running with OpenTofu coverage and the 2026 Associate 004 + Authoring/Operations Professional certs."
---

# Terraform Mastery Learning Plan
**Tailored for a Senior Backend Engineer (Kotlin / Spring Boot / Kafka, 10y) — AWS-first, Multi-Cloud Later**

---

## TL;DR

- **Mastery track (6–9 months, ~8–12 hrs/week):** Work through *Terraform: Up & Running* 3rd ed. (Brikman) end-to-end as the spine, layer in *Terraform in Action* (Winkler) and *Mastering Terraform* (Tinderholt) for advanced/multi-cloud chapters, drive every phase with a corresponding AWS project (S3 → multi-tier VPC/RDS/ALB → modules → multi-env state → GitHub Actions → tests → EKS → multi-cloud refactor → capstone), and finish with HashiCorp Terraform **Associate 004** + the new **Authoring & Operations Professional** exam.
- **Distilled track (8–10 weeks, ~10 hrs/week):** Brikman Ch. 1–8 + KodeKloud "Terraform for Beginners" + Zeal Vora's *Terraform Associate 2026* labs, three projects (single resource → modular multi-tier VPC/RDS-Aurora/ALB → CI/CD with GitHub Actions OIDC + tflint/checkov + native `terraform test`), pass the Associate exam.
- **Strategic notes for 2026:** Terraform is under BSL (HashiCorp/IBM); **OpenTofu** (Linux Foundation, MPL 2.0) is a near drop-in replacement forked from Terraform 1.5.x and now diverging (native state encryption, write-only attributes). For your internal-use case either works — learn Terraform as the canonical syntax, but keep OpenTofu CLI installed and run your test suite against both. **HCP Terraform's free tier ended March 31, 2026**, so plan to learn the open-source workflow (S3+DynamoDB backend, GitHub Actions, Atlantis or Spacelift) rather than relying on TFC for hands-on practice.

---

## Key Findings (Used to Shape the Plan)

1. **Best primary book is still *Terraform: Up & Running, 3rd Edition* (Brikman, O'Reilly, 2022).** It is structured almost exactly like the project progression you described and contains code samples in [brikis98/terraform-up-and-running-code](https://github.com/brikis98/terraform-up-and-running-code). Chapters map cleanly to your phases: Ch. 2 syntax → Ch. 3 state → Ch. 4 modules → Ch. 5 loops/conditionals/zero-downtime → Ch. 6 secrets → Ch. 7 multiple providers/multi-region/multi-cloud + EKS → Ch. 8 production-grade modules → Ch. 9 testing → Ch. 10 team workflow.
2. **Best secondary book for advanced patterns: *Terraform in Action* (Winkler, Manning).** Especially Part 3 (Ch. 9 zero-downtime, Ch. 10 testing/refactoring, Ch. 11 writing custom providers, Ch. 13 secrets). Examples in JS/Go.
3. **Best multi-cloud companion: *Mastering Terraform* (Tinderholt, Packt 2024).** Uniquely treats AWS, Azure, and GCP equally with parallel chapters per cloud × per paradigm (VM/IaaS, Kubernetes/EKS-AKS-GKE, serverless/Lambda-Functions-CloudFunctions). This is your reference when refactoring AWS code to be multi-cloud-portable.
4. **Certification reality (May 2026):** Associate **003 retired January 8, 2026**. The current path is **Associate 004**, plus the new **Terraform Authoring and Operations Professional** (lab-based). HashiCorp's official Learning Path for 004 is at `developer.hashicorp.com/terraform/tutorials/certification-004`.
5. **OpenTofu vs Terraform (relevant 2026 context):**
   - Terraform: Business Source License (BSL 1.1) since v1.6, owned by HashiCorp (IBM since Feb 27, 2025). Permitted for internal use; the BSL only restricts hosting Terraform as a competing managed service.
   - OpenTofu: MPL 2.0 fork from Terraform 1.5.6, Linux Foundation governance, drop-in CLI replacement (`tofu init/plan/apply`). Has shipped some features ahead of (or only in) Terraform: client-side state encryption, early adoption of community features.
   - Practical recommendation: **author code as if Terraform/OpenTofu are interchangeable** (avoid bleeding-edge HCP-only features in modules you want portable), pin provider versions, and lock-test against both.
6. **Best blog series:** Gruntwork's [*A Comprehensive Guide to Terraform*](https://www.gruntwork.io/blog/a-comprehensive-guide-to-terraform) (the seed of *Terraform: Up & Running*) and Anton Babenko's [`weekly.tf`](https://www.weekly.tf/) newsletter + free [*Terraform Best Practices*](https://www.terraform-best-practices.com/) ebook (translated into Korean — the 🇰🇷 flag in the repo's translation list confirms this).
7. **Best open-source repos to read like a textbook:** `terraform-aws-modules/*` (Babenko-led; the VPC, S3, EKS, RDS-Aurora, Lambda, MSK-Kafka modules are reference quality and have been provisioned >2B times); `aws-ia/terraform-aws-eks-blueprints` (AWS's own opinionated EKS patterns); `cloudposse/terraform-aws-components` and `cloudposse/terraform-null-label` (the `context.tf` naming-and-tagging pattern — battle-tested at scale).
8. **Korean resources do exist** (good news for you). The two best: *Terraform Associate 시험으로 배우는 Terraform 기초 강의* on Inflearn (covers 003/004 objectives in Korean with AWS labs), and the DevOpsArt *DevOps : Infrastructure as Code with Terraform and AWS 기본편 + 중급/활용편* series on Inflearn (`terraform101.inflearn.devopsart.dev` and `intermediate.inflearn.devopsart.dev`). Anton Babenko's Terraform Best Practices ebook is also officially translated to Korean.

---

# Part 1 — Mastery Roadmap (6–9 Months, Open-Ended)

Assumes ~8–12 hrs/week. Each phase has a **Theory** block (resources to read/watch in order) and a **Project** (build/ship). All projects belong in one GitHub mono-repo `tf-mastery/` you keep through the whole journey, with a `phaseN-*` directory for each milestone — that becomes your portfolio artifact.

### Phase 0 — Foundations & Mental Model (Week 1, 1 week)

**Why this phase:** As a backend engineer used to JVM build tooling and declarative app config (Spring profiles, Kafka topic configs), you'll absorb HCL fast — but the *immutable infrastructure* mental shift and *state-as-source-of-truth* idea need explicit framing.

**Theory (read in this order):**
1. Brikman, *Terraform: Up & Running* 3rd ed., **Chapter 1** ("Why Terraform") — IaC categories, declarative vs. procedural, mutable vs. immutable. ~1 hr.
2. HashiCorp Learn: [What is IaC with Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/infrastructure-as-code) and [Install Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli). ~30 min.
3. Gruntwork blog: *A Comprehensive Guide to Terraform* — Part 1 (*Why we use Terraform and not Chef/Puppet/Ansible/Pulumi/CloudFormation*). ~30 min.
4. Read the OpenTofu vs Terraform decision: Spacelift's [comparison](https://spacelift.io/blog/opentofu-vs-terraform) and the OpenTofu landing page. **Decision to make now:** install both `terraform` (latest 1.x) and `tofu` (latest) via tfenv/tofuenv; use Terraform syntax in code, but periodically run `tofu plan` against your modules to check portability.

**Project 0 — Toolchain bootstrap:**
- Install Terraform, OpenTofu, AWS CLI v2, `tflint`, `terraform-docs`, `pre-commit`, `tfenv`/`tofuenv`.
- Configure an AWS sandbox account with an IAM user limited to your sandbox plus a billing alarm at $20.
- Set up `pre-commit-terraform` hooks (`terraform_fmt`, `terraform_validate`, `terraform_tflint`, `terraform_docs`) — Anton Babenko's standard config.
- Outcome: `terraform -version`, `tofu -version`, `aws sts get-caller-identity` all green; `pre-commit run --all-files` works.

---

### Phase 1 — HCL Fundamentals & The Core Workflow (Weeks 2–3, ~2 weeks)

**Theory:**
- Brikman **Chapter 2** ("An Introduction to Terraform Syntax") — providers, resources, variables, outputs, data sources, the `count`/`for_each` teasers, deploying a single EC2 + ASG + ALB. This is the highest-signal chapter in the whole book.
- HashiCorp tutorials: the entire [AWS Get Started collection](https://developer.hashicorp.com/terraform/tutorials/aws-get-started) (8 short tutorials, ~3 hrs total) — they validate the Brikman material with the official voice.
- Winkler, *Terraform in Action*, **Chapter 2** ("Life Cycle of a Terraform Resource") — explains CRUD-on-resources and how plans become DAGs (use `terraform graph` + Graphviz). Pair this with Winkler **Chapter 3** ("Functional Programming") for `for` expressions, `for_each`, locals, type constraints.
- Official docs to bookmark: [Configuration Language overview](https://developer.hashicorp.com/terraform/language), [Built-in Functions](https://developer.hashicorp.com/terraform/language/functions), [AWS Provider docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs).

**Project 1 — "Hello, S3 + EC2" with proper structure (matches your Phase 1 spec):**
- One root module that creates: an S3 bucket (versioned, server-side encrypted, public access blocked), one EC2 instance (Amazon Linux 2023, t3.micro, in default VPC) with a user-data script that runs a tiny "hello" HTTP server, and a security group.
- All values parameterized through `variables.tf` with `type` constraints and `validation` blocks (e.g., bucket name must be lowercase, instance type must be in approved list).
- Outputs: bucket ARN, instance public IP, SSH command.
- Practice the loop: `init → fmt → validate → plan → apply → destroy`. Run `terraform graph | dot -Tpng` to *see* the dependency graph (Winkler's tip).
- **Twist for portfolio quality:** also implement the same thing in a `phase1-opentofu/` directory with `tofu` and confirm bit-for-bit identical state output.

**Time:** ~15 hrs reading + ~10 hrs project.

---

### Phase 2 — State Management Deep Dive (Week 4, ~1 week)

**Why now:** Before you build anything bigger, you must internalize state. This is where 90% of real-world Terraform pain happens.

**Theory:**
- Brikman **Chapter 3** ("How to Manage Terraform State") — local vs. remote backends, S3 + DynamoDB locking, file layout (`global/`, `stage/`, `prod/`), `terraform_remote_state` data source.
- Winkler, *Terraform in Action*, **Chapter 6** ("Terraform with Friends") — building an S3 backend module from scratch, the hidden mechanics of partial backend init.
- HashiCorp docs: [Backend block](https://developer.hashicorp.com/terraform/language/backend), [State CLI commands](https://developer.hashicorp.com/terraform/cli/commands/state) (read every subcommand: `list`, `mv`, `rm`, `pull`, `push`, `replace-provider`).
- Spacelift's [Importing Existing Infrastructure](https://spacelift.io/blog/importing-exisiting-infrastructure-into-terraform) — covers both `terraform import` CLI and the **Terraform 1.5+ `import` block** (with `terraform plan -generate-config-out=…` for autogenerated config). This is now the modern import workflow.
- Security: read HashiCorp's [Sensitive Data in State](https://developer.hashicorp.com/terraform/language/state/sensitive-data) note and decide on KMS encryption for your S3 state bucket.

**Project 2 — Bootstrap a state backend and migrate Phase 1:**
- Write a tiny `bootstrap/` module that creates an S3 bucket with versioning + KMS-CMK encryption + public-block, plus a DynamoDB table for locking. Apply it once with local state (chicken-and-egg solved Brikman-style).
- Migrate Project 1 to use this remote backend (`terraform init -migrate-state`).
- Manually create an EC2 instance via the AWS console, then **adopt it into Terraform** twice: once with `terraform import`, once with the declarative `import { to = … id = … }` block + `-generate-config-out`. Compare ergonomics.
- Practice: introduce a deliberate refactor (move a resource into a module), then use `moved {}` blocks (Terraform 1.1+) to move state without destroying.

---

### Phase 3 — Multi-Tier Web App on AWS (Weeks 5–7, ~3 weeks)

**Why this phase:** Bridges syntax knowledge to real architecture. Your Kafka/distributed-systems experience pays off here.

**Theory:**
- Brikman **Chapter 5** first half ("Terraform Tips & Tricks: Loops, If-Statements, Deployment, and Gotchas") — `count`, `for_each`, `dynamic` blocks, conditional resources, ternary expressions.
- AWS networking primer (skim if you already know VPCs): [AWS VPC docs — Default and Non-Default VPCs](https://docs.aws.amazon.com/vpc/latest/userguide/default-vpc.html) and the [terraform-aws-modules/vpc](https://github.com/terraform-aws-modules/terraform-aws-vpc) README. This module has 126M downloads — read its inputs/outputs carefully; it's the de-facto reference for VPC topology in Terraform.
- For the database: read the [terraform-aws-modules/rds-aurora](https://github.com/terraform-aws-modules/terraform-aws-rds-aurora) README + the `examples/mysql/main.tf`. **Directly relevant to your Aurora MySQL day job** — you'll see writer/reader endpoints, IAM-managed master password, parameter groups, performance insights, enhanced monitoring, autoscaling, and cluster activity streams.
- Tinderholt, *Mastering Terraform*, **Chapter 7** ("Getting Started on AWS – Building Solutions with AWS EC2") — alternative explanation, useful diagrams.

**Project 3 — Production-style 3-tier on AWS (still single root module, no custom modules yet):**
- VPC: 3 public subnets, 3 private app subnets, 3 private DB subnets across 3 AZs; IGW; one NAT GW per AZ for resilience (cost note: ~$32/mo per NAT-GW-hour — use a single NAT for cost in this phase, then make it `count`-driven).
- ALB with HTTPS listener (use ACM cert from a Route53 hosted zone you already own, or self-signed for learning).
- ASG of EC2s (or Fargate ECS — pick one; ASG is closer to Brikman's examples) running a Spring Boot Kotlin "echo" service in a Docker container, behind the ALB. Use `for_each` to vary instance config per env.
- **Aurora MySQL cluster**, 1 writer + 1 reader, `db.t4g.medium`, in the DB subnets, with security group rules locked to the app SG only, master password managed by AWS Secrets Manager (`manage_master_user_password = true`), 7-day backup retention, performance insights ON.
- App talks to RDS via the cluster endpoint pulled from a `data "aws_secretsmanager_secret_version"` data source.
- Output: ALB DNS, RDS endpoint, application URL.

**Time:** ~12 hrs reading + ~25 hrs project.

---

### Phase 4 — Modules: Composition, Versioning, Registry (Weeks 8–9, ~2 weeks)

**Theory:**
- Brikman **Chapter 4** ("How to Create Reusable Infrastructure with Terraform Modules") — module inputs/outputs/locals, file paths, inline blocks, module versioning.
- Brikman **Chapter 8** ("Production-Grade Terraform Code") — *the* chapter on module quality: small modules, composable modules, testable modules, versioned modules; the Gruntwork "production-grade infrastructure checklist" is gold.
- Winkler **Chapter 4** ("Deploying a multi-tiered web application in AWS") — the same exercise as your Phase 3 but cast as nested modules (root → networking, database, autoscaling).
- Read the source of three exemplary modules end-to-end (an evening each):
  - `terraform-aws-modules/vpc` — clean variable design, optional features via flags.
  - `terraform-aws-modules/rds-aurora` — sophisticated `for_each` over instances, conditional creation patterns.
  - `cloudposse/terraform-null-label` and the `context.tf` pattern — naming/tagging at scale.
- Babenko's free ebook: [Terraform Best Practices](https://www.terraform-best-practices.com/) — sections on module structure, naming, code style. ~2 hrs.

**Project 4 — Refactor Phase 3 into versioned modules:**
- Split into: `modules/network/` (VPC + subnets + routes + NAT), `modules/security/` (SGs as a separate concern with an explicit "consumer SG ID" input), `modules/aurora-mysql/`, `modules/app-cluster/` (ALB + ASG + launch template).
- Each module gets `README.md` (auto-generated by `terraform-docs`), `variables.tf` with descriptions and validations, `outputs.tf`, an `examples/` subdirectory with a runnable `main.tf` example, and a `versions.tf` with `required_providers` and version pins.
- Tag each module repo with semver: `v0.1.0` first release. Source one of them via Git ref (`source = "git::https://...?ref=v0.1.0"`) from your live infra to feel real version pinning.
- Adopt Cloud Posse's `context.tf` pattern in one module to internalize the convention.

---

### Phase 5 — Multi-Environment Layout & Workspaces vs. Folder-per-Env vs. Terragrunt (Weeks 10–11, ~2 weeks)

**Theory:**
- Brikman **Chapter 3** revisited (the *Isolation via Workspaces* vs. *Isolation via File Layout* sections) — the canonical comparison.
- Brikman blog post series: *How to manage multiple environments with Terraform* (linked in `gruntwork-io/intro-to-terraform`) — workspaces, branches, and Terragrunt with the comparison table at the end.
- Spacelift: [Terragrunt vs Terraform](https://spacelift.io/blog/terragrunt-vs-terraform) and Axel Mendoza's [*Why I Use Terragrunt Over Terraform/OpenTofu in 2025*](https://www.axelmendoza.com/posts/terraform-vs-terragrunt/) — covers the new **Terragrunt Stacks** feature (post v0.80) which materially changed the trade-off.
- HashiCorp docs: [Workspaces](https://developer.hashicorp.com/terraform/language/state/workspaces). Note CLI workspaces ≠ HCP Terraform workspaces; this is a common confusion.
- Read **Terragrunt docs**: [`terragrunt.hcl`](https://terragrunt.gruntwork.io/docs/), the `dependency` block, `read_terragrunt_config`, and the `stacks` documentation.

**Project 5 — Three environments (dev/stage/prod) with isolated state:**
- Adopt the **folder-per-environment** layout (Brikman's recommendation for production):
  ```
  live/
    dev/    {network,db,app}/{terragrunt.hcl, terraform.tfvars}
    stage/  …
    prod/   …
  modules/  (your Phase 4 modules consumed by live)
  ```
- Use **Terragrunt** to DRY the backend, providers, and common inputs. Each env has its own S3 state key under one bucket.
- Make instance sizes/replica counts vary per env (dev = small/single AZ, prod = bigger/multi-AZ). Use Terragrunt's `read_terragrunt_config` + `_envcommon/` overrides.
- Apply in order: `dev` → `stage` → `prod`. Practice promoting a module version from dev to prod by editing the `source = "...?ref=v0.2.0"` ref, not the code.
- **Bonus:** also build a `phase5-workspaces/` showing the same env separation using CLI workspaces, write up a 1-pager on which approach you'd pick at a 50-person company and why.

---

### Phase 6 — CI/CD with GitHub Actions, OIDC, PR Previews (Weeks 12–13, ~2 weeks)

**Theory:**
- Brikman **Chapter 10** ("How to Use Terraform as a Team") — the team workflow, branching, PR flow, the "deploy from CI" pattern, what *not* to do.
- HashiCorp tutorials: [Manage HCP Terraform with the CLI-driven workflow](https://developer.hashicorp.com/terraform/tutorials/automation) — even though you'll skip HCP Terraform paid tier, the patterns transfer.
- Spacelift: [Terraform with GitHub Actions](https://spacelift.io/blog/github-actions-terraform).
- AWS docs: [Configure OIDC for GitHub Actions to assume an IAM role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html) — **always use OIDC, never long-lived `AWS_ACCESS_KEY_ID` secrets in CI.**
- Read the [`hashicorp/setup-terraform`](https://github.com/hashicorp/setup-terraform) action README and either [`dflook/terraform-plan`](https://github.com/marketplace/actions/terraform-plan) or hand-rolled steps for PR-comment plans.
- Optionally skim Atlantis ([runatlantis.io](https://runatlantis.io/)) and Spacelift to know what they replace.

**Project 6 — Real CI/CD pipeline:**
- Three GitHub Actions workflows:
  1. `pr-validate.yml` — on PR: `fmt -check`, `validate`, `tflint`, `checkov`, `tfsec`/Trivy IaC scan, then `plan` per environment with **OIDC-assumed IAM role**, post the plan as a sticky PR comment.
  2. `apply-dev.yml` — on push to `main`: auto-apply dev.
  3. `apply-prod.yml` — manual `workflow_dispatch` with **GitHub Environment** protection (required reviewers, ≥5-min wait timer) targeting prod.
- Cost preview: integrate Infracost on PRs (`infracost/actions`).
- Build a `terraform-cost-budget` policy file that fails the PR if monthly cost increases >$50. Use Open Policy Agent (OPA) via [`open-policy-agent/conftest`](https://www.conftest.dev/) on the plan JSON.
- **Document trade-offs in `docs/cicd.md`:** GitHub Actions vs. Atlantis vs. Spacelift/env0/Scalr — when each makes sense.

---

### Phase 7 — Testing: Native, Terratest, Static, Policy (Week 14, ~1 week)

**Theory:**
- Brikman **Chapter 9** ("How to Test Terraform Code") — manual tests, unit tests, integration tests, end-to-end tests, plus the new (3rd ed.) section on static analysis.
- Winkler **Chapter 10** ("Testing and Refactoring") — Terratest in depth, including helpers like `terraform.InitAndApply` and `aws.GetPrivateIpsOfEc2Instances`.
- HashiCorp docs: [Terraform tests](https://developer.hashicorp.com/terraform/language/tests) — the **native `.tftest.hcl` framework** GA in 1.6+. Read every example. Pair with [env0's Terratest vs Terraform Test comparison](https://www.env0.com/blog/terratest-vs-terraform-opentofu-test-in-depth-comparison) for trade-offs (native = HCL, no Go; Terratest = real-world API verification).
- Static analysis: read [tflint](https://github.com/terraform-linters/tflint), [Checkov](https://www.checkov.io/), and Trivy IaC (which has absorbed `tfsec`). The Spacelift [security tools comparison](https://spacelift.io/blog/terraform-scanning-tools) is a clean overview.
- Policy as code: HashiCorp's Sentinel (paid) vs. **OPA/Rego** (free; what most teams use). Read Styra's intro to Rego + a Conftest Terraform example.

**Project 7 — Layered test pyramid for one of your modules:**
- Pick `modules/aurora-mysql/`. Add:
  - **Static layer:** `.tflint.hcl` with the AWS plugin enabled, `.checkov.yaml` excluding only the rules you can justify (with comments).
  - **Native unit tests:** `tests/unit.tftest.hcl` using `command = plan` to assert that, e.g., when `engine = "aurora-mysql"`, `engine_version` defaults correctly, and that `var.deletion_protection = true` produces a plan that sets `deletion_protection = true`.
  - **Native integration tests:** `tests/integration.tftest.hcl` using `command = apply` to spin up a tiny Aurora cluster, assert with `assert {}` against attributes, then auto-destroy.
  - **Terratest:** `test/aurora_test.go` that does the same thing but in Go and *also* makes a real connection to the writer endpoint with the `database/sql` driver to prove the cluster is actually serving SQL — the gap that native tests can't close (since they only see what the provider reports).
  - **Policy test:** an OPA Rego policy enforcing `deletion_protection`, `storage_encrypted`, `backup_retention_period >= 7`, all `tags.Environment` set. Conftest run in CI on `terraform show -json plan.tfplan`.
- Wire all four layers into the Phase 6 GitHub Actions PR workflow.

---

### Phase 8 — Secrets Management (Week 15, ~1 week)

**Theory:**
- Brikman **Chapter 6** ("Managing Secrets with Terraform") — secret types (human-to-machine, machine-to-machine, infra), the four storage models (env vars, encrypted files, secret stores, dedicated tools), how secrets leak into state and plan files.
- Winkler **Chapter 13** ("Security and Secrets Management").
- HashiCorp Learn: [Inject secrets into Terraform using the Vault provider](https://developer.hashicorp.com/terraform/tutorials/secrets/secrets-vault) — Vault AWS Secrets Engine for *dynamic short-lived AWS credentials*, then the AWS provider consumes them.
- AWS-side: [`data "aws_secretsmanager_secret_version"`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret_version), [SSM Parameter Store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_parameter), and the new **ephemeral resources / write-only attributes** (Terraform 1.10+ / OpenTofu) which keep values out of state.
- GitGuardian: [Terraform Secrets Management Best Practices](https://blog.gitguardian.com/how-to-handle-secrets-in-terraform/) — pragmatic checklist.

**Project 8 — Bolt secrets onto the multi-tier app:**
- Run a local dev Vault (Docker), enable AWS Secrets Engine, configure a role that can mint short-lived AWS credentials, and use the **Vault Terraform provider** to obtain them at plan/apply time — proving end-to-end the "no long-lived AWS keys on developer laptops" pattern.
- Move the app's DB password from Aurora's managed master password into AWS Secrets Manager, with rotation Lambda (use the [`terraform-aws-modules/lambda`](https://registry.terraform.io/modules/terraform-aws-modules/lambda/aws/latest) module).
- Use a `write-only` ephemeral attribute (Terraform 1.10+) for at least one secret to prove you understand state-leak avoidance.

---

### Phase 9 — EKS, Helm, Kubernetes Provider (Weeks 16–18, ~3 weeks)

**Theory:**
- Brikman **Chapter 7** ("Working with Multiple Providers") — second half is a Docker/Kubernetes/EKS crash course with full Terraform code: deploying containerized apps with the `kubernetes` and `helm` Terraform providers.
- Winkler **Chapter 8** ("A Multi-Cloud MMORPG") — provisions Kubernetes on multiple clouds with Terraform; great for thinking patterns.
- Tinderholt **Chapter 8** ("Containerize with AWS – Building Solutions with AWS EKS") — alternative voice, with parallel chapters for AKS (Ch. 11) and GKE (Ch. 14) you'll use later.
- Read the source of `terraform-aws-modules/eks` (latest v21+ supports EKS Auto Mode) and `aws-ia/terraform-aws-eks-blueprints`. Note the warning that AWS does **not** recommend mixing cluster creation and addon-via-Helm in one workspace — split them.
- AWS blog: search for HashiCorp's *Terraform on AWS* posts for EKS Auto Mode patterns and Karpenter setup.

**Project 9 — Production-pattern EKS:**
- Workspace 1: cluster (VPC reused from Phase 5, `terraform-aws-modules/eks`, EKS Auto Mode or managed node groups, IAM roles for service accounts via OIDC, EBS CSI driver addon).
- Workspace 2: cluster addons (ArgoCD or Flux via `helm_release`, AWS Load Balancer Controller, External DNS, Karpenter, cluster autoscaler, metrics-server, Prometheus + Grafana via kube-prometheus-stack).
- Deploy your Spring Boot Kotlin service to the cluster as a Helm chart, exposed via an ALB via the AWS Load Balancer Controller (`Ingress` resource).
- Wire **Pod Identity** (newer than IRSA) using `terraform-aws-modules/eks-pod-identity` so the app can read from S3 / Secrets Manager without static creds.
- For your Kafka background: also provision an **MSK Kafka cluster** with `terraform-aws-modules/msk-kafka-cluster`, IAM-auth, and have the EKS app produce/consume from it. This will pleasantly surprise interviewers.

**Time:** ~15 hrs theory + ~30 hrs project.

---

### Phase 10 — Multi-Cloud Refactor: Provider Abstraction (Weeks 19–22, ~4 weeks)

**Theory:**
- Brikman **Chapter 7** first half ("Working with Multiple Providers") — provider aliases, multiple regions, multiple AWS accounts, then *Working with Multiple Different Providers*. Crucial chapter; read twice.
- Tinderholt **Chapters 7–15** — the AWS/Azure/GCP × VM/Container/Serverless matrix. Skim AWS chapters (you've covered), read **Azure Chapters 10–12** (Ch. 10 VMs, Ch. 11 AKS, Ch. 12 Functions) **OR** **GCP Chapters 13–15** (your choice; pick whichever you'd realistically meet at a Korean enterprise — Azure is more common in chaebol environments, GCP in startups).
- Practitioner blogs: OneUptime's [How to Use Terraform with Multiple Cloud Providers](https://oneuptime.com/blog/post/2026-01-27-terraform-multi-cloud/view) and [How to Create Terraform Modules for Multi-Cloud](https://oneuptime.com/blog/post/2026-02-23-how-to-create-terraform-modules-for-multi-cloud/view) — both stress *don't over-abstract; use a wrapper module that picks the cloud-specific implementation*.
- Read source: [`terraform-google-modules/network`](https://github.com/terraform-google-modules/terraform-google-network) or `Azure/terraform-azurerm-vnet` to map AWS VPC concepts.
- Decision principle (from these readings): **abstract only the primitives that genuinely benefit from portability** (compute, network baseline, blob storage, basic load balancing). Use cloud-native services (Aurora vs. Cloud SQL vs. Azure Database for MySQL) directly when they materially improve the workload — wrap them only behind a workload-level interface.

**Project 10 — Refactor the multi-tier app:**
- Restructure modules into:
  ```
  modules/
    interfaces/    # variable + output contracts only (no resources)
      compute-cluster/
      vpc-network/
      managed-mysql/
      object-storage/
    aws/           # AWS implementations matching the interface
    gcp/  (or azure/)  # second cloud implementations
  ```
- A `live/{cloud}/{env}/` Terragrunt layout selects the implementation.
- Implement at minimum: `vpc-network` (AWS VPC vs. GCP VPC + subnets), `compute-cluster` (ASG+ALB vs. MIG+GLB), `object-storage` (S3 vs. GCS).
- Keep `managed-mysql` cloud-specific (Aurora vs. Cloud SQL) but expose a uniform output: `connection_string`, `secret_arn_or_path`. This is the *honest* multi-cloud pattern: not "rewrite once for every cloud" but "the workload contract is uniform, the implementation is best-of-breed per cloud".
- Run the SAME application Helm chart against EKS and against GKE (or AKS); demonstrate that switching clouds is one Terragrunt path change.
- **Run the full test suite (Terratest) against both clouds** — this is how you'll discover hidden coupling.

---

### Phase 11 — Production-Grade Concerns & Capstone (Weeks 23–28, ~6 weeks)

**Theory:**
- Brikman **Chapter 5** second half — `create_before_destroy`, zero-downtime ASG deployments, `prevent_destroy`, lifecycle gotchas.
- Winkler **Chapter 9** ("Zero-Downtime Deployments") — blue/green ASG patterns, the `null_resource` + `triggers` trick.
- Tinderholt **Chapter 17** ("Importing Existing Environments") and **Chapter 18** ("Operating Models") — operating models for standalone apps vs. shared infra vs. shared services; failure modes; refactoring strategies.
- Drift detection: HCP Terraform's health assessments; for OSS, [`driftctl`](https://github.com/snyk/driftctl) or a scheduled GitHub Action that runs `plan` and alerts on non-zero changes.
- Cost: Infracost, AWS Cost Anomaly Detection, FinOps tagging strategy. Babenko's `weekly.tf` archive has multiple posts on tagging at scale.
- Disaster recovery: AWS Backup as Terraform resources; cross-region replication for state bucket; documented "what to do if the state file is lost" runbook (`terraform import` mass workflow).
- Read at least one of: AWS' *Well-Architected for Reliability* whitepaper, Google's SRE Book chapter on capacity planning. Reframes Terraform decisions around explicit reliability targets.

**Project 11 — Capstone reference architecture:**
A production-grade reference architecture that you'd be proud to point an interviewer at. Suggested: a Kotlin/Spring Boot order-processing service with Kafka event sourcing, Aurora MySQL persistence, deployed multi-region active/passive, observability stack, full IaC.

Required components, each in versioned modules:
- **Networking**: 2-region VPC pair with private inter-region peering or Transit Gateway, multi-AZ.
- **Data plane**: Aurora MySQL Global Database (writer in `ap-northeast-2` Seoul, reader in `ap-northeast-1` Tokyo for DR — see AWS Aurora Global Database Terraform blog), MSK Kafka cluster with MSK Connect, S3 with cross-region replication.
- **Compute**: EKS Auto Mode in primary region + standby cluster in DR region with Karpenter, Argo CD GitOps from a separate repo for app deployments.
- **Observability**: AWS Managed Prometheus + Managed Grafana, OpenTelemetry collector as DaemonSet, CloudWatch alarms with EventBridge → SNS, one synthetic canary.
- **Cost & governance**: AWS Budgets per env via Terraform, Cost Anomaly Detection, mandatory-tag SCP, OPA policies in CI blocking missing tags or untagged resources, monthly cost report by tag posted to Slack.
- **DR**: Aurora cross-region failover script (Lambda + Step Functions in TF), documented RTO/RPO, a tested-and-recorded failover drill.
- **Multi-cloud option**: the static frontend and one stateless service deployable to GCP Cloud Run via the multi-cloud module pattern from Phase 10.
- **Pipeline**: full GitHub Actions OIDC, plan-on-PR, sticky comments with Infracost diff, OPA gate, native + Terratest test suites, manual approval to prod, automated drift detection job nightly.

**Documentation deliverable:** an `architecture.md` with Mermaid diagrams, a `runbook.md`, an `adr/` directory with at least 5 Architecture Decision Records (e.g., "Why Aurora over Cloud SQL", "Why folder-per-env over workspaces", "Why OPA over Sentinel", "Why `terraform-aws-modules/vpc` over hand-rolled", "When to abstract for multi-cloud").

---

### Phase 12 — Certification & Polish (Weeks 29–32, ~4 weeks)

**Theory:**
- HashiCorp's official [Associate 004 Learning Path](https://developer.hashicorp.com/terraform/tutorials/certification-004) — work through every linked tutorial.
- *HashiCorp Terraform Associate (003) Exam Guide* by Bhupinder Sindhwani (Packt, 2024) — still highly relevant for 004 since the topical scope only shifted slightly. Includes mock exams and flashcards.
- Zeal Vora's Udemy course *HashiCorp Certified: Terraform Associate 2026* — ~85k+ students, 4.7 rating; concise and exam-aligned. The Practice Exam companion course is the best mock-exam resource.
- Bryan Krausen's *HashiCorp Certified: Terraform Associate — Hands-On Labs* — practical, lab-driven; good complement.
- Sample questions: HashiCorp's [official sample question page](https://developer.hashicorp.com/terraform/tutorials/certification-004/associate-questions-004) and ExamTopics community discussions.

**For the Professional exam (optional but high-leverage given your seniority):**
- Zeal Vora's *Terraform Authoring and Operations Professional 2026* (Udemy). Lab-based exam, so practical drilling matters more than reading.

**Project 12 — Polish & ship the portfolio:**
- Fork everything into a clean public GitHub org. Each module repo gets: README with usage block, `examples/`, `tests/`, GitHub Actions, semver tags, CHANGELOG.
- Publish 2–3 modules to the public Terraform Registry (private for company, public for portfolio).
- Write 3 blog posts on your own site (or dev.to) — drafted while you're learning, not after: "Migrating an Aurora MySQL cluster to Terraform without downtime", "Native `terraform test` vs Terratest in 2026", "Multi-cloud the honest way: when not to abstract".
- Schedule and pass **Associate 004**. Then schedule Professional 2–3 months later if you want it.

**Total mastery time:** ~32 weeks at ~10 hrs/week ≈ **320 hours**, comfortably 7–8 calendar months with vacation slack.

---

# Part 2 — Distilled 10-Week Intensive (the 80/20)

For ~10 hrs/week. Cuts custom providers, multi-cloud, EKS depth, and the Professional exam. Goal: **competent shipping Terraform engineer + Associate 004 certified**.

| Week | Theme | Theory (read these chapters/modules only) | Project deliverable |
|---|---|---|---|
| 1 | Setup + HCL | Brikman Ch. 1 + 2; HashiCorp [AWS Get Started](https://developer.hashicorp.com/terraform/tutorials/aws-get-started) (all 8 tutorials); OpenTofu install | S3 + EC2 with vars/outputs/validations; OpenTofu parity check |
| 2 | State + import | Brikman Ch. 3; Spacelift [import guide](https://spacelift.io/blog/importing-exisiting-infrastructure-into-terraform) | Bootstrap S3+DynamoDB backend; migrate Wk1 state; import an existing console-created resource via 1.5 `import` block |
| 3–4 | Multi-tier on AWS | Brikman Ch. 5 (loops/conditionals); `terraform-aws-modules/vpc` and `terraform-aws-modules/rds-aurora` READMEs | VPC + ALB + ASG + Aurora MySQL with managed master password and Secrets Manager integration |
| 5 | Modules | Brikman Ch. 4 + Ch. 8 (production checklist) | Refactor Wk3–4 into 4 versioned modules with `examples/`, READMEs (terraform-docs), semver tags |
| 6 | Multi-env | Brikman Ch. 3 (file layout); Spacelift [Terragrunt vs Terraform](https://spacelift.io/blog/terragrunt-vs-terraform) | dev/stage/prod with Terragrunt; promote a module version dev→stage→prod |
| 7 | CI/CD | Brikman Ch. 10; Spacelift [GitHub Actions Terraform](https://spacelift.io/blog/github-actions-terraform); AWS OIDC docs | GitHub Actions PR-plan + apply-on-merge with OIDC, sticky PR comments, Infracost |
| 8 | Testing + scanning | Brikman Ch. 9; HashiCorp [`terraform test` docs](https://developer.hashicorp.com/terraform/language/tests) | tflint + Checkov + native `.tftest.hcl` unit + integration tests in CI for one module |
| 9 | Secrets + EKS taste | Brikman Ch. 6 + first half of Ch. 7; HashiCorp [AWS Secrets Engine tutorial](https://developer.hashicorp.com/terraform/tutorials/secrets/secrets-vault) | Replace static DB password with Secrets Manager + ephemeral attribute; deploy a tiny EKS cluster via `terraform-aws-modules/eks` and one Helm chart |
| 10 | Cert + portfolio | Zeal Vora *Associate 2026* (skim, not full); Bryan Krausen labs; HashiCorp's [sample questions](https://developer.hashicorp.com/terraform/tutorials/certification-004/associate-questions-004); 2 mock exams | **Pass Associate 004**; 1 polished GitHub repo with README, ADR, architecture diagram |

**Totals:** ~100 hours, 1 certification, 3 stacked projects (single resource → modular multi-tier → CI/CD-tested), an interview-grade portfolio repo.

---

# Part 3 — Curated Resource Index

### Books (priority order for mastery track)

| Priority | Book | Edition / Year | Chapters to read first | Skip / skim |
|---|---|---|---|---|
| **#1 spine** | *Terraform: Up & Running* — Yevgeniy Brikman | 3rd ed., O'Reilly 2022 | All 10 chapters in order. Highest signal: Ch. 2, 3, 4, 8, 9 | None — read every chapter |
| **#2 advanced** | *Terraform in Action* — Scott Winkler | Manning 2021 (still relevant) | Part 3 (Ch. 9 zero-downtime, Ch. 10 testing/refactoring, Ch. 13 secrets) | Ch. 11 (writing custom providers) unless you need it |
| **#3 multi-cloud** | *Mastering Terraform* — Mark Tinderholt | Packt 2024 | Ch. 1–3 (architecture, HCL, utility providers), Ch. 7–9 (AWS), and **whichever pair of Azure (10–12) or GCP (13–15) you target** | The other cloud's chapters |
| **#4 cert prep** | *HashiCorp Terraform Associate (003) Exam Guide* — Bhupinder Sindhwani | Packt 2024 | All — it's exam-shaped. Use the included mock exams as practice | Read selectively for objectives you find weak |

### Free / official online

- **HashiCorp Developer**: `developer.hashicorp.com/terraform/tutorials` — all "Get Started", "Modules", "State", "Test", and the Associate 004 learning path. The single most authoritative free resource.
- **HashiCorp blog**: filter for Terraform; especially posts on `import` block, `moved` blocks, ephemeral resources, write-only attributes, native `terraform test`.
- **AWS blog**: `aws.amazon.com/blogs/infrastructure-and-automation/` — search Terraform; the Aurora Global Database with Terraform two-part series is excellent.

### Blogs (subscribe / follow)

| Source | Why follow | Highest-signal pieces |
|---|---|---|
| **Gruntwork blog** (`blog.gruntwork.io`) | Origin of *Terraform: Up & Running*; production-grade voice | *A Comprehensive Guide to Terraform* (6-part series); *A crash course on Terraform*; *How to use Terraform as a team* |
| **Anton Babenko** — `weekly.tf` newsletter + `antonbabenko.com` | Best curated weekly digest of the entire ecosystem; maintainer of `terraform-aws-modules` | Subscribe to weekly.tf; read [terraform-best-practices.com](https://www.terraform-best-practices.com/) (free ebook, **also in Korean** 🇰🇷) |
| **Spacelift blog** (`spacelift.io/blog`) | Highest-volume English Terraform blog; broad and current | Compare-and-contrast posts: workspaces vs Terragrunt, Atlantis alternatives, scanning tools, OpenTofu vs Terraform |
| **env0 blog** | Deep technical posts on testing, drift, Vault | Terratest vs Terraform Test; Checkov vs tfsec vs Terrascan |
| **Cloud Posse / SweetOps** (`docs.cloudposse.com`) | Reference architecture at scale; the `null-label` `context.tf` pattern | The "Conventions" page; the `terraform-aws-components` repo |
| **HashiCorp Discuss** (`discuss.hashicorp.com`) | Official forum; search before you post | Useful for tracking the Terraform ↔ OpenTofu divergence in real time |

### Courses (if you prefer video)

| Course | Where | Use case |
|---|---|---|
| **Zeal Vora — *HashiCorp Certified: Terraform Associate 2026*** | Udemy | Best paid Associate-prep course; tightly mapped to objectives. ~85k students, 4.7★ |
| **Zeal Vora — *Terraform Authoring and Operations Professional 2026*** | Udemy | Only well-known prep course for the new Professional exam |
| **Bryan Krausen — *HashiCorp Certified: Terraform Associate — Hands-On Labs*** | Udemy | Lab-only; complement to Zeal Vora |
| **KodeKloud — *Terraform for Beginners*, *Terraform Challenges*, *HashiCorp Certified Terraform Associate*** | KodeKloud / LinkedIn Learning | Best browser-lab-based learning if you don't want to spin up your own AWS account |
| **HashiCorp Learn (free)** | developer.hashicorp.com | The official path — skip a paid course if you have discipline |
| **freeCodeCamp — *HashiCorp Terraform Associate Certification Course*** | YouTube (free) | Solid free survey if you want a single video |
| **A Cloud Guru / Pluralsight** | Subscription | Older content; only worth it if you have an existing subscription |

### Korean-language resources

| Resource | Link | Notes |
|---|---|---|
| **Terraform Associate 시험으로 배우는 Terraform 기초 강의** | Inflearn | Korean walkthrough of Associate 003/004 objectives with AWS Free Tier labs; theory + sample code + section quizzes. The most polished Korean Terraform course. |
| **DevOps : Infrastructure as Code with Terraform and AWS — 기본편** | Inflearn (`terraform101.inflearn.devopsart.dev`) | DevOpsArt's IaC + AWS introduction in Korean; AWS-Free-Tier-only |
| **DevOps : Infrastructure as Code with Terraform and AWS — 중급/활용편** | Inflearn (`intermediate.inflearn.devopsart.dev`) | Continuation focusing on real ops patterns |
| **Anton Babenko's *Terraform Best Practices* — Korean translation** | github.com/antonbabenko/terraform-best-practices | The 🇰🇷 flag is in the official translation list |

English remains where the bleeding-edge content lives (especially around 1.5+ `import` blocks, native `tftest`, ephemeral resources, Terragrunt Stacks, and OpenTofu) — use Korean resources to lock in fundamentals quickly, then switch to English by Phase 5.

### Open-source repos to read like a textbook (in this order)

1. **`brikis98/terraform-up-and-running-code`** — code from Brikman's book, organized by chapter. Read alongside the book.
2. **`gruntwork-io/intro-to-terraform`** — the simpler, blog-series version of #1.
3. **`terraform-aws-modules/terraform-aws-vpc`** — read every file. The reference VPC module.
4. **`terraform-aws-modules/terraform-aws-rds-aurora`** — directly applicable to your Aurora MySQL day job.
5. **`terraform-aws-modules/terraform-aws-eks`** — modern EKS Auto Mode patterns.
6. **`aws-ia/terraform-aws-eks-blueprints`** — AWS' own opinionated patterns (note: not a consumable module, a pattern catalog).
7. **`cloudposse/terraform-null-label`** + **`cloudposse/terraform-aws-components`** — naming/tagging at scale and the `context.tf` pattern.
8. **`terraform-aws-modules/terraform-aws-msk-kafka-cluster`** + **`terraform-aws-modules/terraform-aws-lambda`** — Anton Babenko's other reference modules; Kafka is interesting given your background.
9. **`hashicorp/terraform`** itself — when you have time, read the Go code for `terraform plan` to internalize the dependency graph and refresh phases. This is Senior+ territory.

### Tools to install and learn (in priority order)

1. `terraform` and `tofu` (via `tfenv` and `tofuenv` for version management)
2. `terraform-docs` (auto-generate module READMEs)
3. `tflint` with the AWS plugin
4. `pre-commit` + `antonbabenko/pre-commit-terraform`
5. `checkov` (and Trivy for IaC scanning since `tfsec` is now part of Trivy)
6. `infracost` (cost diff in PRs)
7. `terragrunt` (when you reach Phase 5)
8. `terratest` (Go module, when you reach Phase 7)
9. `conftest` + OPA / Rego (Phase 7)
10. `driftctl` (Phase 11) — if you don't use HCP Terraform health assessments

---

# Part 4 — Strategic Notes for May 2026

- **HCP Terraform free tier ended March 31, 2026.** Don't plan around it. Use S3+DynamoDB backend for state, GitHub Actions or Atlantis for runs. If you eventually want a managed runner UI, the live alternatives are **Spacelift** (best-in-class, supports Terraform/OpenTofu/Terragrunt/CloudFormation/Pulumi/Kubernetes), **env0** (broad IaC support, FinOps focus, unlimited concurrency on paid plans), **Scalr** (closest drop-in for Terraform Cloud with OpenTofu support), and **Atlantis** (free, self-hosted).
- **Terraform vs OpenTofu in 2026.** They have begun diverging (write-only attributes shipped in Terraform Feb 2025, OpenTofu July 2025; OpenTofu has client-side state encryption, Terraform does not). Treat OpenTofu as a hedge against future BSL changes and as a way to use state encryption today; treat Terraform as the canonical syntax to learn and what enterprise job listings ask for. Lock-test on both via CI matrices once your modules stabilize.
- **CDKTF is gone.** AWS CDK for Terraform was sunset by HashiCorp on December 10, 2025 (repo archived). If you considered TypeScript or Python over HCL, drop the idea — invest fully in HCL.
- **Kafka relevance.** Your Apache Kafka background means **`terraform-aws-modules/terraform-aws-msk-kafka-cluster`** and Confluent Cloud's official Terraform provider are unusually relevant assets. Drop both into your capstone in Phase 11; this is differentiation that very few generalist Terraform candidates have.
- **Spring Boot / Kotlin angle.** Your Phase 3, 9, and 11 services should be Spring Boot Kotlin apps, packaged as containers. This lets your portfolio repos demonstrate the full loop — Kotlin source → Gradle → Docker → ECR → Terraform → EKS → ALB → Aurora → Kafka — which most pure-DevOps engineers can't. Lean into the overlap.
- **Pacing for South Korea schedule.** Korean engineering culture often means evening/weekend study. The Distilled track (10 hrs/week) is realistic; the Mastery track at 8 hrs/week (closer to 9 months) is more sustainable than 12 hrs/week (6 months) without burnout — pick your pace honestly upfront.

---

# Caveats

- **Course versioning is a moving target.** Udemy course version numbers (e.g., "*Terraform Associate 2026*") update yearly; always pick the most recently updated version with high recent-review density. The Zeal Vora and Bryan Krausen names persist across years.
- **Associate 004 vs 003.** Exam 003 retired January 8, 2026. The current exam is 004; I recommended studying with both the 003 Packt book and HashiCorp's 004 learning path because the topical scope shifted only marginally and 004-specific books are still emerging in 2026. Verify the latest objectives at HashiCorp's certification page before scheduling your exam.
- **Multi-cloud is genuinely hard.** The plan for Phase 10 follows the *honest* multi-cloud pattern (interface-and-implementation modules, cloud-native data services per cloud) — not the marketing-driven "deploy once, run anywhere" promise. Production multi-cloud is mostly used for DR, regulatory data residency, or vendor leverage, *not* for daily developer convenience. Set expectations accordingly.
- **EKS chapter dates.** `terraform-aws-modules/eks` v21+ supports EKS Auto Mode (relatively recent). If you're learning from older blog posts that pre-date Auto Mode, the patterns (`aws-auth` ConfigMap, IRSA-only auth) still work but are no longer the default; prefer Pod Identity and Auto Mode for new builds.
- **Some 2026 Spacelift, env0, and Scalr posts are commercial.** They're high-quality but each vendor naturally favors itself — read 2–3 in parallel for any architectural decision (e.g., Atlantis vs Spacelift vs Terraform Cloud).
- **"Gruntwork blog" content frequently overlaps with the *Terraform: Up & Running* book** (the book is the expanded blog series). If the book is in your queue, you can skip Gruntwork blog re-reads except for *post-book* updates.
- **Korean-language Terraform content lags English by 6–18 months** for cutting-edge topics (OpenTofu, native `terraform test`, ephemeral resources). Do fundamentals in Korean if it helps speed; do advanced topics in English.
- **The capstone project (Phase 11) is intentionally over-scoped.** Plan to ship 70% of it; the other 30% becomes "future work" in your README. Resist the perfectionism trap — recruiters care more about a clean, documented 70% repo than a never-finished 100% one.