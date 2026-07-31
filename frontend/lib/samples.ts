/** Sample pair so a visitor can see a real report without uploading anything. */

export const SAMPLE_RESUME = `RIYA CHOWDHURY
riya.chowdhury@example.com | +880 1712 345678 | github.com/riyacd | linkedin.com/in/riyacd

SUMMARY
Machine learning engineer with 5 years building and operating LLM-backed services in production.
Owns systems end to end: retrieval pipelines, model serving, deployment and monitoring.

EXPERIENCE
Senior ML Engineer, Bracket AI - 03/2023 - Present
- Built a retrieval-augmented answering service over 4.2M internal documents using pgvector and a
  cross-encoder reranker, lifting answer relevance from 61% to 84% on a 500-question eval set.
- Cut p95 response latency from 3.4s to 900ms by adding embedding caching and batching in FastAPI.
- Deployed inference workloads on Kubernetes with autoscaling from 2 to 18 pods under load tests.
- Instrumented token and cost accounting in Prometheus and Grafana, reducing monthly spend 38%.

ML Engineer, Shomoy Analytics - 07/2021 - 02/2023
- Shipped a churn model in PyTorch serving 120k daily predictions at p99 under 60ms.
- Built Airflow ETL pipelines over Postgres feeding a 90-feature training set.
- Automated retraining with GitHub Actions and MLflow, cutting release time from 5 days to 4 hours.

PROJECTS
- Open-source RAG evaluation toolkit comparing 6 chunking strategies; 340 GitHub stars.

SKILLS
Python, PyTorch, FastAPI, pgvector, Qdrant, Docker, Kubernetes, Terraform, GitHub Actions,
Prometheus, Grafana, MLflow, Postgres, Redis, AWS, SQL, Git

EDUCATION
B.Sc. in Computer Science, BUET - 2015 - 2019`;

export const SAMPLE_JD = `Job Title: LLM Platform Engineer
Company: Northwind Intelligence
Location: Remote (Asia timezones)

About the role
You will own the retrieval and serving layer behind our customer-facing AI assistant, from
ingestion pipelines through to production monitoring.

Requirements
- 4+ years of professional software engineering experience, at least 2 with machine learning in production.
- Strong Python, including async services with FastAPI or a comparable framework.
- Hands-on experience building retrieval-augmented generation systems: chunking, embeddings,
  vector search and reranking.
- Experience with a vector store such as pgvector, Qdrant or Pinecone.
- Production experience with Docker and Kubernetes.
- Demonstrated ability to evaluate model quality with an offline evaluation harness.
- Solid SQL and Postgres.

Nice to have
- Experience fine-tuning open-weight models with LoRA or QLoRA.
- Familiarity with Prometheus and Grafana for latency and cost dashboards.
- Contributions to open-source ML tooling.

Responsibilities
- Design and ship the document ingestion and embedding pipeline.
- Reduce p95 answer latency while holding answer quality steady.
- Build cost and token accounting into the serving path.
- Mentor two junior engineers and review their pull requests.`;

export const SAMPLE_ROLE = "LLM Platform Engineer";
export const SAMPLE_COMPANY = "Northwind Intelligence";
