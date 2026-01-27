"""
Graph node functions for broadcasting workflow

This module contains all node functions for the broadcasting pipeline:
- call_model_node: LLM orchestrator node
- data_processing_node: File parsing, phone validation, dedup, enrichment
- segmentation_node: Tag-based, behavioral, demographic, lifecycle, predictive
- content_creation_node: Template generation, personalization, A/B, media, CTA
- compliance_node: Spam rules, template policy, opt-out, content safety
- delivery_node: Sample rendering, admin test
- analytics_node: Metrics tracking, optimization recommendations
"""

from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.types import Command
from ...config import logger


# ============================================
# NODE: CALL MODEL (LLM Orchestrator)
# ============================================

async def call_model_node(
    state,
    config: RunnableConfig,
    system_prompt: str,
    tools: list,
    tool_names_set: set
):
    """
    Call the language model node for broadcasting workflow.

    This is the LLM orchestrator that:
    1. Takes state and dependencies as parameters
    2. Calls the model with system prompt + conversation history
    3. Routes to tool_node if backend tools are called, else END
    """
    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    logger.info(f"[BROADCASTING] Call model with {len(state['messages'])} messages, last 2:")
    for i, msg in enumerate(recent_messages):
        msg_type = type(msg).__name__
        content_preview = str(getattr(msg, 'content', ''))[:150]
        logger.info(f"  [{i}] {msg_type}: {content_preview}")

    system_message = SystemMessage(content=system_prompt)
    messages = [system_message] + state["messages"]

    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    logger.info(f"[BROADCASTING] CopilotKit actions count: {len(copilotkit_actions)}")

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    all_tools = [*copilotkit_actions, *tools]
    model_with_tools = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model_with_tools.ainvoke(messages, config)
        logger.info("[BROADCASTING] Model response received successfully")
    except Exception as e:
        logger.error(f"[BROADCASTING] Model invocation failed: {e}", exc_info=True)
        raise

    tool_calls = getattr(response, "tool_calls", None)
    has_backend_tool_calls = False

    if tool_calls:
        logger.info(f"[BROADCASTING] Tool calls made: {[tc.get('name') for tc in tool_calls]}")
        has_backend_tool_calls = any(
            tc.get("name") in tool_names_set
            for tc in tool_calls
        )

    if has_backend_tool_calls:
        logger.info("[BROADCASTING] Routing to tool_node (backend tools)")
        return Command(
            goto="tool_node",
            update={"messages": [response]},
        )
    else:
        logger.info("[BROADCASTING] Routing to END")
        return Command(
            goto=END,
            update={"messages": [response]},
        )


# ============================================
# NODE 1: DATA PROCESSING
# ============================================

async def data_processing_node(state, config: RunnableConfig):
    """
    Data Processing Node - Step 1 of broadcasting pipeline.

    Responsibilities:
    - File parsing (Excel/CSV/Google Sheets)
    - Phone validation & E.164 normalization
    - Duplicate detection & removal
    - Data enrichment (timezone, carrier, metadata)

    Returns:
        Command routing to segmentation_node with processed data summary.
    """
    logger.info("[BROADCASTING] === NODE 1: DATA PROCESSING ===")

    prompt = """You are the Data Processing specialist in a WhatsApp broadcasting pipeline.

Your job is to help the user with:
1. FILE PARSING: Accept and parse contact data from Excel/CSV/Google Sheets
2. PHONE VALIDATION: Validate all phone numbers and normalize to E.164 format (e.g., +919876543210)
3. DUPLICATE DETECTION: Identify and remove duplicate phone numbers
4. DATA ENRICHMENT: Add timezone, carrier, and metadata information

Process the user's data and provide a clear report:
- Total contacts found
- Valid contacts after cleanup
- Duplicates removed
- Invalid numbers filtered out
- Timezone distribution
- Carrier distribution

Ask the user to confirm the cleaned contact list before proceeding to segmentation.
Present the data summary in a clear, structured format.

IMPORTANT: After presenting results, call the display_segmentation_form frontend tool to show the Step 2 UI."""

    messages = [SystemMessage(content=prompt)] + state["messages"]

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    all_tools = [*copilotkit_actions]
    if all_tools:
        model = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model.ainvoke(messages, config)
        logger.info("[BROADCASTING] Data processing node completed")
    except Exception as e:
        logger.error(f"[BROADCASTING] Data processing failed: {e}", exc_info=True)
        raise

    return Command(
        goto="segmentation_node",
        update={"messages": [response]},
    )


