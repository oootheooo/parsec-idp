import asyncio
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ProcessorTemplate


def nullable(kind: str = "string") -> dict[str, Any]: return {"type":[kind,"null"]}
def object_schema(fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"type":"object","additionalProperties":False,"properties":fields,"required":list(fields)}

PRESETS = [
    ("invoice","Invoice","Supplier invoices with totals and line items",object_schema({"invoice_number":nullable(),"invoice_date":nullable(),"supplier":object_schema({"name":nullable(),"tax_id":nullable(),"address":nullable()}),"currency":nullable(),"subtotal":nullable("number"),"tax":nullable("number"),"total":nullable("number"),"line_items":{"type":"array","items":object_schema({"description":nullable(),"quantity":nullable("number"),"unit_price":nullable("number"),"amount":nullable("number")})}})),
    ("receipt","Receipt","Retail receipts and payment details",object_schema({"merchant_name":nullable(),"receipt_number":nullable(),"date":nullable(),"currency":nullable(),"line_items":{"type":"array","items":object_schema({"description":nullable(),"amount":nullable("number")})},"subtotal":nullable("number"),"tax":nullable("number"),"discounts":nullable("number"),"total":nullable("number"),"payment_method":nullable()})),
    ("purchase_order","Purchase Order","Purchase order header and items",object_schema({"po_number":nullable(),"issue_date":nullable(),"buyer":nullable(),"supplier":nullable(),"delivery_address":nullable(),"currency":nullable(),"items":{"type":"array","items":object_schema({"description":nullable(),"quantity":nullable("number"),"amount":nullable("number")})},"subtotal":nullable("number"),"tax":nullable("number"),"total":nullable("number"),"terms":nullable()})),
    ("contract","Generic Contract Metadata","Contract parties, dates, terms and obligations",object_schema({"title":nullable(),"contract_type":nullable(),"effective_date":nullable(),"expiration_date":nullable(),"parties":{"type":"array","items":nullable()},"governing_law":nullable(),"payment_terms":nullable(),"renewal_terms":nullable(),"termination_terms":nullable(),"key_obligations":{"type":"array","items":nullable()},"signatures":{"type":"array","items":nullable()}})),
    ("bank_statement","Bank Statement Summary","Account balances and transactions",object_schema({"institution":nullable(),"account_name":nullable(),"account_number":nullable(),"statement_start":nullable(),"statement_end":nullable(),"opening_balance":nullable("number"),"closing_balance":nullable("number"),"currency":nullable(),"transactions":{"type":"array","items":object_schema({"date":nullable(),"description":nullable(),"debit":nullable("number"),"credit":nullable("number"),"balance":nullable("number")})}})),
    ("identity","ID / Identity Document","Text extraction only; not identity verification",object_schema({"document_type":nullable(),"issuing_country":nullable(),"document_number":nullable(),"full_name":nullable(),"date_of_birth":nullable(),"issue_date":nullable(),"expiry_date":nullable(),"address":nullable()})),
    ("blank","Custom Blank Processor","Start with an empty extraction schema",object_schema({})),
]

async def seed():
    async with SessionLocal() as db:
        for key,name,description,schema in PRESETS:
            if not await db.scalar(select(ProcessorTemplate.id).where(ProcessorTemplate.key==key)):
                validations=[]
                if key=="invoice": validations=[{"key":"totals_match","expression":{"op":"approx_equal","left":{"op":"add","args":[{"op":"path","path":"$.subtotal"},{"op":"path","path":"$.tax"}]},"right":{"op":"path","path":"$.total"},"tolerance":0.02},"message":"Subtotal plus tax must match total"}]
                db.add(ProcessorTemplate(key=key,name=name,description=description,schema_json=schema,instructions=f"Extract the requested {name.lower()} fields only from the document.",validation_config=validations,review_config={"threshold":0.7,"always_review":True}))
        await db.commit()

if __name__=="__main__": asyncio.run(seed())
