"""LLM review orchestration for user facts."""

import json
import uuid


async def run_review(
    session_id: uuid.UUID,
    messages: list[dict],
    settings_obj,
    logger,
    anthropic_client_factory,
    resolve_client_kwargs,
    get_structured_model,
    has_api_key,
    extract_text,
    strip_code_fence,
    load_existing,
    apply_review_item,
    maybe_consolidate,
    review_prompt: str,
) -> None:
    """Run the background review agent and apply returned fact actions."""
    if not has_api_key(getattr(settings_obj, "anthropic_api_key", "")) and not has_api_key(
        getattr(settings_obj, "deepseek_api_key", ""),
    ):
        return

    try:
        logger.info("Background review started for session %s", session_id)

        existing = await load_existing()
        review_messages = [
            {
                "role": message["role"],
                "content": (
                    message["content"]
                    if isinstance(message["content"], str)
                    else str(message["content"])
                ),
            }
            for message in messages
        ]

        if existing:
            numbered = "\n".join(
                f"{index + 1}. {fact}" for index, (_, fact) in enumerate(existing)
            )
            facts_context = f"Known facts:\n{numbered}"
            review_messages.append({
                "role": "user",
                "content": f"{facts_context}\n\n{review_prompt}",
            })
        else:
            review_messages.append({"role": "user", "content": review_prompt})

        active_model = await get_structured_model()
        client = anthropic_client_factory(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
            max_tokens=8000,
            temperature=0.3,
            messages=review_messages,
        )

        raw_text = extract_text(response)
        cleaned = strip_code_fence(raw_text)
        items = json.loads(cleaned)

        if not isinstance(items, list) or not items:
            logger.info("Background review: no actions returned")
            return

        counts = {"saved": 0, "updated": 0, "duplicate": 0, "skipped": 0}
        for item in items:
            if not isinstance(item, dict):
                counts["skipped"] += 1
                continue
            outcome = await apply_review_item(item, existing, session_id)
            counts[outcome] = counts.get(outcome, 0) + 1

        logger.info(
            "Background review done for %s — added=%d updated=%d dup=%d skipped=%d",
            session_id,
            counts["saved"], counts["updated"], counts["duplicate"], counts["skipped"],
        )

        await maybe_consolidate(session_id)

    except json.JSONDecodeError as exc:
        logger.warning(
            "Background review: failed to parse JSON — %s | raw=%r",
            exc, raw_text[:400] if "raw_text" in locals() else "<no response>",
        )
    except Exception:
        logger.exception("Background review failed for session %s", session_id)