# ============================================
# NODE 2: SEGMENTATION & TARGETING
# ============================================

async def segmentation_node(state, config: RunnableConfig):
    """
    Segmentation & Targeting Node - Step 2 of broadcasting pipeline.

    Responsibilities:
    - Tag-based filtering (user + system tags)
    - Behavioral segmentation (engagement patterns)
    - Demographic segmentation (location, language)
    - Lifecycle stage analysis (new/engaged/at-risk)
    - Predictive segmentation (ML-powered)

    Returns:
        Command routing to content_creation_node with segment definitions.
    """
    logger.info("[BROADCASTING] === NODE 2: SEGMENTATION & TARGETING ===")

    prompt = """You are the Segmentation & Targeting specialist in a WhatsApp broadcasting pipeline.

Your job is to analyze the contact list and help the user create targeted segments:

1. TAG-BASED FILTERING:
   - Filter by user-defined tags and system tags
   - Support include/exclude tag logic

2. BEHAVIORAL SEGMENTATION:
   - Group by engagement patterns (active, moderate, dormant)
   - Consider message open rates, reply rates, click-through rates

3. DEMOGRAPHIC SEGMENTATION:
   - Group by location (city, state, country)
   - Group by language preference

4. LIFECYCLE STAGE ANALYSIS:
   - New subscribers (< 30 days)
   - Engaged users (regular interactions)
   - At-risk users (declining engagement)
   - Dormant users (no recent activity)

5. PREDICTIVE SEGMENTATION:
   - Predict best time to send based on past engagement
   - Identify high-value contacts likely to convert

Present segment options to the user. Let them select or customize segments.
Show estimated audience size for each segment.
Confirm the target audience before proceeding to content creation.

IMPORTANT: After confirming segments, call the display_content_creation_form frontend tool to show the Step 3 UI."""

    messages = [SystemMessage(content=prompt)] + state["messages"]

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    all_tools = [*copilotkit_actions]
    if all_tools:
        model = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model.ainvoke(messages, config)
        logger.info("[BROADCASTING] Segmentation node completed")
    except Exception as e:
        logger.error(f"[BROADCASTING] Segmentation failed: {e}", exc_info=True)
        raise

    return Command(
        goto="content_creation_node",
        update={"messages": [response]},
    )


# ============================================
# NODE 3: CONTENT CREATION
# ============================================

async def content_creation_node(state, config: RunnableConfig):
    """
    Content Creation Node - Step 3 of broadcasting pipeline.

    Responsibilities:
    - Template generation (campaign-type specific)
    - Variable personalization ({{name}}, {{product}})
    - A/B variant creation
    - Media generation/optimization (images/videos)
    - CTA button configuration

    Returns:
        Command routing to compliance_node with created content.
    """
    logger.info("[BROADCASTING] === NODE 3: CONTENT CREATION ===")

    prompt = """You are the Content Creation specialist in a WhatsApp broadcasting pipeline.

Your job is to help the user create broadcast message content:

1. TEMPLATE GENERATION:
   - Generate WhatsApp message templates based on campaign type
   - Support types: promotional, transactional, informational, re-engagement
   - Include header (text/image/video/document), body, footer sections

2. VARIABLE PERSONALIZATION:
   - Support dynamic variables: {{name}}, {{product}}, {{order_id}}, {{company}}, etc.
   - Map variables to contact data fields
   - Show preview with sample data

3. A/B VARIANT CREATION:
   - Create 2-3 variants of the message for A/B testing
   - Vary subject lines, CTAs, or body text
   - Define split percentages (e.g., 50/50 or 33/33/34)

4. MEDIA GENERATION/OPTIMIZATION:
   - Generate image/video/banner for the message
   - Resize for WhatsApp channel requirements
   - Optimize file size for fast delivery

5. CTA BUTTON CONFIGURATION:
   - Add Quick Reply buttons (up to 3)
   - Add URL buttons (up to 2)
   - Add Call-to-Action phone number button
   - Configure button text and actions

Show a complete preview of the message(s) to the user.
Get explicit approval on the content before proceeding to compliance checks.

IMPORTANT: After getting approval, call the display_compliance_form frontend tool to show the Step 4 UI."""

    messages = [SystemMessage(content=prompt)] + state["messages"]

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    all_tools = [*copilotkit_actions]
    if all_tools:
        model = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model.ainvoke(messages, config)
        logger.info("[BROADCASTING] Content creation node completed")
    except Exception as e:
        logger.error(f"[BROADCASTING] Content creation failed: {e}", exc_info=True)
        raise

    return Command(
        goto="compliance_node",
        update={"messages": [response]},
    )


