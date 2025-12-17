"""
Third-Party Reputation System

Query and aggregate reputation scores from trusted Qubes.
From docs/08_P2P_Network_Discovery.md Section 5.4
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import asyncio

from core.exceptions import NetworkError
from utils.logging import get_logger

logger = get_logger(__name__)


class ReputationQuery:
    """
    Third-party reputation aggregation system

    Queries multiple trusted Qubes for their opinion about a target Qube,
    then aggregates scores to form a consensus view.
    """

    def __init__(self, qube):
        """
        Initialize reputation query system

        Args:
            qube: Qube instance for accessing relationships and messaging
        """
        self.qube = qube
        self.reputation_cache: Dict[str, Tuple[float, int]] = {}  # qube_id -> (score, timestamp)
        self.cache_ttl = 3600  # 1 hour cache

    async def query_reputation(
        self,
        target_qube_id: str,
        trusted_sources: Optional[List[str]] = None,
        min_responses: int = 3
    ) -> Dict[str, any]:
        """
        Query third-party reputation for a target Qube

        Asks trusted Qubes: "What do you think about target_qube_id?"
        Aggregates responses into a consensus score.

        From docs Section 5.4 - Third-party reputation queries

        Args:
            target_qube_id: Qube ID to query about
            trusted_sources: List of Qube IDs to ask (None = use high-trust relationships)
            min_responses: Minimum responses required for valid result

        Returns:
            {
                "target_qube_id": str,
                "overall_reputation": float,  # 0-100 consensus score
                "response_count": int,
                "scores": [{"source": str, "score": float, "relationship": str}, ...],
                "confidence": float,  # Based on response count and variance
                "cached": bool,
                "timestamp": int
            }
        """
        # Check cache first
        if target_qube_id in self.reputation_cache:
            cached_score, cached_time = self.reputation_cache[target_qube_id]
            age = int(datetime.now(timezone.utc).timestamp()) - cached_time

            if age < self.cache_ttl:
                logger.debug(
                    "reputation_cache_hit",
                    target=target_qube_id,
                    age_seconds=age
                )
                return {
                    "target_qube_id": target_qube_id,
                    "overall_reputation": cached_score,
                    "response_count": 0,
                    "scores": [],
                    "confidence": 0.8,  # Slightly lower confidence for cached
                    "cached": True,
                    "timestamp": cached_time
                }

        # Determine who to ask
        if trusted_sources is None:
            trusted_sources = self._get_trusted_sources()

        if len(trusted_sources) == 0:
            logger.warning(
                "no_trusted_sources",
                target=target_qube_id,
                message="No trusted Qubes to query for reputation"
            )
            return self._default_reputation_response(target_qube_id)

        logger.info(
            "querying_third_party_reputation",
            target=target_qube_id,
            sources=len(trusted_sources)
        )

        # Query all trusted sources in parallel
        query_tasks = [
            self._query_single_source(source_id, target_qube_id)
            for source_id in trusted_sources[:10]  # Limit to top 10
        ]

        responses = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Filter out errors and None responses
        valid_responses = [
            r for r in responses
            if r is not None and not isinstance(r, Exception)
        ]

        if len(valid_responses) < min_responses:
            logger.warning(
                "insufficient_reputation_responses",
                target=target_qube_id,
                responses=len(valid_responses),
                required=min_responses
            )
            return self._default_reputation_response(target_qube_id)

        # Aggregate scores
        result = self._aggregate_scores(target_qube_id, valid_responses)

        # Cache result
        self.reputation_cache[target_qube_id] = (
            result["overall_reputation"],
            result["timestamp"]
        )

        logger.info(
            "reputation_query_complete",
            target=target_qube_id,
            score=result["overall_reputation"],
            responses=result["response_count"],
            confidence=result["confidence"]
        )

        return result

    async def _query_single_source(
        self,
        source_qube_id: str,
        target_qube_id: str
    ) -> Optional[Dict[str, any]]:
        """
        Query a single Qube for their opinion about target

        Args:
            source_qube_id: Who to ask
            target_qube_id: Who to ask about

        Returns:
            {"source": str, "score": float, "relationship": str} or None
        """
        try:
            # Note: This will be fully implemented once Phase 5 relationships are complete
            # For now, we'll check if we have a relationship record

            # Try to get relationship from qube (Phase 5 integration point)
            try:
                relationship = self.qube.get_relationship(source_qube_id)
                if not relationship:
                    return None

                # Get their opinion about target from relationship data
                third_party_rep = relationship.get("third_party_reputation", {})
                if target_qube_id in third_party_rep:
                    opinion = third_party_rep[target_qube_id]
                    return {
                        "source": source_qube_id,
                        "score": opinion.get("trust_score", 50),
                        "relationship": opinion.get("relationship", "unknown")
                    }

            except AttributeError:
                # Qube.get_relationship() doesn't exist yet (Phase 5)
                logger.debug(
                    "relationships_not_implemented",
                    message="Phase 5 relationships not yet implemented"
                )
                pass

            # Fallback: Query via P2P message (if messenger available)
            if hasattr(self.qube, 'messenger') and self.qube.messenger:
                # Send reputation query message
                response = await self.qube.messenger.send_message(
                    recipient_qube_id=source_qube_id,
                    message_type="reputation_query",
                    content={
                        "target_qube_id": target_qube_id,
                        "query_type": "trust_score"
                    },
                    timeout=5.0  # 5 second timeout
                )

                if response and "trust_score" in response:
                    return {
                        "source": source_qube_id,
                        "score": response["trust_score"],
                        "relationship": response.get("relationship", "unknown")
                    }

            return None

        except Exception as e:
            logger.error(
                "reputation_query_failed",
                source=source_qube_id,
                target=target_qube_id,
                error=str(e)
            )
            return None

    def _get_trusted_sources(self) -> List[str]:
        """
        Get list of trusted Qubes to query for reputation

        Uses high-trust relationships from Phase 5 (when available)

        Returns:
            List of Qube IDs with trust >= 70
        """
        trusted = []

        try:
            # Try to get relationships from qube (Phase 5)
            if hasattr(self.qube, 'get_all_relationships'):
                relationships = self.qube.get_all_relationships()

                for rel in relationships:
                    trust_score = rel.get("overall_trust_score", 0)
                    if trust_score >= 70:  # High trust threshold
                        trusted.append(rel["entity_id"])

        except AttributeError:
            logger.debug("relationships_not_available", message="Phase 5 not implemented yet")

        # Fallback: Use known peers from P2P network
        if len(trusted) == 0 and hasattr(self.qube, 'p2p_node'):
            if self.qube.p2p_node and self.qube.p2p_node.known_peers:
                # Use any known peers as sources
                trusted = list(self.qube.p2p_node.known_peers.keys())[:10]

        return trusted

    def _aggregate_scores(
        self,
        target_qube_id: str,
        responses: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Aggregate reputation scores from multiple sources

        Uses weighted average based on our trust in each source.

        Args:
            target_qube_id: Target Qube ID
            responses: List of response dicts with source, score, relationship

        Returns:
            Aggregated reputation dict
        """
        if not responses:
            return self._default_reputation_response(target_qube_id)

        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0

        for response in responses:
            source_id = response["source"]
            score = response["score"]

            # Weight by our trust in the source (Phase 5 integration)
            weight = self._get_source_weight(source_id)

            weighted_sum += score * weight
            total_weight += weight

        overall_score = weighted_sum / total_weight if total_weight > 0 else 50.0

        # Calculate confidence based on response count and variance
        variance = self._calculate_variance([r["score"] for r in responses])
        confidence = min(0.95, (len(responses) / 10.0) * (1.0 - (variance / 100.0)))

        return {
            "target_qube_id": target_qube_id,
            "overall_reputation": round(overall_score, 2),
            "response_count": len(responses),
            "scores": responses,
            "confidence": round(confidence, 2),
            "cached": False,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }

    def _get_source_weight(self, source_qube_id: str) -> float:
        """
        Get weight for a reputation source based on our trust in them

        Args:
            source_qube_id: Source Qube ID

        Returns:
            Weight multiplier (0.5 to 1.5)
        """
        try:
            if hasattr(self.qube, 'get_relationship'):
                relationship = self.qube.get_relationship(source_qube_id)
                if relationship:
                    trust = relationship.get("overall_trust_score", 50)
                    # Map 0-100 trust to 0.5-1.5 weight
                    return 0.5 + (trust / 100.0)

        except AttributeError:
            pass

        return 1.0  # Default weight

    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate variance of scores (0-100 range)"""
        if len(scores) < 2:
            return 0.0

        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return variance

    def _default_reputation_response(self, target_qube_id: str) -> Dict[str, any]:
        """Return default neutral reputation when queries fail"""
        return {
            "target_qube_id": target_qube_id,
            "overall_reputation": 50.0,  # Neutral score
            "response_count": 0,
            "scores": [],
            "confidence": 0.0,
            "cached": False,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }

    def clear_cache(self, qube_id: Optional[str] = None) -> None:
        """
        Clear reputation cache

        Args:
            qube_id: Specific Qube to clear (None = clear all)
        """
        if qube_id:
            if qube_id in self.reputation_cache:
                del self.reputation_cache[qube_id]
                logger.debug("reputation_cache_cleared", qube_id=qube_id)
        else:
            self.reputation_cache.clear()
            logger.debug("reputation_cache_cleared_all")
