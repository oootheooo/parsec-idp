# Sample Processor Schemas

These are seed examples, not special cases in the engine.

## Invoice

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "invoice_number": {
      "type": ["string", "null"],
      "description": "Invoice identifier exactly as shown."
    },
    "invoice_date": {
      "type": ["string", "null"],
      "description": "Invoice date in YYYY-MM-DD when unambiguous."
    },
    "supplier": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "name": {"type": ["string", "null"]},
        "tax_id": {"type": ["string", "null"]},
        "address": {"type": ["string", "null"]}
      },
      "required": ["name", "tax_id", "address"]
    },
    "currency": {"type": ["string", "null"]},
    "subtotal": {"type": ["number", "null"]},
    "tax": {"type": ["number", "null"]},
    "total": {"type": ["number", "null"]},
    "line_items": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "description": {"type": ["string", "null"]},
          "quantity": {"type": ["number", "null"]},
          "unit_price": {"type": ["number", "null"]},
          "amount": {"type": ["number", "null"]}
        },
        "required": ["description", "quantity", "unit_price", "amount"]
      }
    }
  },
  "required": [
    "invoice_number",
    "invoice_date",
    "supplier",
    "currency",
    "subtotal",
    "tax",
    "total",
    "line_items"
  ]
}
```

Suggested validation:
- if subtotal, tax, total present -> approx_equal(subtotal + tax, total, 2%)
- total >= 0

## Receipt
Fields:
- merchant_name
- receipt_number
- date
- currency
- line_items
- subtotal
- tax
- discounts
- total
- payment_method

## Purchase Order
Fields:
- po_number
- issue_date
- buyer
- supplier
- delivery_address
- currency
- items
- subtotal
- tax
- total
- terms

## Contract Metadata
Fields:
- title
- contract_type
- effective_date
- expiration_date
- parties[]
- governing_law
- payment_terms
- renewal_terms
- termination_terms
- key_obligations[]
- signatures[]

Prompt note: summarize clauses only when schema explicitly asks for summaries; otherwise preserve exact named metadata.

## Bank Statement Summary
Fields:
- institution
- account_name
- account_number_masked_or_exact_as_requested
- statement_start
- statement_end
- opening_balance
- closing_balance
- currency
- transactions[]

Transaction:
- date
- description
- debit
- credit
- balance

## Identity Document
Fields:
- document_type
- issuing_country
- document_number
- full_name
- date_of_birth
- issue_date
- expiry_date
- address

Do not market this seed as identity verification. It is text/data extraction only.