# ============================================
# NODE 4: COMPLIANCE & POLICY
# ============================================

async def compliance_node(state, config: RunnableConfig):
    """
    Compliance & Policy Node - Step 4 of broadcasting pipeline.

    Responsibilities:
    - Check spam rules
    - Verify WhatsApp template policy compliance
    - Add opt-out text
    - Block unsafe content

    Returns:
        Command routing to delivery_node after compliance passes.
    """
    logger.info("[BROADCASTING] === NODE 4: COMPLIANCE & POLICY ===")

    prompt = """You are the Compliance & Policy specialist in a WhatsApp broadcasting pipeline.

Your job is to run compliance checks on the broadcast content:

1. SPAM RULES CHECK:
   - Verify message frequency limits (no more than X messages per day per user)
   - Check for spam trigger words or patterns
   - Ensure message is not bulk unsolicited content
   - Verify sender reputation score

2. WHATSAPP TEMPLATE POLICY:
   - Verify template follows WhatsApp Business API guidelines
   - Check character limits (header: 60, body: 1024, footer: 60)
   - Validate button configurations (max 3 quick replies, 2 URL buttons)
   - Ensure no prohibited content (gambling, adult, alcohol, etc.)
   - Verify template category matches content

3. OPT-OUT TEXT:
   - Ensure opt-out/unsubscribe option is included
   - Validate opt-out mechanism works (e.g., "Reply STOP to unsubscribe")
   - Check opt-out text is visible and clear

4. CONTENT SAFETY:
   - Block unsafe or prohibited content
   - Check for misleading claims
   - Verify no personal data leaks in template variables
   - Ensure media content is appropriate

Present a compliance report:
- ✅ Passed checks
- ⚠️ Warnings (non-blocking)
- ❌ Failed checks (must fix before sending)

If issues are found, suggest specific fixes.
Get user confirmation after all checks pass before proceeding to delivery.

IMPORTANT: After compliance passes, call the display_delivery_form frontend tool to show the Step 5 UI."""

    messages = [SystemMessage(content=prompt)] + state["messages"]

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    all_tools = [*copilotkit_actions]
    if all_tools:
        model = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model.ainvoke(messages, config)
        logger.info("[BROADCASTING] Compliance node completed")
    except Exception as e:
        logger.error(f"[BROADCASTING] Compliance check failed: {e}", exc_info=True)
        raise

    return Command(
        goto="delivery_node",
        update={"messages": [response]},
    )


# ============================================
# NODE 5: DELIVERY ORCHESTRATION
# ============================================

