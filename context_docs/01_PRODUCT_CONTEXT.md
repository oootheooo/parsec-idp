# Product Context

## Product name
**Parsec**

Working descriptor:
> Universal document extraction, review, and automation infrastructure for business workflows.

This is not merely an OCR app. It is a general-purpose Intelligent Document Processing (IDP) platform.

## Problem

Businesses receive information trapped in:
- PDFs;
- scanned forms;
- receipts;
- invoices;
- purchase orders;
- contracts;
- bank statements;
- identity documents;
- Office files;
- spreadsheets;
- images;
- statements and reports.

Traditional approaches require rigid templates or manual encoding. LLM-only approaches can be visually capable but are hard to validate, can hallucinate, and often throw away useful geometry/layout information.

The product combines:
1. deterministic/native parsing;
2. OCR;
3. layout/table reconstruction;
4. multimodal LLM understanding;
5. strict user-defined schemas;
6. source evidence;
7. validations;
8. human review;
9. APIs/workflows.

## Product philosophy

### Universal engine, reusable processors
The core engine should accept arbitrary supported documents. A **Processor** defines what the user wants extracted.

Examples:
- "Invoice Processor"
- "BIR Form Processor"
- "Supplier Accreditation Form"
- "Lease Contract"
- "Proof of Delivery"
- "Resume/CV"
- "Custom Compliance Checklist"

A processor contains:
- name and description;
- optional document type hints;
- JSON Schema;
- extraction instructions;
- validation rules;
- review rules;
- optional workflow rules.

### Extraction is evidence-based
An extracted field should not just be:
`total = 125000`.

It should ideally contain:
- raw model value;
- normalized value;
- confidence;
- page number;
- bounding box or source block IDs;
- source text/snippet;
- validation messages;
- review status;
- reviewer override.

### Human review is a first-class workflow
The system must be useful even when extraction is imperfect. Low-confidence or invalid fields should be easy to find and correct.

## Target users

Initial:
- operations teams;
- finance/accounting teams;
- BPO/shared services;
- agencies/software integrators;
- SMEs with document-heavy workflows;
- internal Parsec client projects.

Future:
- enterprise document automation;
- developer/API customers;
- regulated workflows;
- high-volume processing.

## Commercial shape

Potential plans can eventually meter:
- pages processed;
- LLM pages/tokens;
- storage;
- API volume;
- users/workspaces;
- premium OCR/model providers.

Billing is explicitly out of MVP scope, but usage events should be recorded so billing can be added later.

## Product boundaries

MVP does not aim to:
- replace a full ERP;
- provide legal conclusions;
- guarantee identity verification/KYC compliance;
- train custom foundation models;
- create advanced BPMN workflow authoring;
- provide handwriting-specialized guarantees.

The architecture should leave room for these later.
