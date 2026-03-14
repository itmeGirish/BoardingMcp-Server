# SKILL: civil-classification

## Purpose
Complete civil suit classification taxonomy for Indian courts. Use when building/updating LKB entries, intake prompts, or cause_type lists. Every cause type in the LKB must map to exactly one group below.

---

## AXIS 1: CAUSE GROUPS (16 groups, 85 causes)

### 1. MONEY_AND_DEBT (15 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | money_recovery_loan | Loan recovery (hand loan, bank loan, promissory note) |
| 2 | money_recovery_goods | Goods sold & delivered — unpaid invoices |
| 3 | money_recovery_services | Services rendered — unpaid professional fees |
| 4 | money_recovery_deposit | Security deposit / advance refund |
| 5 | money_recovery_cheque_dishonour | Cheque bounce (civil remedy, not S.138 NI Act) |
| 6 | money_recovery_negotiable_instrument | Promissory note, bill of exchange enforcement |
| 7 | money_recovery_bond | Bond / debenture / fixed deposit recovery |
| 8 | money_recovery_wages | Unpaid wages / salary / remuneration |
| 9 | money_recovery_quantum_meruit | Quantum meruit — reasonable value of work done |
| 10 | money_recovery_unjust_enrichment | Unjust enrichment / money had and received |
| 11 | guarantee_recovery | Recovery from guarantor / surety |
| 12 | indemnity_recovery | Recovery under indemnity contract |
| 13 | contribution_recovery | Co-obligor contribution (S.43 ICA) |
| 14 | judgment_debt_recovery | Execution of money decree / judgment debt |
| 15 | interest_only_recovery | Standalone interest claim (S.34 CPC / S.3 Interest Act) |

### 2. CONTRACT_AND_COMMERCIAL (9 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | breach_of_contract | General breach of contract — damages |
| 2 | breach_dealership_franchise | Dealership / franchise / distributorship termination |
| 3 | breach_employment_contract | Employment contract breach (non-compete, wrongful termination) |
| 4 | breach_construction_contract | Construction / works contract disputes |
| 5 | breach_agency_contract | Principal-agent disputes |
| 6 | specific_performance | Specific performance of contract (SRA 1963) |
| 7 | rescission_of_contract | Rescission / cancellation of contract |
| 8 | rectification_of_instrument | Rectification of deed / instrument (S.26 SRA) |
| 9 | cancellation_of_instrument | Cancellation of void/voidable instrument (S.31 SRA) |

### 3. IMMOVABLE_PROPERTY (16 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | recovery_of_possession_tenant | Possession from tenant (lease expired / determined) |
| 2 | recovery_of_possession_licensee | Possession from licensee (license revoked) |
| 3 | recovery_of_possession_trespasser | Possession from trespasser / encroacher |
| 4 | recovery_of_possession_co_owner | Possession from co-owner (ouster) |
| 5 | declaration_title | Declaration of title / ownership |
| 6 | partition | Partition and separate possession |
| 7 | mortgage_redemption | Mortgage redemption (S.60 TPA) |
| 8 | mortgage_foreclosure | Mortgage foreclosure (S.67 TPA) |
| 9 | mortgage_sale | Mortgage sale (Order XXXIV Rule 5 CPC) |
| 10 | cancellation_sale_deed | Cancellation of sale deed / conveyance |
| 11 | easement | Easement rights (Indian Easements Act 1882) |
| 12 | adverse_possession | Title by adverse possession (S.27 Limitation Act) |
| 13 | boundary_dispute | Boundary dispute / demarcation |
| 14 | pre_emption | Pre-emption right |
| 15 | specific_performance_immovable | Specific performance of sale agreement (immovable property) |
| 16 | mesne_profits | Mesne profits / damages for wrongful possession |

### 4. INJUNCTION_AND_DECLARATORY (2 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | permanent_injunction | Permanent injunction (S.38 SRA) |
| 2 | mandatory_injunction | Mandatory injunction (S.39 SRA) |

### 5. TORT_AND_CIVIL_WRONG (15 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | negligence_personal_injury | Negligence — personal injury / bodily harm |
| 2 | negligence_property_damage | Negligence — property damage / economic loss |
| 3 | medical_negligence | Medical negligence / malpractice |
| 4 | motor_accident_claim | Motor accident compensation (MV Act) |
| 5 | defamation | Civil defamation — damages for reputation injury |
| 6 | nuisance_private | Private nuisance — interference with property enjoyment |
| 7 | nuisance_public | Public nuisance — civil remedy (S.91 CPC) |
| 8 | trespass_to_land | Trespass to immovable property |
| 9 | trespass_to_goods | Trespass to / conversion of movable property |
| 10 | malicious_prosecution | Malicious prosecution |
| 11 | false_imprisonment | False imprisonment / wrongful confinement |
| 12 | fraud_misrepresentation | Fraud / misrepresentation — civil remedy |
| 13 | product_liability | Product liability / defective goods |
| 14 | professional_negligence | Professional negligence (lawyer, CA, engineer) |
| 15 | environmental_tort | Environmental damage / pollution — civil remedy |

