from app import settings
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
from openai import AzureOpenAI
import time
from datetime import datetime

# Initialize clients
# client = QdrantClient(url="http://localhost:6333")


client = QdrantClient(
    url=settings.QUADRANT_CLIENT_URL, 
    api_key=settings.QUADRANT_API_KEY,
)

api_key = settings.azure_openai_api_key.get_secret_value() if hasattr(settings.azure_openai_api_key, 'get_secret_value') else str(settings.azure_openai_api_key)
endpoint = settings.azure_openai_endpoint.get_secret_value() if hasattr(settings.azure_openai_endpoint, 'get_secret_value') else str(settings.azure_openai_endpoint)


azure_client = AzureOpenAI(
    api_key=api_key,
    api_version="2024-02-01",
    azure_endpoint=endpoint,
)

deployment_name = settings.azure_openai_deployment_name_embedding

# # Batch embedding function
def get_azure_embeddings_batch(texts):
    """Get embeddings for multiple texts in one API call"""
    response = azure_client.embeddings.create(
        input=texts,
        model=deployment_name
    )
    return [item.embedding for item in response.data]

# # Sample data
# payload =[
# {
#   "document": "This module introduces the foundations of alternative investing. It explains what alternatives are, why they matter today, and why both advisors and individuals now participate in private markets once reserved for institutions.",
#   "source": "What_Are_Alternatives",
#   "topic": "course_intro",
#   "intent": "introduce",
#   "level": "beginner"
# },
# {
#   "document": "In this lesson, alternatives include private equity, private credit, venture capital, private real estate, infrastructure and real assets, and secondaries or co-investments. These investments lie outside of publicly traded stocks and bonds.",
#   "source": "What_Are_Alternatives",
#   "topic": "types_of_alternative_investments",
#   "intent": "list_examples",
#   "level": "beginner"
# },

