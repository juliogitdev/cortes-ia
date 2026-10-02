from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

from clip_platform.services.store import Store
from clip_platform.shared.contracts import ClipRevision, MediaAsset
from clip_platform.shared.jobs import Export


def analysis():
    return json.loads((Path(__file__).resolve().parents[2] / "docs/contracts/v1/analysis_output.json").read_text(encoding="utf-8"))


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path)
    project = store.create_project("Teste")
    asset = MediaAsset.model_validate(analysis()["asset"])
    store.put_asset(project.project_id, asset)
    return store, project, asset


def test_roundtrip_and_restart(setup):
    store, project, asset = setup
    revision = ClipRevision(revision_id="revision_1", candidate_id="candidate_1", asset_id=asset.asset_id,
                            boundaries={"start_s":35,"end_s":65}, editor_changes=[])
    store.put_revision(revision)
    export = Export(export_id="export_1", revision_id=revision.revision_id, asset_id=asset.asset_id,
                    local_path="storage/export.mp4", duration_s=30, content_hash=asset.content_hash)
    store.put_export(export)
    reopened = Store(store.root)
    assert reopened.get_asset(asset.asset_id) == asset
    assert reopened.get_revision(revision.revision_id) == revision
    assert reopened.get_export(export.export_id) == export
    assert reopened.get_project(project.project_id).asset_id == asset.asset_id
    assert len(reopened.list_projects()) == 1


def test_idempotency_is_scoped_and_rejects_changed_payload(setup):
    store, project, _ = setup
    job = store.enqueue(project.project_id, "analysis", "action", {"a":1,"b":2})
    assert store.enqueue(project.project_id,"analysis","action", {"b":2,"a":1}) == job
    with pytest.raises(ValueError):
        store.enqueue(project.project_id,"analysis","action", {"a":2})


def test_two_workers_claim_only_one_job(setup):
    store, project, _ = setup
    store.enqueue(project.project_id,"analysis","one",{})
    store.enqueue(project.project_id,"analysis","two",{})
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda owner: Store(store.root).claim(owner), ["worker-a","worker-b"]))
    assert sum(item is not None for item in results) == 1


def test_concurrent_enqueue_consolidates_same_action(setup):
    store, project, _ = setup
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = list(executor.map(lambda _: Store(store.root).enqueue(project.project_id,"analysis","same",{"asset_id":"asset_sample"}), range(2)))
    assert jobs[0].job_id == jobs[1].job_id


def test_restarted_worker_reclaims_persisted_expired_job(setup):
    store, project, _ = setup
    store._clock = lambda:1000.0
    queued = store.enqueue(project.project_id,"analysis","action",{})
    store.claim("dead-process",10)
    restarted = Store(store.root)
    restarted._clock = lambda:1011.0
    assert restarted.claim("new-process",10).job_id == queued.job_id
    with pytest.raises(ValueError):
        restarted.set_stage(queued.job_id,"dead-process","stale-write")
    restarted._clock = lambda:1022.0
    with pytest.raises(ValueError):
        restarted.claim("dead-process",10)


def test_expiry_reclaim_and_fencing(setup):
    store, project, _ = setup
    now = [1000.0]
    store._clock = lambda: now[0]
    job = store.enqueue(project.project_id,"analysis","one",{})
    assert store.claim("old",10).attempts == 1
    store.set_stage(job.job_id,"old","transcribing")
    now[0] += 11
    for action in [lambda: store.heartbeat(job.job_id,"old"), lambda: store.set_stage(job.job_id,"old","done"), lambda: store.finish(job.job_id,"old",analysis())]:
        with pytest.raises(ValueError):
            action()
    with pytest.raises(ValueError):
        store.claim("old")
    reclaimed = store.claim("new",10)
    assert reclaimed.job_id == job.job_id
    assert reclaimed.stage == "transcribing"
    assert reclaimed.attempts == 2
    with pytest.raises(ValueError):
        store.fail(job.job_id,"old","stale")
    store.finish(job.job_id,"new",analysis())
    assert store.get_analysis(job.job_id).asset.asset_id == "asset_sample"


def test_heartbeat_extends_reservation(setup):
    store, project, _ = setup
    now = [1000.0]
    store._clock = lambda: now[0]
    job = store.enqueue(project.project_id,"analysis","one",{})
    store.claim("worker",10)
    now[0] += 8
    store.heartbeat(job.job_id,"worker",10)
    now[0] += 8
    assert store.claim("other") is None
    store.fail(job.job_id,"worker","explicit error")
    assert store.get_job(job.job_id).status == "failed"


def test_cancel_blocks_worker_and_allows_next(setup):
    store, project, _ = setup
    first = store.enqueue(project.project_id,"analysis","one",{})
    second = store.enqueue(project.project_id,"analysis","two",{})
    store.claim("worker")
    store.cancel(first.job_id)
    store.cancel(first.job_id)
    with pytest.raises(ValueError):
        store.finish(first.job_id,"worker",analysis())
    assert store.claim("next") is None
    with pytest.raises(ValueError):
        store.release(first.job_id,"stranger")
    store.release(first.job_id,"worker")
    store.release(first.job_id,"worker")
    assert store.claim("next").job_id == second.job_id


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_terminal_job_holds_resource_until_process_exit(setup, status):
    store, project, _ = setup
    first = store.enqueue(project.project_id,"analysis","one",{})
    second = store.enqueue(project.project_id,"analysis","two",{})
    store.claim("worker")
    with pytest.raises(ValueError):
        store.release(first.job_id,"worker")
    if status == "completed":
        store.finish(first.job_id,"worker",analysis())
    else:
        store.fail(first.job_id,"worker","error")
    assert store.claim("next") is None
    store.release(first.job_id,"worker")
    assert store.claim("next").job_id == second.job_id


def test_invalid_completion_does_not_change_job(setup):
    store, project, _ = setup
    job = store.enqueue(project.project_id,"analysis","one",{})
    store.claim("worker")
    invalid = analysis()
    invalid["candidates"][0]["evidence_ids"] = ["invented"]
    with pytest.raises(ValueError):
        store.finish(job.job_id,"worker",invalid)
    assert store.get_job(job.job_id).status == "running"


def test_missing_ids_and_invalid_revision(setup):
    store, _, asset = setup
    for getter in [store.get_project,store.get_asset,store.get_job,store.get_revision,store.get_export]:
        with pytest.raises(KeyError):
            getter("missing")
    with pytest.raises(ValueError):
        store.put_revision(ClipRevision(revision_id="r",candidate_id="c",asset_id=asset.asset_id,
                          boundaries={"start_s":100,"end_s":150},editor_changes=[]))


def test_export_job_completion_persists_export_atomically(setup):
    store, project, asset = setup
    revision = ClipRevision(revision_id="r",candidate_id="c",asset_id=asset.asset_id,
                            boundaries={"start_s":35,"end_s":65},editor_changes=[])
    store.put_revision(revision)
    job = store.enqueue(project.project_id,"export","export-action",{"revision_id":"r"})
    store.claim("worker")
    exported = Export(export_id="e",revision_id="r",asset_id=asset.asset_id,
                      local_path="storage/e.mp4",duration_s=30,content_hash=asset.content_hash)
    store.finish(job.job_id,"worker",exported.model_dump(mode="json"))
    assert store.get_export("e") == exported
    assert store.get_job(job.job_id).status == "completed"
    with pytest.raises(ValueError):
        store.cancel(job.job_id)
