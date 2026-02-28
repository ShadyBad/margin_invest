# Incident Response Plan: Breach Procedures

**Document ID:** IRP-BREACH-001
**Version:** 1.0
**Classification:** CONFIDENTIAL
**Effective Date:** 2026-02-27
**Next Review Date:** 2027-02-27
**Document Owner:** Chief Information Security Officer (CISO)
**Approved By:** _[Executive Sponsor Name / Title]_

---

## Document Control

| Version | Date       | Author                | Description                |
|---------|------------|-----------------------|----------------------------|
| 1.0     | 2026-02-27 | Security Operations   | Initial release            |
| —       | —          | —                     | —                          |

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Definitions](#2-definitions)
3. [Incident Classification & Severity Levels](#3-incident-classification--severity-levels)
4. [Roles & Responsibilities (RACI)](#4-roles--responsibilities-raci)
5. [Detection & Identification Procedures](#5-detection--identification-procedures)
6. [Containment Strategy](#6-containment-strategy)
7. [Investigation & Evidence Handling](#7-investigation--evidence-handling)
8. [Eradication & Remediation](#8-eradication--remediation)
9. [Recovery Procedures](#9-recovery-procedures)
10. [Internal & External Communication Plan](#10-internal--external-communication-plan)
11. [Third-Party & Vendor Coordination](#11-third-party--vendor-coordination)
12. [Documentation Requirements](#12-documentation-requirements)
13. [Post-Incident Review & Lessons Learned](#13-post-incident-review--lessons-learned)
14. [Testing & Continuous Improvement](#14-testing--continuous-improvement)
15. [Appendices](#15-appendices)

---

## 1. Purpose & Scope

### 1.1 Purpose

This Incident Response Plan (IRP) establishes the organization's procedures for detecting, responding to, containing, investigating, and recovering from data breaches and security incidents. It provides a structured, repeatable framework that minimizes damage, reduces recovery time and costs, and ensures compliance with applicable regulatory requirements.

This plan aligns with the NIST Computer Security Incident Handling Guide (SP 800-61 Rev. 2) and supports compliance with GDPR, HIPAA, PCI DSS, and ISO 27001 Annex A.16.

### 1.2 Scope

This plan applies to:

- All employees, contractors, temporary staff, and third-party service providers with access to organizational information systems or data.
- All information assets owned, operated, or managed by the organization, including cloud-hosted infrastructure, SaaS applications, on-premises systems, endpoints, and mobile devices.
- All categories of data processed by the organization, including personal data, protected health information (PHI), financial records, intellectual property, and authentication credentials.

This plan does not cover:

- Physical security incidents unrelated to information systems (refer to the Physical Security Plan).
- Business continuity or disaster recovery beyond the scope of incident-triggered restoration (refer to the BCP/DR Plan).

### 1.3 Authority

The CISO has the authority to activate this plan and mobilize the Incident Response Team (IRT). During an active Severity 1 or Severity 2 incident, the Incident Commander has operational authority to make time-critical decisions, including system isolation, credential revocation, and emergency change deployments, without standard change-control approval.

---

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Security Incident** | Any event that actually or potentially jeopardizes the confidentiality, integrity, or availability of an information system or the information the system processes, stores, or transmits. |
| **Data Breach** | A security incident in which sensitive, protected, or confidential data is accessed, disclosed, altered, or destroyed by an unauthorized party, or where there is a reasonable belief such access occurred. |
| **Personal Data** | Any information relating to an identified or identifiable natural person (per GDPR Article 4(1)), including name, email, IP address, financial identifiers, and biometric data. |
| **Protected Health Information (PHI)** | Individually identifiable health information as defined under HIPAA 45 CFR 160.103. |
| **Indicator of Compromise (IOC)** | An artifact observed on a network or in an operating system that, with high confidence, indicates a computer intrusion. Examples: malicious IP addresses, file hashes, abnormal DNS queries. |
| **Incident Response Team (IRT)** | The cross-functional team responsible for executing this plan, comprising security, engineering, legal, communications, and management representatives. |
| **Incident Commander (IC)** | The individual designated to lead the response effort for a specific incident, with decision-making authority during the active response phase. |
| **Chain of Custody** | The documented, chronological record of the seizure, custody, control, transfer, analysis, and disposition of evidence. |
| **Containment** | Actions taken to limit the scope and magnitude of an incident, preventing further unauthorized access or data loss. |
| **Eradication** | The removal of the root cause of an incident from the environment, including malware, unauthorized accounts, and exploited vulnerabilities. |
| **Recovery** | The process of restoring systems and data to normal operational status after an incident has been contained and eradicated. |
| **Tabletop Exercise** | A discussion-based exercise in which team members walk through a simulated incident scenario to validate procedures and identify gaps. |

### 2.1 What Qualifies as a Breach

A security incident is classified as a **data breach** when ANY of the following conditions are met:

1. **Unauthorized access** — A person or system gained access to data they were not authorized to view, and the data includes personal, financial, health, or otherwise regulated information.
2. **Unauthorized disclosure** — Regulated or confidential data was transmitted, published, or otherwise made available to an unintended recipient, whether intentionally or accidentally.
3. **Data exfiltration** — Evidence exists (network logs, forensic artifacts, threat intelligence) that data was copied or transferred outside the organization's controlled environment.
4. **Loss of physical media** — An unencrypted device or storage medium containing regulated data was lost or stolen.
5. **Ransomware with data access** — Ransomware or other destructive malware was deployed in an environment where the attacker had access to regulated data, regardless of whether exfiltration is confirmed.
6. **Credential compromise at scale** — Authentication credentials (passwords, tokens, API keys) for systems containing regulated data were compromised, and unauthorized access cannot be ruled out.

**Safe harbor exception:** If the compromised data was encrypted with a current, industry-standard algorithm (AES-256 or equivalent) and the encryption keys were not compromised in the same incident, the event may be classified as an incident rather than a breach, subject to legal review. This safe harbor does not apply under all regulatory frameworks — consult legal counsel.

---

## 3. Incident Classification & Severity Levels

All incidents are classified by severity to drive appropriate response speed, staffing, and communication requirements.

### 3.1 Severity Matrix

| Severity | Label      | Description | Response SLA | Examples |
|----------|------------|-------------|--------------|----------|
| **SEV-1** | Critical   | Active, confirmed breach of regulated data affecting a large population or critical systems. Existential business risk. | Mobilize IRT within **15 minutes**. Incident Commander assigned immediately. Executive notification within **1 hour**. | Mass PII exfiltration; ransomware across production; compromise of authentication infrastructure; breach of financial/payment systems. |
| **SEV-2** | High       | Confirmed breach with limited scope, or high-confidence indicators that a breach is imminent or in progress. Significant business risk. | Mobilize IRT within **1 hour**. Incident Commander assigned within **2 hours**. Executive notification within **4 hours**. | Single-system compromise containing PII; stolen unencrypted laptop with customer data; insider data theft detected in progress. |
| **SEV-3** | Medium     | Security incident with potential to escalate to a breach, or confirmed unauthorized access to non-regulated data. Moderate business risk. | Triage within **4 hours**. Assign responder within **8 hours**. Management notification within **24 hours**. | Phishing campaign with credential harvesting; unauthorized access to staging/dev environments; malware on an isolated endpoint. |
| **SEV-4** | Low        | Security event or policy violation with no evidence of data compromise. Minimal business risk. | Triage within **24 hours**. Resolve within **5 business days**. | Failed brute-force attempts; policy violations (e.g., shadow IT); low-confidence IOCs from threat intelligence feeds. |

### 3.2 Escalation Criteria

An incident **must** be escalated to the next severity level when any of the following occur:

- Evidence of data exfiltration is discovered.
- The number of affected records exceeds initial estimates by more than 10x.
- A second system or data store is confirmed compromised (lateral movement).
- The attacker demonstrates persistent access after initial containment.
- Regulatory notification timelines may be triggered.
- Media inquiries are received regarding the incident.

### 3.3 De-escalation Criteria

Severity may be reduced when:

- Forensic analysis confirms the scope is smaller than initially assessed.
- Containment is verified and no further unauthorized access is detected for a sustained monitoring period (minimum 24 hours for SEV-1, 12 hours for SEV-2).
- Legal counsel confirms no regulatory notification obligation.

---

## 4. Roles & Responsibilities (RACI)

### 4.1 Incident Response Team Composition

| Role | Filled By | Backup |
|------|-----------|--------|
| **Incident Commander (IC)** | CISO | Director of Security Operations |
| **Security Lead** | Senior Security Engineer | Security Analyst |
| **Engineering Lead** | VP of Engineering | Senior Platform Engineer |
| **Legal Counsel** | General Counsel | External Breach Counsel |
| **Communications Lead** | VP of Communications | Marketing Director |
| **Privacy Officer** | Data Protection Officer | Legal Counsel |
| **Executive Sponsor** | CTO or CEO | COO |
| **Human Resources** | HR Director | HR Manager |
| **Customer Support Lead** | VP of Customer Success | Support Manager |

### 4.2 RACI Matrix

**R** = Responsible | **A** = Accountable | **C** = Consulted | **I** = Informed

| Activity | IC | Security Lead | Engineering Lead | Legal | Comms Lead | Privacy Officer | Executive Sponsor |
|----------|:--:|:---:|:---:|:---:|:---:|:---:|:---:|
| Declare incident severity | **A** | **R** | C | I | I | I | I |
| Activate IRT | **R/A** | I | I | I | I | I | I |
| Technical containment | A | **R** | **R** | I | I | I | I |
| Forensic investigation | A | **R** | C | C | I | I | I |
| Evidence preservation | A | **R** | C | **R** | I | C | I |
| Determine breach scope | A | **R** | C | C | I | **R** | I |
| Regulatory notification | I | C | I | **R/A** | C | **R** | A |
| Customer notification | A | I | I | **R** | **R** | C | A |
| Media / public statement | A | I | I | C | **R** | I | A |
| Executive briefing | **R** | C | C | C | I | I | **A** |
| System recovery | A | C | **R** | I | I | I | I |
| Post-incident review | **R/A** | **R** | **R** | C | C | C | I |
| Plan updates | **A** | **R** | C | C | I | C | I |

### 4.3 Contact Activation

The IRT is activated via the following channels, in order of priority:

1. **Incident Response Platform** — PagerDuty / Opsgenie (automated escalation).
2. **Dedicated IRT Phone Bridge** — _[Insert bridge number]_.
3. **Encrypted Messaging** — Signal group "IRT-Active."
4. **Email** — irt@_[domain]_.com (non-urgent / asynchronous only).

All IRT members must acknowledge activation within the SLA defined for the assigned severity level. Failure to acknowledge triggers automatic escalation to the backup contact.

---

## 5. Detection & Identification Procedures

### 5.1 Detection Sources

| Source | Description | Monitoring Responsibility |
|--------|-------------|--------------------------|
| SIEM / Log Aggregation | Correlated alerts from centralized logging (e.g., Splunk, Elastic, Sentinel) | Security Operations Center (SOC) |
| Endpoint Detection & Response (EDR) | Behavioral alerts from endpoint agents (e.g., CrowdStrike, SentinelOne) | SOC |
| Network Detection | IDS/IPS alerts, NetFlow anomalies, DNS query analysis | SOC / Network Engineering |
| Cloud Security Posture | Misconfigurations, policy violations, anomalous API calls (e.g., AWS GuardDuty, GCP SCC) | Cloud Security |
| Application Monitoring | Anomalous error rates, authentication failures, unexpected data access patterns | Engineering |
| Vulnerability Scanning | Exploitable vulnerabilities correlated with threat intelligence | Vulnerability Management |
| Threat Intelligence | External IOC feeds, dark web monitoring, sector-specific advisories | Threat Intelligence |
| User Reports | Employee or customer reports of suspicious activity | Help Desk / Support |
| Third-Party Notification | Vendor, partner, law enforcement, or researcher notification | Legal / CISO |
| Regulatory / Media | Notification from a regulator or discovery via media reporting | Legal / Communications |

### 5.2 Initial Triage Procedure

Upon receipt of an alert or report, the on-call security analyst shall:

**Step 1: Log the event.**
- Create an incident ticket in the incident management system.
- Record: timestamp, detection source, affected systems/data, reporter identity, initial description.

**Step 2: Validate the alert.**
- Confirm the alert is not a false positive by cross-referencing at least two independent data sources (e.g., SIEM logs + EDR telemetry).
- If unable to validate within 30 minutes, escalate to the Security Lead.

**Step 3: Assess initial scope.**
- Identify affected systems, user accounts, and data stores.
- Determine whether regulated data (PII, PHI, financial) is potentially involved.
- Estimate the volume of records at risk (order of magnitude is acceptable at this stage).

**Step 4: Assign severity.**
- Apply the severity matrix from Section 3.1.
- When in doubt, assign the higher severity level. De-escalation is always preferable to delayed escalation.

**Step 5: Activate the IRT.**
- If SEV-1 or SEV-2: Activate the full IRT per Section 4.3.
- If SEV-3: Notify the Security Lead and assign a dedicated responder.
- If SEV-4: Assign to the on-call analyst queue for resolution within standard SLA.

**Step 6: Begin timeline documentation.**
- Start a running incident timeline (see Appendix C for template).
- All subsequent actions, decisions, and observations are recorded in this timeline.

---

## 6. Containment Strategy

Containment is divided into two phases: short-term (immediate threat suppression) and long-term (sustained controls while investigation proceeds).

### 6.1 Short-Term Containment

**Objective:** Stop the active bleeding. Prevent further unauthorized access or data loss within the first hours of response.

**Actions (execute as applicable, in priority order):**

1. **Isolate compromised systems.**
   - Remove affected hosts from the network (disable switch port, revoke cloud security group access, or apply network ACL deny rules).
   - Do NOT power off systems unless data destruction is actively occurring — live memory is forensically valuable.

2. **Revoke compromised credentials.**
   - Disable or rotate all credentials (user accounts, API keys, service account tokens, OAuth tokens) associated with compromised systems.
   - Force re-authentication for all sessions on affected services.

3. **Block known attacker infrastructure.**
   - Add confirmed malicious IPs, domains, and file hashes to firewall deny lists, DNS sinkholes, and EDR block lists.

4. **Preserve volatile evidence.**
   - Capture memory dumps from compromised hosts before any remediation.
   - Export and preserve current firewall, proxy, DNS, and authentication logs.

5. **Enable enhanced monitoring.**
   - Deploy additional logging or packet capture on the network segments adjacent to compromised systems.
   - Increase alert sensitivity thresholds for related IOCs.

6. **Redirect traffic (if applicable).**
   - For web application breaches, route traffic through a WAF with emergency rule sets.
   - For DNS-based attacks, update DNS records to point to a safe landing page if necessary.

### 6.2 Long-Term Containment

**Objective:** Maintain operational stability while the full investigation and eradication proceed. Long-term containment may last days to weeks.

**Actions:**

1. **Implement temporary architecture changes.**
   - Segment the network to isolate the affected zone from clean infrastructure.
   - Deploy jump hosts or bastion servers for any necessary administrative access to the quarantined zone.

2. **Rebuild compromised credentials and certificates.**
   - Issue new TLS certificates if private keys may have been exposed.
   - Rotate all shared secrets, database passwords, and encryption keys accessible from compromised systems.

3. **Apply emergency patches.**
   - If the attack vector is a known vulnerability, deploy patches to all affected systems, using emergency change procedures.

4. **Establish clean staging environment.**
   - Prepare verified-clean systems to receive restored data and services during recovery.

5. **Continue enhanced monitoring.**
   - Monitor for re-entry attempts using the IOCs and TTPs identified during investigation.

### 6.3 Containment Decision Authority

| Action | SEV-1 / SEV-2 | SEV-3 / SEV-4 |
|--------|---------------|---------------|
| Isolate a single host | Security Lead (immediate) | On-call analyst |
| Isolate a production service | Incident Commander | Security Lead + Engineering Lead |
| Revoke customer-facing credentials | Incident Commander + Executive Sponsor | Incident Commander |
| Block external IP ranges | Security Lead | Security Lead |
| Emergency DNS change | Incident Commander + Engineering Lead | Engineering Lead |

---

## 7. Investigation & Evidence Handling

### 7.1 Investigation Objectives

1. Determine the attack vector (how the attacker gained access).
2. Establish the timeline of unauthorized activity (when it started, when it ended).
3. Identify all affected systems, accounts, and data (the blast radius).
4. Attribute the attack if possible (who, and their objectives).
5. Collect evidence sufficient to support legal proceedings, regulatory filings, and insurance claims.

### 7.2 Forensic Process

**Step 1: Secure the scene.**
- Restrict physical and logical access to compromised systems to authorized investigators only.
- Document the current state of all systems before any investigative action (screenshots, photographs, running process lists).

**Step 2: Create forensic images.**
- Produce bit-for-bit forensic images of all affected storage media using write-blockers.
- Generate cryptographic hashes (SHA-256) of all forensic images and original media.
- Store forensic images on dedicated, encrypted, access-controlled storage.

**Step 3: Collect volatile data.**
- Capture RAM dumps, active network connections, running processes, and open file handles.
- Volatile data collection must precede any system shutdown or reboot.

**Step 4: Collect log data.**
- Aggregate logs from SIEM, firewalls, proxies, DNS servers, authentication systems, application servers, and cloud audit trails.
- Preserve logs beyond their standard retention period by exporting to immutable storage.

**Step 5: Analyze.**
- Construct a detailed timeline correlating all evidence sources.
- Identify IOCs, TTPs (mapped to MITRE ATT&CK where applicable), and lateral movement paths.
- Determine the complete list of data accessed, modified, or exfiltrated.

**Step 6: Document findings.**
- Produce a Forensic Investigation Report (see Appendix C).
- All findings must reference specific evidence items and chain-of-custody records.

### 7.3 Chain of Custody

All physical and digital evidence must be tracked using a Chain of Custody Log that records:

- Evidence item identifier and description.
- Date/time of collection.
- Identity of the collector.
- Storage location and access controls.
- Every transfer of custody (who, when, why).
- Cryptographic hash values at each transfer point.

Evidence handling must preserve admissibility in legal proceedings. When in doubt, consult Legal Counsel before taking any action that might alter evidence.

### 7.4 External Forensic Support

For SEV-1 incidents, or when internal capabilities are insufficient, the Incident Commander shall engage the organization's pre-contracted digital forensics and incident response (DFIR) firm. The DFIR retainer agreement should be reviewed annually and is maintained by _[Legal / CISO]_.

---

## 8. Eradication & Remediation

### 8.1 Eradication

**Objective:** Remove the root cause and all attacker footholds from the environment.

**Actions:**

1. **Remove malware and unauthorized tools.**
   - Use EDR and forensic tools to identify and remove all malicious binaries, scripts, scheduled tasks, and persistence mechanisms.
   - Verify removal by scanning with at least two independent detection engines.

2. **Close the attack vector.**
   - Patch the exploited vulnerability.
   - Reconfigure the misconfigured service.
   - Revoke the compromised credential permanently (not just rotated temporarily).

3. **Eliminate unauthorized access.**
   - Remove attacker-created user accounts, SSH keys, API keys, and OAuth grants.
   - Review and harden all accounts with administrative or elevated privileges.

4. **Verify eradication.**
   - Conduct a full sweep of all systems within the blast radius using updated IOCs.
   - Review authentication logs for any continued anomalous access.
   - Confirm eradication with the Security Lead before proceeding to recovery.

### 8.2 Remediation

**Objective:** Address the systemic weaknesses that allowed the incident to occur or persist.

**Actions:**

1. **Patch management** — Apply all outstanding security patches to affected systems and related infrastructure.
2. **Configuration hardening** — Review and harden configurations per CIS Benchmarks or organizational baseline.
3. **Access control review** — Audit access permissions using the principle of least privilege; remove excessive grants.
4. **Detection gap closure** — Create or tune detection rules to identify the attack's TTPs in future.
5. **Security control deployment** — Implement any new controls identified as necessary (e.g., MFA enforcement, network segmentation, DLP rules).

All remediation actions shall be tracked as action items in the incident ticket with assigned owners and due dates.

---

## 9. Recovery Procedures

### 9.1 Recovery Sequence

Recovery proceeds in a controlled, phased manner. Each phase requires explicit sign-off before proceeding.

**Phase 1: Validate clean state.**
- Confirm eradication is complete (Security Lead sign-off).
- Verify forensic images are preserved and chain of custody is intact.

**Phase 2: Restore from verified backups.**
- Identify the last known-good backup predating the compromise.
- Restore systems from backup to the clean staging environment.
- Validate data integrity (checksums, record counts, application-level consistency checks).

**Phase 3: Harden before reconnection.**
- Apply all patches and configuration changes identified during remediation.
- Rotate all credentials on restored systems.
- Verify that all attacker persistence mechanisms identified during investigation are absent.

**Phase 4: Controlled reintroduction.**
- Reconnect restored systems to the production network in a phased manner (start with least critical).
- Monitor reconnected systems with heightened alerting for a minimum of:
  - SEV-1: 30 days
  - SEV-2: 14 days
  - SEV-3: 7 days

**Phase 5: Confirm normal operations.**
- Validate all business functions are operating correctly.
- Confirm monitoring and alerting have returned to steady state.
- Obtain Engineering Lead and Security Lead sign-off to close the recovery phase.

### 9.2 Recovery Sign-Off

| Milestone | Required Approvers |
|-----------|--------------------|
| Eradication complete | Security Lead |
| Backups validated | Engineering Lead |
| Systems hardened | Security Lead + Engineering Lead |
| Production reconnection | Incident Commander |
| Recovery phase closed | Incident Commander + Executive Sponsor |

---

## 10. Internal & External Communication Plan

### 10.1 Communication Principles

- **Need-to-know basis** — Share incident details only with those who require them for response, legal compliance, or business operations.
- **Single source of truth** — All external communications originate from, or are approved by, the Communications Lead and Legal Counsel.
- **Factual and measured** — Communicate confirmed facts. Do not speculate about scope, attribution, or impact.
- **Timely** — Meet all regulatory notification deadlines. Proactive disclosure is preferable to reactive disclosure.

### 10.2 Executive Reporting

**Frequency:**

| Severity | Initial Briefing | Ongoing Updates | Final Report |
|----------|-----------------|-----------------|--------------|
| SEV-1 | Within 1 hour | Every 4 hours (or on material change) | Within 5 business days of closure |
| SEV-2 | Within 4 hours | Daily | Within 10 business days of closure |
| SEV-3 | Within 24 hours | As needed | Within 15 business days of closure |
| SEV-4 | Weekly summary | — | Included in monthly security report |

**Executive Briefing Content:**

1. Incident summary (what happened, current severity).
2. Business impact (affected systems, customers, data).
3. Current response status and next actions.
4. Regulatory and legal exposure.
5. Resource requirements.
6. Timeline to resolution (estimated).

### 10.3 Legal & Compliance Notification

The Privacy Officer and Legal Counsel are responsible for determining notification obligations based on the jurisdiction, data type, and volume of affected records.

**Key regulatory timelines:**

| Regulation | Notification Deadline | Recipient | Trigger |
|------------|----------------------|-----------|---------|
| **GDPR** (EU) | 72 hours from awareness | Supervisory Authority | Breach of personal data likely to result in risk to individuals |
| **GDPR** (EU) | Without undue delay | Affected individuals | High risk to rights and freedoms |
| **HIPAA** (US) | 60 calendar days from discovery | HHS / OCR | Breach of unsecured PHI |
| **HIPAA** (US) | Without unreasonable delay, ≤60 days | Affected individuals | Breach of unsecured PHI |
| **HIPAA** (US) | Within 60 days of year-end | HHS / OCR | Breaches affecting <500 individuals (annual log) |
| **PCI DSS** | Immediately upon confirmation | Acquiring bank, card brands | Compromise of cardholder data |
| **US State Laws** | Varies (30–90 days typical) | State AG, affected individuals | Breach of covered personal information |
| **SEC** (US) | 4 business days (Form 8-K) | SEC / Investors | Material cybersecurity incident (public companies) |
| **NIS2** (EU) | 24h early warning; 72h notification | CSIRT / competent authority | Significant incident affecting essential/important entities |

**Action:** Legal Counsel shall maintain a current regulatory notification matrix covering all jurisdictions in which the organization operates. This matrix is reviewed quarterly.

### 10.4 Customer / Public Notification

Customer notification is required when a breach involves their data and a legal or ethical obligation to notify exists. All customer communications must be reviewed by Legal Counsel and the Communications Lead before release.

**Notification content must include:**

1. Description of the incident in plain language.
2. Types of data involved.
3. What the organization is doing in response.
4. What the individual can do to protect themselves.
5. Contact information for questions (dedicated support line/email).
6. Information about credit monitoring or identity protection services, if applicable.

**See Appendix B for notification templates.**

### 10.5 Media & Public Communications

- All media inquiries are routed to the Communications Lead.
- No IRT member shall make public statements without Communications Lead and Legal Counsel approval.
- A holding statement shall be prepared within 4 hours of a SEV-1 declaration for use if media inquiries are received before a proactive disclosure is ready.

---

## 11. Third-Party & Vendor Coordination

### 11.1 Vendor Involvement in Incidents

When an incident involves a third-party vendor (the vendor's system was compromised, the vendor's personnel caused the breach, or the vendor's services are needed for response), the following procedures apply:

**Step 1: Notify the vendor.**
- Contact the vendor's designated security contact (maintained in the vendor risk management register).
- Provide a factual summary of the incident and the vendor's potential involvement.
- Request the vendor's incident response plan and point of contact for coordination.

**Step 2: Coordinate investigation.**
- Establish a shared communication channel (encrypted) between the organization's IRT and the vendor's response team.
- Define information-sharing boundaries — what can be shared, under what classification, and with which individuals.
- Jointly review logs, access records, and forensic artifacts.

**Step 3: Enforce contractual obligations.**
- Review the vendor contract for breach notification clauses, SLAs, indemnification, and cooperation requirements.
- Legal Counsel shall assess whether the vendor's actions (or inactions) constitute a contractual breach.
- Document all vendor interactions and commitments for potential future claims.

**Step 4: Assess ongoing risk.**
- Determine whether the vendor should be temporarily disconnected from organizational systems.
- If the vendor is a critical service provider, activate the contingency plan for that vendor (maintained in the business continuity plan).

### 11.2 Pre-Contracted Response Partners

The organization maintains retainer agreements with the following external partners, to be activated by the Incident Commander or CISO:

| Partner Type | Purpose | Activation Trigger |
|-------------|---------|-------------------|
| DFIR Firm | Digital forensics and incident response | SEV-1, or when internal capability is exceeded |
| External Legal Counsel | Breach counsel, regulatory filings, litigation hold | All confirmed breaches |
| Crisis Communications | Public relations, media management | SEV-1 with media exposure risk |
| Credit Monitoring Provider | Identity protection services for affected individuals | Breach involving SSN, financial, or identity data |
| Cyber Insurance Broker | Claims initiation, coverage coordination | All confirmed breaches |

**Activation procedure:** Notify the partner via the emergency contact on file, provide the incident ticket number, and establish a shared communication channel. Cyber insurance carrier must be notified within the timeframe specified in the policy (typically 24-48 hours).

---

## 12. Documentation Requirements

### 12.1 Mandatory Documentation

Every incident, regardless of severity, must produce the following documentation:

| Document | Owner | When Created | Retention |
|----------|-------|-------------|-----------|
| **Incident Ticket** | On-call Analyst | At detection | 7 years |
| **Running Timeline** | Incident Commander | At IRT activation | 7 years |
| **Evidence Log / Chain of Custody** | Security Lead | At evidence collection | 7 years (or per legal hold) |
| **Communication Log** | Communications Lead | At first external communication | 7 years |
| **Forensic Investigation Report** | Security Lead / DFIR | During investigation | 7 years |
| **Executive Summary** | Incident Commander | At incident closure | 7 years |
| **Post-Incident Review Report** | Incident Commander | Within 10 business days of closure | 7 years |
| **Regulatory Notification Records** | Legal Counsel | At each notification | Per regulation (minimum 7 years) |

### 12.2 Documentation Standards

- All timestamps in UTC.
- All documents stored in the designated incident repository with access restricted to IRT members and Legal Counsel.
- Documents created during an active incident are marked CONFIDENTIAL — ATTORNEY-CLIENT PRIVILEGED where directed by Legal Counsel.
- No incident documentation shall be stored on personal devices, personal cloud storage, or unencrypted removable media.

---

## 13. Post-Incident Review & Lessons Learned

### 13.1 Post-Incident Review Meeting

A post-incident review (PIR) shall be conducted after every SEV-1, SEV-2, and SEV-3 incident:

| Severity | PIR Deadline | Attendees |
|----------|-------------|-----------|
| SEV-1 | Within 5 business days of closure | Full IRT + Executive Sponsor |
| SEV-2 | Within 10 business days of closure | IRT core members |
| SEV-3 | Within 15 business days of closure | Security Lead + assigned responders |

### 13.2 PIR Agenda

1. **Incident timeline walkthrough** — Reconstruct the incident chronologically using the running timeline.
2. **What went well** — Identify procedures, tools, and decisions that were effective.
3. **What could be improved** — Identify gaps, delays, communication failures, and tooling limitations.
4. **Root cause analysis** — Identify the underlying technical, process, and human factors. Use the "5 Whys" method for non-trivial incidents.
5. **Action items** — Define specific, measurable corrective actions with owners and due dates.
6. **Metrics review:**
   - Time to detect (TTD): Time from initial compromise to detection.
   - Time to contain (TTC): Time from detection to effective containment.
   - Time to eradicate (TTE): Time from containment to verified eradication.
   - Time to recover (TTR): Time from eradication to normal operations.
   - Notification compliance: Whether all regulatory deadlines were met.

### 13.3 PIR Output

The PIR produces a Post-Incident Review Report containing:

- Executive summary.
- Detailed timeline with key decision points.
- Root cause analysis.
- Impact assessment (records affected, financial cost, business disruption).
- Action items table (action, owner, priority, due date, status).
- Recommendations for plan updates.

The PIR Report is reviewed by the CISO and distributed to the Executive Sponsor. Action items are tracked to completion in the organization's risk management or project tracking system.

---

## 14. Testing & Continuous Improvement

### 14.1 Testing Schedule

| Exercise Type | Frequency | Scope | Led By |
|--------------|-----------|-------|--------|
| **Tabletop Exercise** | Quarterly | Scenario-based walkthrough with IRT and executives | CISO |
| **Technical Drill** | Semi-annually | Hands-on simulation (e.g., simulated phishing, red team, forensic challenge) | Security Lead |
| **Full Simulation** | Annually | End-to-end breach simulation including communications, legal notification, and vendor coordination | CISO + External Facilitator |
| **Plan Review** | Annually (and after every SEV-1/SEV-2 incident) | Full document review, contact list validation, regulatory matrix update | CISO |

### 14.2 Exercise Requirements

- Each exercise must have defined objectives, a scenario, and evaluation criteria.
- Exercise results are documented in an After-Action Report (AAR).
- Identified gaps are recorded as action items with owners and tracked to completion.
- Contact lists and escalation matrices are validated during every exercise.

### 14.3 Continuous Improvement Process

1. **PIR action items** — Tracked in a central register; reviewed monthly by the CISO.
2. **Exercise findings** — Integrated into the next plan revision cycle.
3. **Threat landscape updates** — The Security Lead monitors emerging threats and updates detection rules, playbooks, and this plan accordingly.
4. **Regulatory changes** — Legal Counsel monitors regulatory developments and updates the notification matrix and procedures.
5. **Metrics trending** — TTD, TTC, TTE, and TTR are tracked over time; targets are set annually and reviewed quarterly.

### 14.4 Plan Revision Control

All changes to this plan follow the document control process:

- Changes are proposed by the CISO or delegate.
- Material changes require review by Legal Counsel and the Executive Sponsor.
- The updated plan is distributed to all IRT members with a changelog summary.
- Previous versions are archived and retained per the documentation retention policy.

---

## 15. Appendices

### Appendix A: Escalation Matrix

#### A.1 Severity-Based Escalation

```
SEV-4 (Low)
  └─ On-call Security Analyst
      └─ [if unable to resolve in 24h] → Security Lead

SEV-3 (Medium)
  └─ On-call Security Analyst + Security Lead
      └─ [if regulated data potentially involved] → Escalate to SEV-2
      └─ [if no progress in 8h] → Incident Commander

SEV-2 (High)
  └─ Incident Commander + Full IRT
      └─ [if scope expands or containment fails] → Escalate to SEV-1
      └─ Legal Counsel notified (breach assessment)
      └─ Executive Sponsor briefed within 4h

SEV-1 (Critical)
  └─ Incident Commander + Full IRT + Executive Sponsor
      └─ DFIR firm activated
      └─ Cyber insurance carrier notified
      └─ Board notification within 24h (if material)
      └─ Regulatory notification clock starts
```

#### A.2 Contact Directory

| Role | Primary Contact | Phone | Email | Backup Contact |
|------|----------------|-------|-------|---------------|
| Incident Commander | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| Security Lead | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| Engineering Lead | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| Legal Counsel | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| Communications Lead | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| Privacy Officer | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| Executive Sponsor | _[Name]_ | _[Phone]_ | _[Email]_ | _[Backup Name]_ |
| DFIR Firm | _[Firm Name]_ | _[Phone]_ | _[Email]_ | — |
| External Breach Counsel | _[Firm Name]_ | _[Phone]_ | _[Email]_ | — |
| Cyber Insurance Broker | _[Firm Name]_ | _[Phone]_ | _[Email]_ | — |

> **This directory must be validated quarterly and after any personnel change.**

---

### Appendix B: Breach Notification Templates

#### B.1 Regulatory Authority Notification (GDPR Supervisory Authority)

```
To: [Supervisory Authority Name]
From: [Organization Name], [Data Protection Officer Name]
Date: [Date]
Subject: Data Breach Notification Pursuant to GDPR Article 33

1. NATURE OF THE BREACH
   Description: [Brief factual description of the breach]
   Date/time of breach: [Date/time or estimated range]
   Date/time of discovery: [Date/time]
   Categories of data: [e.g., names, email addresses, financial data]
   Categories of data subjects: [e.g., customers, employees]
   Approximate number of data subjects: [Number or range]
   Approximate number of records: [Number or range]

2. DATA PROTECTION OFFICER CONTACT
   Name: [Name]
   Email: [Email]
   Phone: [Phone]

3. LIKELY CONSEQUENCES
   [Description of the likely consequences of the breach for
   data subjects, including risk of identity theft, financial
   loss, reputational damage, etc.]

4. MEASURES TAKEN
   Containment measures: [Description]
   Remediation measures: [Description]
   Measures to mitigate adverse effects on data subjects: [Description]

5. ADDITIONAL INFORMATION
   [Any additional context, pending investigation findings,
   or planned follow-up notifications]

This notification is made without undue delay and within 72 hours
of becoming aware of the breach, in compliance with GDPR Article 33.
```

#### B.2 Customer Notification (General)

```
Subject: Important Security Notice from [Organization Name]

Dear [Customer Name],

We are writing to inform you of a security incident that may
have involved your personal information.

WHAT HAPPENED
On [date], we discovered that [brief, plain-language description
of the incident]. Upon discovery, we immediately [brief description
of response actions — e.g., "secured our systems, launched an
investigation, and engaged independent cybersecurity experts"].

WHAT INFORMATION WAS INVOLVED
The incident may have involved the following types of your
personal information: [list specific data types — e.g., "your
name, email address, and encrypted password"].

WHAT WE ARE DOING
[Description of remediation steps, monitoring measures, and
any services being offered — e.g., "We have reset all affected
passwords and are offering 24 months of complimentary credit
monitoring through [Provider Name]."]

WHAT YOU CAN DO
We recommend the following steps to protect yourself:
- [Action 1 — e.g., "Change your password on any other service
  where you used the same password."]
- [Action 2 — e.g., "Monitor your financial statements for
  any unusual activity."]
- [Action 3 — e.g., "Enroll in the complimentary credit
  monitoring service using the enclosed activation code."]

HOW TO REACH US
If you have questions or concerns, please contact our dedicated
support team:
- Phone: [Dedicated incident support line]
- Email: [Dedicated incident support email]
- Hours: [Operating hours]

We sincerely regret this incident and are committed to protecting
your information. We will continue to review and enhance our
security practices to help prevent future incidents.

Sincerely,
[Name]
[Title]
[Organization Name]
```

#### B.3 Media Holding Statement

```
[Organization Name] is aware of a security incident affecting
[general description — e.g., "certain customer data"].

Upon discovery, we immediately activated our incident response
procedures, engaged independent cybersecurity experts, and
notified relevant authorities.

Protecting the security and privacy of our [customers/users/
members] is our highest priority. We are actively investigating
this matter and will provide updates as our investigation
progresses.

Individuals who believe they may be affected can contact
[dedicated support line/email] for assistance.

We have no further comment at this time and will provide
additional information when appropriate.

Contact: [Communications Lead Name]
Email: [Media relations email]
Phone: [Media relations phone]
```

---

### Appendix C: Incident Report Template

```
═══════════════════════════════════════════════════════
           SECURITY INCIDENT REPORT
═══════════════════════════════════════════════════════

INCIDENT IDENTIFICATION
───────────────────────────────────────────────────────
Incident ID:         [INC-YYYY-NNNN]
Severity:            [SEV-1 / SEV-2 / SEV-3 / SEV-4]
Status:              [Open / Contained / Eradicated / Recovered / Closed]
Incident Commander:  [Name]
Report Date:         [Date]
Report Author:       [Name]

TIMELINE
───────────────────────────────────────────────────────
Initial Compromise:      [Date/Time UTC] (estimated/confirmed)
Detection:               [Date/Time UTC]
IRT Activation:          [Date/Time UTC]
Containment (short):     [Date/Time UTC]
Containment (long):      [Date/Time UTC]
Eradication Complete:    [Date/Time UTC]
Recovery Complete:       [Date/Time UTC]
Incident Closed:         [Date/Time UTC]

METRICS
───────────────────────────────────────────────────────
Time to Detect (TTD):    [Duration]
Time to Contain (TTC):   [Duration]
Time to Eradicate (TTE): [Duration]
Time to Recover (TTR):   [Duration]

INCIDENT SUMMARY
───────────────────────────────────────────────────────
[2-3 paragraph summary of the incident in plain language,
covering: what happened, how it was discovered, what data/
systems were affected, and current status.]

ATTACK VECTOR & ROOT CAUSE
───────────────────────────────────────────────────────
Attack Vector:       [e.g., phishing, vulnerability exploitation,
                      credential stuffing, insider threat]
Root Cause:          [Detailed root cause analysis]
MITRE ATT&CK TTPs:  [List applicable technique IDs]

SCOPE & IMPACT
───────────────────────────────────────────────────────
Systems Affected:         [List]
Data Types Compromised:   [List]
Records Affected:         [Count or estimate]
Business Impact:          [Description of operational disruption]
Financial Impact:         [Estimated cost, if known]
Regulatory Implications:  [List applicable regulations triggered]

CONTAINMENT & ERADICATION ACTIONS
───────────────────────────────────────────────────────
[Numbered list of all containment and eradication actions
taken, with dates and responsible parties.]

1. [Date/Time] — [Action] — [Performed by]
2. [Date/Time] — [Action] — [Performed by]
...

RECOVERY ACTIONS
───────────────────────────────────────────────────────
[Numbered list of recovery actions taken.]

1. [Date/Time] — [Action] — [Performed by]
...

NOTIFICATIONS
───────────────────────────────────────────────────────
| Recipient              | Date Notified | Method | Status   |
|------------------------|---------------|--------|----------|
| [Supervisory Authority]| [Date]        | [Method]| [Ack/Pending] |
| [Affected Individuals] | [Date]        | [Method]| [Sent/Pending] |
| [Insurance Carrier]    | [Date]        | [Method]| [Ack/Pending] |
| [Law Enforcement]      | [Date]        | [Method]| [Ack/Pending] |

EVIDENCE INVENTORY
───────────────────────────────────────────────────────
| Evidence ID | Description | Hash (SHA-256) | Custodian |
|-------------|-------------|----------------|-----------|
| [ID]        | [Desc]      | [Hash]         | [Name]    |
...

LESSONS LEARNED & ACTION ITEMS
───────────────────────────────────────────────────────
| # | Action Item | Owner | Priority | Due Date | Status |
|---|------------|-------|----------|----------|--------|
| 1 | [Action]   | [Name]| [H/M/L] | [Date]   | [Open] |
| 2 | [Action]   | [Name]| [H/M/L] | [Date]   | [Open] |
...

APPROVALS
───────────────────────────────────────────────────────
Incident Commander:   ________________  Date: ________
Security Lead:        ________________  Date: ________
Legal Counsel:        ________________  Date: ________
Executive Sponsor:    ________________  Date: ________
```

---

**— End of Incident Response Plan —**

*This document is classified CONFIDENTIAL and is intended for authorized personnel only. Unauthorized distribution is prohibited.*
