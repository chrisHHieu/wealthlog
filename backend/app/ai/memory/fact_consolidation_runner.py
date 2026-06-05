"""LLM consolidation orchestration for user facts."""

import json
import uuid


async def maybe_consolidate(
    _session_id: uuid.UUID,
    settings_obj,
    logger,
    anthropic_client_factory,
    resolve_client_kwargs,
    get_structured_model,
    has_api_key,
    extract_text,
    strip_code_fence,
    count_active_facts,
    load_existing,
    apply_merge_item,
    consolidation_prompt: str,
) -> None:
    """Run the merge pass when active fact count exceeds the configured threshold."""
    if not has_api_key(getattr(settings_obj, "anthropic_api_key", "")) and not has_api_key(
        getattr(settings_obj, "deepseek_api_key", ""),
    ):
        return

    threshold = settings_obj.user_fact_consolidation_threshold
    before = await count_active_facts()
    if before <= threshold:
        return

    logger.info(
        "Consolidation triggered: %d active facts > threshold %d",
        before,
        threshold,
    )

    existing = await load_existing()
    numbered = "\n".join(
        f"{index + 1}. {fact}" for index, (_, fact) in enumerate(existing)
    )

    try:
        active_model = await get_structured_model()
        client = anthropic_client_factory(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
            max_tokens=8000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": f"Known facts:\n{numbered}\n\n{consolidation_prompt}",
            }],
        )
        raw_text = extract_text(response)
        items = json.loads(strip_code_fence(raw_text))
    except json.JSONDecodeError as exc:
        logger.warning(
            "Consolidation: failed to parse JSON — %s | raw=%r",
            exc,
            raw_text[:400] if "raw_text" in locals() else "<no response>",
        )
        return
    except Exception:
        logger.exception("Consolidation API call failed")
        return

    if not isinstance(items, list) or not items:
        logger.info("Consolidation: no merges proposed")
        return

    merged = removed = skipped = 0
    for item in items:
        merge_count, remove_count = await apply_merge_item(item, existing)
        merged += merge_count
        removed += remove_count
        if merge_count == 0 and remove_count == 0:
            skipped += 1

    after = await count_active_facts()
    logger.info(
        "Consolidation done: %d → %d facts (merged=%d removed=%d skipped=%d)",
        before,
        after,
        merged,
        removed,
        skipped,
    )