### 6. TENANCY_AND_RENT (3 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | eviction | Eviction under Rent Control Act (state-specific) |
| 2 | arrears_of_rent | Recovery of arrears of rent |
| 3 | mesne_profits_after_eviction | Mesne profits post-eviction / holding over |

### 7. PARTNERSHIP_AND_BUSINESS (2 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | partnership_dissolution | Partnership dissolution and accounts (S.44 IPA) |
| 2 | partner_restraint | Restraining partner from acting beyond authority |

### 8. IP_CIVIL (4 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | passing_off | Passing off / trademark infringement (civil) |
| 2 | copyright_infringement | Copyright infringement — damages + injunction |
| 3 | patent_infringement | Patent infringement — damages + injunction |
| 4 | design_infringement | Design infringement — damages + injunction |

### 9. TRUST_AND_FIDUCIARY (2 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | trust_dispute | Trust property / trustee removal / breach of trust |
| 2 | benami_declaration | Benami property declaration (Benami Act 1988) |

### 10. EXECUTION_AND_RESTITUTION (3 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | execution_petition | Execution of decree (Order XXI CPC) |
| 2 | court_sale_challenge | Challenge to court auction / sale |
| 3 | restitution | Restitution (S.144 CPC) |

### 11. SPECIAL_AND_MISCELLANEOUS (2 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | recurring_right | Successive breach / recurring right (S.22 Limitation Act) |
| 2 | hereditary_office | Hereditary office / emoluments |

### 12. SUCCESSION_AND_ESTATE (3 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | probate | Probate of will (S.276 ISA) |
| 2 | letters_of_administration | Letters of administration |
| 3 | succession_certificate | Succession certificate (S.372 ISA) |

### 13. FAMILY_AND_GUARDIANSHIP (4 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | divorce | Divorce petition (HMA / Special Marriage Act) |
| 2 | maintenance | Maintenance (S.125 CrPC / HMA S.24-25) |
| 3 | custody | Child custody / guardianship (GWA 1890) |
| 4 | minor_property | Minor's property management (GWA 1890) |

### 14. ARBITRATION_COURT (4 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | arbitration_s9_interim | S.9 interim relief (Arbitration Act 1996) |
| 2 | arbitration_s11_appointment | S.11 arbitrator appointment |
| 3 | arbitration_s34_set_aside | S.34 set aside arbitral award |
| 4 | arbitration_s37_appeal | S.37 appeal against arbitral order |

### 15. CONSUMER_AND_SPECIAL_FORA (3 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | consumer_complaint | Consumer complaint (Consumer Protection Act 2019) |
| 2 | sarfaesi_challenge | SARFAESI Act challenge (S.17 DRT) |
| 3 | ibc_application | IBC application (S.7/9/10 NCLT) |

### 16. PUBLIC_AND_SPECIAL_PROCEEDINGS (2 causes)
| # | cause_type | Description |
|---|-----------|-------------|
| 1 | public_trust_s92 | S.92 CPC public trust / charity |
| 2 | public_premises_eviction | Public Premises Eviction Act |

---

## AXIS 2: STAGE GROUPS (12 groups, 59 families)

### A. PRE_SUIT (2 families)
| # | family | Description |
|---|--------|-------------|
| 1 | caveat | Caveat petition (S.148A CPC) |
| 2 | notice_s80 | S.80 CPC notice to government |

### B. INSTITUTION (10 families)
| # | family | Description |
|---|--------|-------------|
| 1 | plaint | Original suit plaint |
| 2 | interpleader | Interpleader suit (Order XXXV) |
| 3 | indigent_suit | Suit as indigent person (Order XXXIII) |
| 4 | representative_suit | Representative suit (Order I Rule 8) |
| 5 | government_suit | Suit by/against government |
| 6 | minor_suit | Suit by/against minor through next friend |
| 7 | condonation_delay | Condonation of delay application |
| 8 | return_plaint | Return of plaint (Order VII Rule 10) |
| 9 | transfer_petition | Transfer petition (S.24/25 CPC) |
| 10 | vakalatnama | Vakalatnama / memo of appearance |

### C. PLEADINGS (11 families)
| # | family | Description |
|---|--------|-------------|
| 1 | written_statement | Written statement (Order VIII) |
| 2 | set_off | Set-off (Order VIII Rule 6) |
| 3 | counterclaim | Counterclaim (Order VIII Rule 6A) |
| 4 | replication | Replication to written statement |
| 5 | amendment_plaint | Amendment of plaint (Order VI Rule 17) |
| 6 | impleadment | Impleadment / addition of party (Order I Rule 10) |
| 7 | rejection_plaint | Rejection of plaint (Order VII Rule 11) |
| 8 | additional_documents | Application to file additional documents |
| 9 | leave_to_defend | Leave to defend (Order XXXVII) |
| 10 | appearance | Memo of appearance |
| 11 | substitution | Legal representative substitution (Order XXII) |