async def delivery_node(state, config: RunnableConfig):
    """
    Delivery Orchestration Node - Step 5 of broadcasting pipeline.

    Responsibilities:
    - Render sample messages with real data
    - Test on admin number
    - Execute broadcast delivery

    Returns:
        Command routing to analytics_node after delivery.
    """
    logger.info("[BROADCASTING] === NODE 5: DELIVERY ORCHESTRATION ===")

    prompt = """You are the Delivery Orchestration specialist in a WhatsApp broadcasting pipeline.

Your job is to manage the broadcast delivery process:

1. RENDER SAMPLE MESSAGES:
   - Take the approved template and render it with real contact data
   - Show 3-5 sample rendered messages to the user
   - Highlight personalized variables in the preview
   - Verify all variables are properly populated

2. TEST ON ADMIN NUMBER:
   - Send a test message to the admin/user's own WhatsApp number
   - Wait for confirmation that the test message looks correct
   - Allow the user to make last-minute adjustments

3. DELIVERY EXECUTION:
   - Ask for final confirmation: "Ready to send to X contacts?"
   - Execute the broadcast in batches to respect rate limits
   - Handle delivery scheduling (immediate or scheduled)
   - Support timezone-aware delivery (send at optimal local time)
   - Report delivery progress:
     * Messages queued
     * Messages sent
     * Messages delivered
     * Messages failed
   - Handle retries for failed deliveries

Present the delivery summary and ask for final go/no-go confirmation.
After delivery, route to analytics for tracking.

IMPORTANT: After delivery completes, call the display_analytics_view frontend tool to show the Step 6 UI."""

    messages = [SystemMessage(content=prompt)] + state["messages"]

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    all_tools = [*copilotkit_actions]
    if all_tools:
        model = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model.ainvoke(messages, config)
        logger.info("[BROADCASTING] Delivery node completed")
    except Exception as e:
        logger.error(f"[BROADCASTING] Delivery failed: {e}", exc_info=True)
        raise

    return Command(
        goto="analytics_node",
        update={"messages": [response]},
    )


# ============================================
# NODE 6: ANALYTICS & OPTIMIZATION
# ============================================

async def analytics_node(state, config: RunnableConfig):
    """
    Analytics & Optimization Node - Step 6 (final) of broadcasting pipeline.

    Responsibilities:
    - Track delivery metrics (sent, delivered, read, failed)
    - Monitor engagement (clicks, replies)
    - Provide optimization recommendations

    Returns:
        Command routing to END.
    """
    logger.info("[BROADCASTING] === NODE 6: ANALYTICS & OPTIMIZATION ===")

    prompt = """You are the Analytics & Optimization specialist in a WhatsApp broadcasting pipeline.

Your job is to analyze broadcast performance and provide insights:

1. DELIVERY METRICS:
   - Total messages sent
   - Delivery rate (delivered / sent)
   - Read rate (read / delivered)
   - Failed messages and reasons
   - Bounce rate

2. ENGAGEMENT METRICS:
   - Click-through rate (CTR) on URL buttons
   - Reply rate
   - Quick reply button usage
   - Opt-out rate
   - Conversion rate (if tracking enabled)

3. A/B TEST RESULTS (if applicable):
   - Compare variant performance
   - Statistical significance analysis
   - Winning variant recommendation

4. OPTIMIZATION RECOMMENDATIONS:
   - Best performing time slots
   - Best performing segments
   - Content improvement suggestions
   - Audience refinement ideas
   - Recommended send frequency

Present a comprehensive analytics dashboard:
📊 **Broadcast Performance Report**
- Summary metrics with visual indicators
- Segment-level breakdown
- Time-based delivery heatmap
- Recommendations for next broadcast

This is the final step of the broadcasting pipeline.
Congratulate the user on completing the broadcast and offer to help with the next one.

IMPORTANT: After presenting analytics, call the display_campaign_complete frontend tool to show the completion UI."""

    messages = [SystemMessage(content=prompt)] + state["messages"]

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    all_tools = [*copilotkit_actions]
    if all_tools:
        model = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model.ainvoke(messages, config)
        logger.info("[BROADCASTING] Analytics node completed")
    except Exception as e:
        logger.error(f"[BROADCASTING] Analytics failed: {e}", exc_info=True)
        raise

    return Command(
        goto=END,
        update={"messages": [response]},
    )


# ============================================
# EXPORTS
# ============================================

__all__ = [
    "call_model_node",
    "data_processing_node",
    "segmentation_node",
    "content_creation_node",
    "compliance_node",
    "delivery_node",
    "analytics_node",
]
