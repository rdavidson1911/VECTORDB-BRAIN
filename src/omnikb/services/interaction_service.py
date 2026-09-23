"""Layer 2 interaction recording and score fusion helpers."""

from __future__ import annotations

from hashlib import sha256

from omnikb.adapters.interaction_store import InteractionStore, boost_norm
from omnikb.domain.memory_tier import boost_allowed, event_weight


class InteractionService:
    def __init__(self, store: InteractionStore) -> None:
        self.store = store

    @staticmethod
    def hash_query(text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()

    def record_events(
        self,
        *,
        session_id: str,
        events: list[dict[str, str | None]],
    ) -> int:
        accepted = 0
        for event in events:
            event_type = str(event.get("event_type") or "")
            point_id = str(event.get("point_id") or "")
            if not event_type or not point_id:
                continue
            memory_tier = str(event.get("memory_tier") or "default")
            apply = boost_allowed(memory_tier, event_type)
            weight = event_weight(event_type) if apply else 0.0
            self.store.record_event(
                session_id=session_id,
                event_type=event_type,
                point_id=point_id,
                query_text_hash=event.get("query_text_hash"),
                memory_tier=memory_tier,
                weight=weight,
                apply_boost=apply,
                ts=event.get("ts"),
            )
            accepted += 1
        return accepted

    def fuse_matches(
        self,
        matches: list[dict],
        *,
        boost_weight: float,
    ) -> tuple[list[dict], list[dict]]:
        """Return (layer1_matches, layer2_boosted_matches) with fused scores on L2."""
        layer1 = [dict(m) for m in matches]
        point_ids = [str(m.get("id", "")) for m in layer1 if m.get("id") is not None]
        boosts = self.store.get_boosts(point_ids)
        hit_max = self.store.max_hit_count()
        w = max(0.0, min(1.0, boost_weight))
        layer2: list[dict] = []
        for match in layer1:
            item = dict(match)
            payload = dict(item.get("payload") or {})
            point_id = str(item.get("id", ""))
            cosine = float(item.get("score", 0.0))
            boost = boosts.get(point_id)
            hit = boost.hit_count if boost else 0.0
            bn = boost_norm(hit, hit_max)
            fused = (1.0 - w) * cosine + w * bn
            item["score"] = fused
            item["cosine_score"] = cosine
            item["boost_norm"] = bn
            item["hit_count"] = hit
            payload["cosine_score"] = cosine
            payload["boost_norm"] = bn
            payload["hit_count"] = hit
            if boost:
                payload["memory_tier"] = boost.memory_tier
            item["payload"] = payload
            layer2.append(item)
        layer2.sort(key=lambda row: float(row.get("score", 0.0)), reverse=True)
        return layer1, layer2