### D. INTERIM_RELIEF (7 families)
| # | family | Description |
|---|--------|-------------|
| 1 | temporary_injunction | Temporary injunction (Order XXXIX) |
| 2 | mandatory_temporary_injunction | Mandatory temporary injunction |
| 3 | receiver | Appointment of receiver (Order XL) |
| 4 | commissioner | Appointment of commissioner (Order XXVI) |
| 5 | attachment_before_judgment | Attachment before judgment (Order XXXVIII) |
| 6 | security_for_costs | Security for costs |
| 7 | inherent_powers_s151 | S.151 CPC inherent powers application |

### E. EVIDENCE_AND_DISCOVERY (3 families)
| # | family | Description |
|---|--------|-------------|
| 1 | affidavit | Affidavit in evidence / support |
| 2 | chief_examination | Examination-in-chief affidavit (Order XVIII) |
| 3 | interrogatories | Interrogatories / discovery (Order XI) |

### F. JUDGMENT_AND_DECREE (4 families)
| # | family | Description |
|---|--------|-------------|
| 1 | compromise_decree | Compromise decree (Order XXIII Rule 3) |
| 2 | withdrawal_suit | Withdrawal of suit (Order XXIII Rule 1) |
| 3 | decree_support | Application in support of decree |
| 4 | certified_copy | Certified copy application |

### G. APPEAL_AND_REVIEW (7 families)
| # | family | Description |
|---|--------|-------------|
| 1 | first_appeal | First appeal (S.96 CPC) |
| 2 | second_appeal | Second appeal (S.100 CPC) |
| 3 | commercial_appeal | Commercial appeal (Commercial Courts Act) |
| 4 | stay_pending_appeal | Stay pending appeal |
| 5 | review | Review application (Order XLVII) |
| 6 | revision | Revision petition (S.115 CPC) |
| 7 | cross_objection | Cross-objection (Order XLI Rule 22) |

### H. EXECUTION (4 families)
| # | family | Description |
|---|--------|-------------|
| 1 | execution_petition | Execution petition (Order XXI) |
| 2 | objection_execution | Objection to execution (Order XXI Rule 58) |
| 3 | claim_execution | Claim petition (Order XXI Rule 58) |
| 4 | arrest_attachment | Arrest / attachment of person or property |

### I. RESTORATION (3 families)
| # | family | Description |
|---|--------|-------------|
| 1 | restore_suit | Restoration of suit for default |
| 2 | set_aside_ex_parte | Set aside ex parte decree (Order IX Rule 13) |
| 3 | set_aside_abatement | Set aside abatement (Order XXII Rule 9) |

### J. SPECIAL_INSTITUTION (2 families)
| # | family | Description |
|---|--------|-------------|
| 1 | agreed_case | Agreed case / case stated (Order XXXVI) |
| 2 | small_cause_suit | Small cause suit |

### K. EXPANDED_EXECUTION (4 families)
| # | family | Description |
|---|--------|-------------|
| 1 | transfer_precept | Transfer of decree / precept |
| 2 | delivery_possession | Delivery of possession (Order XXI Rule 35/36) |
| 3 | resistance_obstruction | Resistance / obstruction (Order XXI Rule 97) |
| 4 | reciprocal_s44a | S.44A reciprocal foreign decree |

### L. APPEAL_EXPANDED (2 families)
| # | family | Description |
|---|--------|-------------|
| 1 | indigent_appeal | Appeal as indigent person |
| 2 | appeal_from_order | Appeal from order (Order XLIII) |

---

## Classification Rules

1. **Every user request maps to exactly ONE cause_type (Axis 1) + ONE family (Axis 2)**
   - cause_type = WHAT the dispute is about (substantive law)
   - family = WHAT document to draft (procedural stage)

2. **Intake LLM must classify into specific sub-types, not parent groups**
   - WRONG: `recovery_of_possession` (ambiguous — tenant? licensee? trespasser?)
   - RIGHT: `recovery_of_possession_tenant` (flat, specific, one LKB entry)

3. **No conditional resolution needed** — each cause_type has exactly one set of:
   - primary_acts, alternative_acts, limitation, court_rules
   - damages_categories, permitted_doctrines, mandatory_averments
   - prayer_template, facts_must_cover, coa_guidance

4. **Alias map resolves LLM near-misses** — `_CAUSE_TYPE_ALIASES` in LKB `__init__.py`

5. **Group is metadata only** — used for reporting, not routing. Pipeline uses cause_type directly.

---

## Usage in Pipeline

```python
# Intake classifies into specific cause_type
cause_type = "recovery_of_possession_tenant"  # NOT "recovery_of_possession"

# LKB lookup returns flat entry — no conditional resolution needed
entry = lookup("Civil", cause_type)
# Returns: primary_acts, limitation, court_rules, etc. — all flat values

# Draft LLM gets clean, unambiguous data
lkb_brief = build_lkb_brief(entry)
```
