"""
Test script: Generate a sample legal notice draft and save to output/ folder.

Usage:
    python research/test_draft_output.py

This tests the output saving logic WITHOUT needing the LangGraph server.
It simulates what the pipeline would produce.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.drafting_app import save_draft_to_output, OUTPUT_DIR

SAMPLE_DRAFT = """
============================================================
LEGAL NOTICE UNDER SECTION 80 CPC
============================================================

TO:
{{BORROWER_NAME}}
{{BORROWER_ADDRESS}}
Bengaluru, Karnataka

FROM:
{{LENDER_NAME}}
{{LENDER_ADDRESS}}
Bengaluru, Karnataka

DATE: {{NOTICE_DATE}}

SUBJECT: LEGAL NOTICE FOR RECOVERY OF HAND LOAN OF ₹8,50,000/- (RUPEES EIGHT LAKHS FIFTY THOUSAND ONLY) WITH INTEREST AT 18% PER ANNUM

Sir/Madam,

Under instructions from and on behalf of my client, {{LENDER_NAME}}, I, the undersigned Advocate, do hereby serve upon you the following Legal Notice:

1. BACKGROUND AND FACTS

1.1 That my client and you were known to each other and shared a relationship of trust and confidence.

1.2 That on or about {{LOAN_DATE}}, you approached my client requesting a hand loan of ₹8,50,000/- (Rupees Eight Lakhs Fifty Thousand Only) for your personal/business needs, promising to repay the same within {{REPAYMENT_PERIOD}}.

1.3 That relying upon your assurances and promise to repay, my client transferred a sum of ₹8,50,000/- (Rupees Eight Lakhs Fifty Thousand Only) to your bank account via bank transfer on {{TRANSFER_DATE}}.

1.4 That the said transfer was made from my client's account at {{LENDER_BANK_NAME}} (Account No: {{LENDER_ACCOUNT_NUMBER}}) to your account at {{BORROWER_BANK_NAME}} (Account No: {{BORROWER_ACCOUNT_NUMBER}}), bearing Transaction Reference No: {{TRANSACTION_REFERENCE}}.

1.5 That there exists bank transfer proof evidencing the said transaction, which shall be relied upon as documentary evidence.

2. DEFAULT AND NON-REPAYMENT

2.1 That despite the agreed repayment period having expired and despite repeated oral and telephonic demands, you have failed, neglected, and refused to repay the said amount of ₹8,50,000/- or any part thereof.

2.2 That your conduct amounts to criminal breach of trust and cheating under Sections 405 and 420 of the Indian Penal Code, 1860.

3. INTEREST CLAIM

3.1 That in addition to the principal amount of ₹8,50,000/-, my client is entitled to interest at the rate of 18% per annum from the date of the loan ({{LOAN_DATE}}) till the date of actual repayment.

3.2 That the interest accrued as on the date of this notice amounts to approximately ₹{{ACCRUED_INTEREST}}/-.

4. DEMAND

4.1 You are hereby called upon to pay the following within {{NOTICE_PERIOD}} days from the receipt of this notice:

   (a) Principal amount: ₹8,50,000/-
   (b) Interest at 18% p.a.: ₹{{ACCRUED_INTEREST}}/-
   (c) Legal costs and expenses: ₹{{LEGAL_COSTS}}/-
   ─────────────────────────────────
   Total: ₹{{TOTAL_AMOUNT}}/-

4.2 The said amount shall be paid by way of demand draft/bank transfer in favour of {{LENDER_NAME}}.

5. CONSEQUENCES OF NON-COMPLIANCE

5.1 In the event of your failure to comply with this notice within the stipulated period, my client shall be constrained to initiate appropriate civil and/or criminal proceedings against you before the competent court of jurisdiction in Bengaluru, Karnataka, at your risk, cost, and consequences.

5.2 My client reserves the right to claim enhanced damages, costs of litigation, and any other relief as the Hon'ble Court may deem fit.

6. RESERVATION OF RIGHTS

6.1 This notice is issued without prejudice to any other rights, remedies, and claims available to my client under law.

6.2 A copy of this notice is retained for record and future reference.

VERIFICATION

I, {{LENDER_NAME}}, the sender of this legal notice, do hereby verify that the contents of this notice are true and correct to the best of my knowledge and belief. No part hereof is false and nothing material has been concealed.

Verified at Bengaluru on this {{NOTICE_DATE}}.

_______________________
{{LENDER_NAME}}
(Sender)

Through:
_______________________
{{ADVOCATE_NAME}}
Advocate
{{ADVOCATE_ENROLLMENT_NO}}
{{ADVOCATE_ADDRESS}}
Bengaluru, Karnataka

ENCLOSURES:
1. Bank transfer statement/receipt dated {{TRANSFER_DATE}}
2. Copy of identification documents
3. Record of communication/demand made

NOTE: This notice is sent via Registered Post with Acknowledgement Due / Speed Post / Email at {{BORROWER_EMAIL}}.
""".strip()


def main():
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Draft length: {len(SAMPLE_DRAFT)} characters")

    # Save the draft
    saved = save_draft_to_output(SAMPLE_DRAFT, "legal_notice")

    print("\nSaved files:")
    for fmt, path in saved.items():
        size = os.path.getsize(path)
        print(f"  {fmt.upper()}: {path} ({size:,} bytes)")

    # Count placeholders
    import re
    placeholders = re.findall(r"\{\{([A-Za-z_]+)\}\}", SAMPLE_DRAFT)
    unique = sorted(set(placeholders))
    print(f"\nPlaceholders found: {len(placeholders)} total, {len(unique)} unique")
    for p in unique:
        print(f"  - {{{{{p}}}}}")

    print("\nDone! Check the output/ folder.")


if __name__ == "__main__":
    main()