# {
#   "document": "Alternatives differ fundamentally from traditional public markets. They operate on longer time horizons, require different operational infrastructure, and depend on specialized managers to create value.",
#   "source": "What_Are_Alternatives",
#   "topic": "alternatives_vs_public_high_level",
#   "intent": "contrast",
#   "level": "beginner"
# },
# {
#   "document": "Understanding how alternatives differ from public markets is essential for navigating modern private markets. These differences affect liquidity, valuation, operations, and investor expectations.",
#   "source": "What_Are_Alternatives",
#   "topic": "importance_of_understanding_differences",
#   "intent": "explain_why",
#   "level": "beginner"
# },
# {
#   "document": "Alternatives are investments that lie outside publicly traded stocks and bonds. They are privately held and do not trade continuously on public exchanges.",
#   "source": "What_Are_Alternatives",
#   "topic": "alternatives_definition",
#   "intent": "define",
#   "level": "beginner"
# },
# {
#   "document": "Private equity involves acquiring and improving private companies. Returns are generated through operational improvements, strategic changes, and long-term ownership.",
#   "source": "What_Are_Alternatives",
#   "topic": "private_equity",
#   "intent": "explain_asset",
#   "level": "beginner"
# },
# {
#   "document": "Private credit focuses on lending directly to businesses and projects. Investors earn returns primarily through interest payments rather than ownership appreciation.",
#   "source": "What_Are_Alternatives",
#   "topic": "private_credit",
#   "intent": "explain_asset",
#   "level": "beginner"
# },
# {
#   "document": "Venture capital supports early-stage and high-growth companies. Returns depend on innovation success and long-term company scaling rather than near-term cash flow.",
#   "source": "What_Are_Alternatives",
#   "topic": "venture_capital",
#   "intent": "explain_asset",
#   "level": "beginner"
# },
# {
#   "document": "Private real estate includes income-producing properties and development projects. Value comes from rental income, asset appreciation, and active property management.",
#   "source": "What_Are_Alternatives",
#   "topic": "private_real_estate",
#   "intent": "explain_asset",
#   "level": "beginner"
# },
# {
#   "document": "Infrastructure and real assets include energy, transportation, logistics, and natural resources. These investments often provide long-duration cash flows tied to essential services.",
#   "source": "What_Are_Alternatives",
#   "topic": "infrastructure_real_assets",
#   "intent": "explain_asset",
#   "level": "beginner"
# },
# {
#   "document": "Secondaries and co-investments allow participation in existing private market deals. Investors gain exposure without committing capital at the fund's initial launch.",
#   "source": "What_Are_Alternatives",
#   "topic": "secondaries_coinvestments",
#   "intent": "explain_asset",
#   "level": "beginner"
# },
# {
#   "document": "Alternative investments are managed by a General Partner. The GP sources investments, oversees operations, and executes the fund's strategy.",
#   "source": "What_Are_Alternatives",
#   "topic": "general_partner_role",
#   "intent": "explain_role",
#   "level": "beginner"
# },
# {
#   "document": "Investors participate in alternative funds as Limited Partners. LPs provide capital and receive a share of performance without managing daily operations.",
#   "source": "What_Are_Alternatives",
#   "topic": "limited_partner_role",
#   "intent": "explain_role",
#   "level": "beginner"
# },
# {
#   "document": "Alternative investments are typically illiquid. Capital cannot be accessed on demand and is committed for extended periods of time.",
#   "source": "What_Are_Alternatives",
#   "topic": "illiquidity",
#   "intent": "explain_characteristic",
#   "level": "beginner"
# },
# {
#   "document": "Alternatives require longer holding periods than public investments. Investors must plan for multi-year commitments rather than short-term trading.",
#   "source": "What_Are_Alternatives",
#   "topic": "long_holding_periods",
#   "intent": "explain_characteristic",
#   "level": "beginner"
# },
# {
#   "document": "Alternatives may offer higher return potential compared to traditional assets. This potential compensates investors for illiquidity and complexity.",
#   "source": "What_Are_Alternatives",
#   "topic": "higher_return_potential",
#   "intent": "explain_characteristic",
#   "level": "beginner"
# },
# {
#   "document": "Returns in alternatives are often driven by active value creation. Specialized managers improve operations rather than relying on market price movements.",
#   "source": "What_Are_Alternatives",
#   "topic": "active_value_creation",
#   "intent": "explain_characteristic",
#   "level": "beginner"
# },
# {
#   "document": "Private markets are no longer limited to institutional investors. Growth is now driven by advisors, family offices, RIAs, and individual investors.",
#   "source": "What_Are_Alternatives",
#   "topic": "broader_access",
#   "intent": "explain_shift",
#   "level": "beginner"
# },
# {
#   "document": "Public market assets increasingly move together during stress periods. This correlation reduces diversification benefits in traditional portfolios.",
#   "source": "What_Are_Alternatives",
#   "topic": "public_market_correlation",
#   "intent": "explain_problem",
#   "level": "beginner"
# },
# {
#   "document": "Alternatives provide access to privately negotiated deals. These opportunities are not available through public exchanges.",
#   "source": "What_Are_Alternatives",
#   "topic": "private_deal_access",
#   "intent": "explain_benefit",
#   "level": "beginner"
# },
# {
#   "document": "Many alternative investments generate cash flows independent of public markets. These cash flows depend on contracts, lending terms, or asset operations.",
#   "source": "What_Are_Alternatives",
#   "topic": "independent_cash_flows",
#   "intent": "explain_benefit",
#   "level": "beginner"
# },
# {
#   "document": "Alternative returns are often tied to operational improvements. Performance depends more on execution than on macroeconomic movements.",
#   "source": "What_Are_Alternatives",
#   "topic": "operational_return_drivers",
#   "intent": "explain_benefit",
#   "level": "beginner"
# },
# {
#   "document": "Wealth advisors act as gatekeepers to private markets. They evaluate products, perform due diligence, assess fees, and educate clients.",
#   "source": "What_Are_Alternatives",
#   "topic": "advisor_gatekeeping",
#   "intent": "explain_role",
#   "level": "beginner"
# },
# {
#   "document": "Modern fund structures allow broader participation in private markets. These vehicles provide limited liquidity while maintaining private asset exposure.",
#   "source": "What_Are_Alternatives",
#   "topic": "modern_fund_structures",
#   "intent": "explain_structure",
#   "level": "beginner"
# },
# {
#   "document": "Interval funds offer periodic repurchase windows and require daily net asset value calculations. Liquidity is limited and scheduled rather than continuous.",
#   "source": "What_Are_Alternatives",
#   "topic": "interval_funds",
#   "intent": "explain_structure",
#   "level": "beginner"
# },
# {
#   "document": "Tender offer funds provide quarterly liquidity based on manager-supplied valuations. Investors may redeem only during specific offer periods.",
#   "source": "What_Are_Alternatives",
#   "topic": "tender_offer_funds",
#   "intent": "explain_structure",
#   "level": "beginner"
# },
# {
#   "document": "Evergreen funds allow continuous subscriptions and redemptions. Liquidity is governed by fund policies rather than market trading.",
#   "source": "What_Are_Alternatives",
#   "topic": "evergreen_funds",
#   "intent": "explain_structure",
#   "level": "beginner"
# },
# {
#   "document": "Private BDCs and retirement-only trusts are designed for income or retirement-focused investors. These structures align with specific distribution and regulatory needs.",
#   "source": "What_Are_Alternatives",
#   "topic": "bdcs_retirement_trusts",
#   "intent": "explain_structure",
#   "level": "beginner"
# },
# {
#   "document": "Expanded access places significant operational demands on managers and service providers. Systems must support liquidity, reporting, and compliance requirements.",
#   "source": "What_Are_Alternatives",
#   "topic": "operational_demands",
#   "intent": "explain_impact",
#   "level": "beginner"
# },
# {
#   "document": "Public markets offer real-time pricing, efficient settlement, immediate liquidity, automated tax reporting, and standardized data.",
#   "source": "What_Are_Alternatives",
#   "topic": "public_market_characteristics",
#   "intent": "describe",
#   "level": "beginner"
# },
# {
#   "document": "Private market assets are illiquid and cannot be priced continuously. Valuations rely on judgment, models, and professional review rather than live markets.",
#   "source": "What_Are_Alternatives",
#   "topic": "private_market_valuation_judgment",
#   "intent": "explain",
#   "level": "beginner"
# },
# {
#   "document": "Traditional private funds calculate net asset value quarterly. Valuations are reviewed by committees, appraisers, and administrators.",
#   "source": "What_Are_Alternatives",
#   "topic": "quarterly_nav",
#   "intent": "explain_process",
#   "level": "beginner"
# },
# {
#   "document": "Retail-accessible private funds may require daily NAV calculations. This introduces new operational and valuation challenges.",
#   "source": "What_Are_Alternatives",
#   "topic": "daily_nav_shift",
#   "intent": "explain_change",
#   "level": "beginner"
# },
# {
#   "document": "Retail-accessible private funds may require daily NAV calculations. This introduces new operational and valuation challenges.",
#   "source": "What_Are_Alternatives",
#   "topic": "daily_nav_shift",
#   "intent": "explain_change",
#   "level": "beginner"
# },
# {
#   "document": "Private market access requires continuous onboarding and suitability checks. These ensure investments align with investor risk and liquidity profiles.",
#   "source": "What_Are_Alternatives",
#   "topic": "onboarding_suitability",
#   "intent": "explain_requirement",
#   "level": "beginner"
# },
# {
#   "document": "Advisors and custodians require real-time position updates for private investments. This supports portfolio reporting and client visibility.",
#   "source": "What_Are_Alternatives",
#   "topic": "advisor_custodian_updates",
#   "intent": "explain_requirement",
#   "level": "beginner"
# },
# {
#   "document": "Daily pricing and liquidity require a mature technology stack. This includes valuation workflows, data integration, and liquidity management systems.",
#   "source": "What_Are_Alternatives",
#   "topic": "technology_stack",
#   "intent": "explain_requirement",
#   "level": "beginner"
# },
# {
#   "document": "In modern private funds, operational discipline is as important as investment performance. Errors in valuation or liquidity management create investor risk.",
#   "source": "What_Are_Alternatives",
#   "topic": "operational_discipline",
#   "intent": "emphasize",
#   "level": "beginner"
# },
# {
#   "document": "Regulatory developments are modernizing private markets. These changes support broader access while increasing compliance expectations.",
#   "source": "What_Are_Alternatives",
#   "topic": "regulatory_modernization",
#   "intent": "explain_trend",
#   "level": "beginner"
# },
# {
#   "document": "Tokenized fund interests digitally represent ownership in private funds. This enables fractional ownership and automated settlement processes.",
#   "source": "What_Are_Alternatives",
#   "topic": "tokenized_fund_interests",
#   "intent": "explain_concept",
#   "level": "beginner"
# },
# {
#   "document": "Digital financial rails support wallet-based onboarding and integrated KYC and AML checks. These tools streamline investor access to private funds.",
#   "source": "What_Are_Alternatives",
#   "topic": "digital_onboarding",
#   "intent": "explain_process",
#   "level": "beginner"
# },
# {
#   "document": "Digital fund representations may improve secondary liquidity over time. However, liquidity remains limited and structure-dependent.",
#   "source": "What_Are_Alternatives",
#   "topic": "secondary_liquidity_potential",
#   "intent": "explain_expectation",
#   "level": "beginner"
# },
# {
#   "document": "Investors increasingly expect frequent valuation updates and clear liquidity schedules. These expectations exceed traditional private fund reporting norms.",
#   "source": "What_Are_Alternatives",
#   "topic": "real_time_data_expectations",
#   "intent": "explain_expectation",
#   "level": "beginner"
# },
# {
#   "document": "Modern private funds are adopting API-first architectures and workflow automation. These systems support reporting, compliance, and data consolidation.",
#   "source": "What_Are_Alternatives",
#   "topic": "api_and_automation",
#   "intent": "explain_infrastructure",
#   "level": "beginner"
# },
# {
#   "document": "Greater access and transparency increase operational complexity. Fund managers must balance investor expectations with illiquid assets.",
#   "source": "What_Are_Alternatives",
#   "topic": "operational_complexity",
#   "intent": "highlight_tradeoff",
#   "level": "beginner"
# },
# {
#   "document": "Private markets are undergoing significant transformation. Advisors and individual investors now play a central role in this evolving ecosystem.",
#   "source": "What_Are_Alternatives",
#   "topic": "ecosystem_transformation",
#   "intent": "explain_context",
#   "level": "beginner"
# }
# ,{
#   "document": "Understanding alternatives requires knowledge of asset classes, fund structures, valuation timing, liquidity engineering, operations, and data infrastructure.",
#   "source": "What_Are_Alternatives",
#   "topic": "required_knowledge_areas",
#   "intent": "summarize",
#   "level": "beginner"
# }
# ,{
#   "document": "By the end of this course, learners will understand how alternatives function, why access is expanding, and what operational realities support modern private funds.",
#   "source": "What_Are_Alternatives",
#   "topic": "course_outcome",
#   "intent": "summarize",
#   "level": "beginner"
# }
# ]

