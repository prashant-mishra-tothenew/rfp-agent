#!/usr/bin/env python3
"""Generate training PPTX proposals from proposal-template.pptx.

Usage:
    python ingestion/scripts/generate_training_pptx.py
    python ingestion/scripts/generate_training_pptx.py --output-dir ingestion/historical-rfps
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ai-service"))

from app.proposal.pptx_template import render_pptx_from_template

TRAINING_PROPOSALS: list[dict] = [
    {
        "rfp_id": "TRAIN-RFP-001",
        "filename": "TRAIN_TTN_Proposal_RetailMax_Ecommerce_Platform.pptx",
        "customer": "RetailMax Group",
        "executiveSummary": (
            "Following our discussions with RetailMax Group, we are pleased to submit this proposal "
            "for the design and development of a unified B2C and B2B commerce platform. TTN will "
            "deliver a Drupal Commerce solution with PIM integration, multi-store management, and "
            "faceted search supporting 100,000+ SKUs across Australia and New Zealand."
        ),
        "understandingOfRequirements": (
            "Enable multi-store catalogue management with regional pricing and tax rules.\n"
            "Support faceted search, product recommendations, and inventory sync with ERP.\n"
            "Provide B2B account hierarchies, quote-to-order workflows, and approval chains.\n"
            "Integrate Stripe, PayPal, and Afterpay for multi-currency checkout.\n"
            "Deliver WCAG 2.1 AA accessible storefronts with CDN-backed performance."
        ),
        "proposedSolution": (
            "Drupal 10 with Commerce 2.x as the core commerce engine.\n"
            "Akeneo PIM connector for product enrichment and attribute management.\n"
            "Search API with Solr for faceted navigation and autocomplete.\n"
            "Headless Next.js storefront with SSR for SEO and Core Web Vitals.\n"
            "Middleware layer for ERP (SAP) inventory and order synchronisation."
        ),
        "technicalApproach": (
            "Modular microservices architecture deployed on AWS EKS.\n"
            "API-first design with GraphQL gateway for storefront and mobile apps.\n"
            "Redis caching layer for session, cart, and catalogue hot paths.\n"
            "Event-driven order pipeline using Amazon SQS and Lambda.\n"
            "Blue-green deployments with automated rollback on health check failure."
        ),
        "securityCompliance": (
            "PCI-DSS aligned payment flows with tokenised card data via Stripe.\n"
            "OWASP Top 10 mitigations including WAF, CSP, and rate limiting.\n"
            "Data residency in ap-southeast-2 with encrypted RDS and S3 buckets.\n"
            "SOC 2 Type II controls for access management and audit logging.\n"
            "Penetration testing before go-live and quarterly vulnerability scans."
        ),
        "assumptions": (
            "RetailMax will provide API access to SAP ERP within 2 weeks of kick-off.\n"
            "Product data migration scope limited to 80,000 active SKUs.\n"
            "UAT environment and test accounts provided by RetailMax.\n"
            "Third-party PIM licence costs are borne by RetailMax.\n"
            "Hypercare support of 2 weeks included post go-live."
        ),
        "implementationMethodology": (
            "Phase 1 — Discovery & Architecture (4 weeks): workshops, backlog, solution design.\n"
            "Phase 2 — Core Platform (10 weeks): catalogue, cart, checkout, admin.\n"
            "Phase 3 — Integrations (6 weeks): ERP, PIM, payments, search tuning.\n"
            "Phase 4 — UAT & Go-Live (4 weeks): regression, performance, cutover.\n"
            "Agile sprints with fortnightly demos and steering committee reviews."
        ),
        "supportAndSla": (
            "L1/L2 support via dedicated ServiceNow queue, 8x5 AEST coverage.\n"
            "P1 incidents: 1-hour response, 4-hour resolution target.\n"
            "Monthly platform health reports and quarterly optimisation reviews.\n"
            "Dedicated Customer Success Manager for first 6 months post go-live."
        ),
    },
    {
        "rfp_id": "TRAIN-RFP-002",
        "filename": "TRAIN_TTN_Proposal_MediCare_Patient_Portal.pptx",
        "customer": "MediCare Health Network",
        "executiveSummary": (
            "TTN proposes a secure, patient-centric digital health portal for MediCare Health Network. "
            "The solution enables appointment booking, telehealth, medical records access, and "
            "prescription management while meeting Australian healthcare privacy and My Health Record "
            "integration requirements."
        ),
        "understandingOfRequirements": (
            "Patient registration with identity verification and MFA login.\n"
            "Online appointment scheduling across 45 clinic locations.\n"
            "Secure messaging between patients and care teams.\n"
            "View lab results, discharge summaries, and immunisation history.\n"
            "Telehealth video consultations with calendar integration.\n"
            "My Health Record (MHR) consent-based document upload and retrieval."
        ),
        "proposedSolution": (
            "React Native mobile app and responsive web portal on Azure.\n"
            "FHIR R4 APIs for clinical data exchange with existing EMR (Cerner).\n"
            "Azure AD B2C for patient identity with passwordless OTP option.\n"
            "Twilio Video for HIPAA-compliant telehealth sessions.\n"
            "Notification service for SMS/email reminders via MessageMedia."
        ),
        "technicalApproach": (
            "Zero-trust network architecture with private endpoints for all PaaS services.\n"
            "FHIR server (HAPI) as integration hub between portal and Cerner EMR.\n"
            "Immutable audit logs stored in Azure Log Analytics for 7 years.\n"
            "Automated CI/CD with SAST/DAST gates in Azure DevOps pipelines.\n"
            "Disaster recovery with geo-redundant storage and 4-hour RTO target."
        ),
        "securityCompliance": (
            "Compliance with Australian Privacy Principles (APPs) and ISM Essential Eight.\n"
            "All PHI encrypted at rest (AES-256) and in transit (TLS 1.3).\n"
            "Role-based access control with break-glass procedures for emergencies.\n"
            "Annual IRAP assessment pathway aligned with MediCare security policy.\n"
            "Patient consent management for data sharing and MHR integration."
        ),
        "assumptions": (
            "Cerner FHIR API sandbox available within 3 weeks of project start.\n"
            "MediCare provides clinical workflow SMEs for fortnightly workshops.\n"
            "MHR integration subject to ADHA conformance testing timelines.\n"
            "Content localisation limited to English for initial release.\n"
            "Training for 200 clinic staff included in scope."
        ),
        "implementationMethodology": (
            "Discovery (3 weeks): clinical workflows, integration mapping, security design.\n"
            "MVP Build (12 weeks): registration, appointments, messaging, records view.\n"
            "Integration Sprint (6 weeks): Cerner FHIR, MHR, telehealth, notifications.\n"
            "Pilot & Rollout (5 weeks): 5-clinic pilot, feedback, phased national rollout.\n"
            "Change management and staff training embedded in each phase."
        ),
        "supportAndSla": (
            "24x7 P1 support for clinical-critical incidents during first 90 days.\n"
            "Business-hours L2 support with 2-hour P2 response SLA.\n"
            "Dedicated clinical safety officer for incident triage.\n"
            "Monthly security patch cycle with emergency patch process for CVEs."
        ),
    },
    {
        "rfp_id": "TRAIN-RFP-003",
        "filename": "TRAIN_TTN_Proposal_FinServe_Digital_Onboarding.pptx",
        "customer": "FinServe Bank",
        "executiveSummary": (
            "TTN is pleased to present our proposal for FinServe Bank's digital customer onboarding "
            "and mobile banking platform modernisation. We will deliver a cloud-native solution "
            "supporting KYC/AML verification, account opening in under 5 minutes, and personalised "
            "banking experiences across iOS and Android."
        ),
        "understandingOfRequirements": (
            "Digital account opening for personal and business customers with eKYC.\n"
            "Integration with AUSTRAC reporting and identity providers (GreenID, OCR labs).\n"
            "Mobile banking: balances, transfers, BPAY, card controls, and spending insights.\n"
            "Open Banking (CDR) consent management and data sharing dashboards.\n"
            "Push notifications for transactions, fraud alerts, and marketing opt-in.\n"
            "Accessibility compliance and support for screen readers on mobile."
        ),
        "proposedSolution": (
            "Flutter cross-platform mobile app with native biometric authentication.\n"
            "Camunda BPM for onboarding workflow orchestration and exception handling.\n"
            "Mambu core banking connector for account provisioning and ledger sync.\n"
            "Feature flags via LaunchDarkly for controlled rollout of new capabilities.\n"
            "Adobe Target for personalised product offers based on customer segments."
        ),
        "technicalApproach": (
            "Kubernetes on GCP with Istio service mesh for mTLS between services.\n"
            "Event sourcing for onboarding audit trail with Apache Kafka.\n"
            "API gateway (Kong) with OAuth 2.0, rate limiting, and API versioning.\n"
            "Chaos engineering practices in pre-production environments.\n"
            "Performance testing targeting 10,000 concurrent onboarding sessions."
        ),
        "securityCompliance": (
            "APRA CPS 234 aligned information security controls.\n"
            "ASIC RG 271 compliant design for digital advice disclosures.\n"
            "Hardware security module (HSM) for key management via GCP Cloud HSM.\n"
            "Real-time fraud scoring integration with Feedzai.\n"
            "Annual penetration test and red-team exercise before production launch."
        ),
        "assumptions": (
            "Mambu sandbox and API credentials provided within 2 weeks.\n"
            "FinServe legal team approves KYC vendor contracts before build starts.\n"
            "Apple and Google developer accounts managed by FinServe.\n"
            "Legacy core cutover window limited to approved maintenance windows.\n"
            "Regulatory sign-off gates defined in joint governance plan."
        ),
        "implementationMethodology": (
            "Foundation (4 weeks): architecture, security baseline, CI/CD setup.\n"
            "Onboarding MVP (10 weeks): eKYC, account opening, welcome journey.\n"
            "Mobile Banking (10 weeks): core banking features, cards, payments.\n"
            "Hardening (4 weeks): performance, security testing, APRA evidence pack.\n"
            "Phased rollout: 5,000 customers in pilot, then full marketing launch."
        ),
        "supportAndSla": (
            "Follow-the-sun support model: Sydney + Manila L1, Sydney L2/L3.\n"
            "P1 (service down): 15-minute response, 1-hour workaround target.\n"
            "99.95% uptime SLA for onboarding and mobile API tier.\n"
            "Quarterly disaster recovery drills with FinServe IT operations."
        ),
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate training PPTX proposals")
    parser.add_argument(
        "--output-dir",
        default="./ingestion/historical-rfps",
        help="Directory to write training PPTX files",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    for proposal in TRAINING_PROPOSALS:
        output_path = os.path.join(output_dir, proposal["filename"])
        content = {k: v for k, v in proposal.items() if k not in ("rfp_id", "filename")}
        render_pptx_from_template(content, output_path, proposal["rfp_id"])
        print(f"Created: {output_path}")

    print(f"\nDone. {len(TRAINING_PROPOSALS)} training proposals in {output_dir}")
    print("Ingest with: python ingestion/scripts/ingest.py --dir ingestion/historical-rfps")


if __name__ == "__main__":
    main()
