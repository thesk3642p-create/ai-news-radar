from app.models import CandidateItem, StoryEvent
from app.processing.normalize import canonical_url
from app.processing.scoring import score_event
from app.processing.stories import cluster, relevant
from app.collectors.x import XCollector


def test_canonical_url_removes_tracking_parameters():
    assert canonical_url("https://Example.com/news/?utm_source=x&b=2#part") == "https://example.com/news?b=2"


def test_relevance_matches_target_entity():
    item = CandidateItem(title="OpenAI releases a new GPT model", url="https://example.com/a", source_name="Test", source_tier="official", source_type="rss")
    assert relevant(item, ["benchmark"], ["OpenAI"])


def test_cluster_combines_similar_titles():
    first = CandidateItem(title="OpenAI launches GPT Next", url="https://example.com/one", source_name="OpenAI", source_tier="official", source_type="rss")
    second = CandidateItem(title="GPT Next launch announced by OpenAI", url="https://example.org/two", source_name="Outlet", source_tier="trusted", source_type="rss")
    events = cluster([first, second], [])
    assert len(events) == 1
    assert len(events[0].sources) == 2


def test_official_launch_scores_as_qualified_story():
    event = StoryEvent(id="test", headline="OpenAI launches new GPT reasoning model", summary="The new model improves AI coding benchmarks and is available through the API.", created_at="2026-08-09T00:00:00+00:00", last_seen_at="2026-08-09T00:00:00+00:00", sources=[{"source_name": "OpenAI", "source_tier": "official", "url": "https://example.com"}])
    scored = score_event(event, ["ai model", "reasoning model", "ai coding", "benchmark", "api"], ["OpenAI", "GPT"], [])
    assert scored.score >= 45
    assert scored.confidence >= 60


def test_x_collector_is_inert_until_explicitly_enabled():
    assert XCollector([], enabled=False).collect() == []
    assert XCollector([], enabled=False, max_post_age_hours=72).max_post_age_hours == 72