# print(len(payload))







# ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,48]



# # Get embeddings
# start = time.time()
# doc_texts = [data["document"] for data in payload]
# doc_embeddings = get_azure_embeddings_batch(doc_texts)
# print(f"Embedding time: {time.time() - start:.2f}s")

# # Get actual embedding dimension from the first embedding
# embedding_size = len(doc_embeddings[0])
# print(f"Embedding dimension: {embedding_size}")

# # DELETE old collection and create new one with correct dimensions
# try:
#     client.delete_collection(collection_name="What_Are_Alternatives")
#     print("Deleted old collection")
# except Exception as e:
#     print(f"No existing collection to delete: {e}")

# # Create collection with CORRECT dimension
# client.create_collection(
#     collection_name="What_Are_Alternatives",
#     vectors_config=models.VectorParams(
#         size=embedding_size,  # This will be 1536 for text-embedding-3-small
#         distance=models.Distance.COSINE
#     )
# )
# print(f"Created collection with dimension {embedding_size}")

# # Upsert with batch
# points = [
#     PointStruct(id=id_val, vector=embedding, payload=data)
#     for id_val, embedding, data in zip(ids, doc_embeddings, payload)
# ]
# client.upsert(
#     collection_name="What_Are_Alternatives",
#     points=points,
#     wait=True
# )
# print("Uploaded documents")

start_time = datetime.now()
print("Start time:", start_time)

query_embedding = get_azure_embeddings_batch("How are alternatives different from the stocks and bonds I see every day?")[0]
search_result = client.query_points(
    collection_name="What_Are_Alternatives",
    query=query_embedding,
    limit=5
).points

# payload = search_result[0].payload
# print(payload)

print(search_result)

end_time = datetime.now()
print("End time:", end_time)

Total_Latency = end_time - start_time
print("Total_Latency:", Total_Latency)