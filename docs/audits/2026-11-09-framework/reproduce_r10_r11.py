"""Isolated audit reproductions; copy temporarily under tests/integration/server to run.

No fixes. Real project persistence and handlers; controlled scheduling, local fake
media/duration/ASR and a cost-compute stub where noted. No provider requests.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from pathlib import Path

import pytest

from lib.infra.async_thread import run_sync_transaction
from lib.speech.audio_review import AudioReviewUnavailable
from server.media_tools import speech_review, workflow_access
from server.tool_runtime import CallerContext, NoArguments, ProjectScope, Services, ToolRequest
from tests.integration.server.test_workflow_access import access, png
from tests.integration.server.services.presentation.test_presentation_read_model import (
    _SettingsResolver, _setup_narrator_project,
)
from server.services.presentation.presentation_read_model import PresentationReadModelService


def install_script(pm, *, reference=True, legacy=True):
    path = pm.get_project_path('demo') / 'scripts/episode_1.json'
    script = {'episode': 1, 'content_mode': 'drama', 'title': 'Cena brasileira'}
    if reference:
        unit = {'unit_id': 'E1U01', 'duration_seconds': 8, 'references': [],
                'shots': [{'text': 'Olá, Ana!', **({'duration': 8} if legacy else {})}]}
        if legacy:
            unit['duration_override'] = False
        script['video_units'] = [unit]
    else:
        script['scenes'] = []
    path.write_text(json.dumps(script, ensure_ascii=False), encoding='utf-8')
    pm.update_project('demo', lambda p: p.update({
        'generation_mode': 'reference_video' if reference else 'storyboard',
        'source_language': 'pt-BR',
        'episodes': [{'episode': 1, 'title': 'Cena', 'script_file': 'scripts/episode_1.json'}],
    }))
    return path


async def no_cost_compute(self, *args, **kwargs):
    return {'audit': 'cost computation stubbed after real script reads'}


@pytest.mark.parametrize('legacy', [True, False])
@pytest.mark.parametrize('stub_cost_compute', [False, True])
async def test_r10_cost_read_persistence(access, monkeypatch, legacy, stub_cost_compute):
    pm, call = access
    path = install_script(pm, legacy=legacy)
    before = path.read_bytes()
    project_before = (pm.get_project_path('demo') / 'project.json').read_bytes()
    if stub_cost_compute:
        monkeypatch.setattr(workflow_access.CostEstimationService, 'compute', no_cost_compute)
    result = await call('get_project_costs')
    assert result.problem is None
    assert (path.read_bytes() != before) == legacy
    assert (pm.get_project_path('demo') / 'project.json').read_bytes() == project_before
    data = json.loads(path.read_bytes())
    assert data['video_units'][0]['duration_seconds'] == 8
    assert data['video_units'][0]['shots'][0]['text'] == 'Olá, Ana!'
    assert 'duration_override' not in data['video_units'][0]
    print('R10 cost:', {'legacy': legacy, 'stub_cost_compute': stub_cost_compute, 'script_changed': path.read_bytes() != before, 'ptBR_preserved': True})


@pytest.mark.parametrize('transaction_control', [False, True])
async def test_r10_cancelled_cost_reader(access, monkeypatch, transaction_control):
    pm, call = access
    path = install_script(pm)
    before = path.read_bytes()
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    real_persist = pm._persist_script_json

    def paused_persist(*args, **kwargs):
        entered.set()
        assert release.wait(5), 'audit release timeout'
        try:
            return real_persist(*args, **kwargs)
        finally:
            completed.set()

    monkeypatch.setattr(pm, '_persist_script_json', paused_persist)
    monkeypatch.setattr(workflow_access.CostEstimationService, 'compute', no_cost_compute)
    # Control uses the native transaction wrapper over the same real writing reader.
    task = asyncio.create_task(
        run_sync_transaction(pm.load_script, 'demo', 'episode_1.json')
        if transaction_control else call('get_project_costs')
    )
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        for _ in range(10):
            await asyncio.sleep(0)
        if transaction_control:
            assert not task.done()
        else:
            with pytest.raises(asyncio.CancelledError):
                await task
            assert task.done() and not completed.is_set()
            assert path.read_bytes() == before
        release.set()
        assert await asyncio.to_thread(completed.wait, 5)
        if transaction_control:
            with pytest.raises(asyncio.CancelledError):
                await task
        assert path.read_bytes() != before
        print('R10 cancellation:', {'native_transaction_control': transaction_control,
              'write_completed_after_caller_cancelled': not transaction_control})
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize('mode', ['reference_video', 'storyboard'])
async def test_r10_storyboard_quote_route_qualification(access, mode):
    pm, call = access
    path = install_script(pm)
    pm.update_project('demo', lambda p: p.update({'generation_mode': mode}))
    before = path.read_bytes()
    result = await call('quote_storyboards', episode_id=1)
    assert result.problem is not None
    # Valid reference route rejects before reading. Mismatched storyboard/ref skeleton
    # reads/migrates first and only then rejects the incompatible skeleton.
    assert (path.read_bytes() != before) == (mode == 'storyboard')
    print('R10 storyboard quote:', {'mode': mode, 'rejected': True, 'script_changed': path.read_bytes() != before})


async def test_r10_storyboard_preview_migrates_before_return(access):
    from server.media_tools import image_edits
    from tests.integration.server.agent_tool_support import fake_caps_resolver
    pm, _ = access
    path = install_script(pm)
    before = path.read_bytes()
    services = Services(projects=pm, workflow_planner=None, capabilities=fake_caps_resolver(), queue=None)
    # A missing target must not submit; the real loader still adopts legacy duration fields.
    result = await image_edits.edit_images(
        ToolRequest(image_edits.EditImagesRequest(resource_type='storyboard', script_file='episode_1.json',
                    edits=[{'id': 'E1U01', 'instruction': 'Preserve the spoken Portuguese'}], preview=True)),
        ProjectScope('demo', pm.data_root), CallerContext('test', 'mcp'), services)
    assert path.read_bytes() != before
    assert (pm.get_project_path('demo') / 'project.json').exists()
    print('R10 edit preview:', {'script_changed': True, 'problem': result.problem.code if result.problem else None})


def snapshot(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file() and p.suffix in {'.json', '.srt', '.mp4', '.wav'}}


@pytest.mark.parametrize('asr_available', [False, True])
async def test_r10_speech_inspection_materializes_before_asr(tmp_path, monkeypatch, asr_available):
    pm, path, settings = _setup_narrator_project(tmp_path)
    async def probe(_path):
        return 6.25
    reader = PresentationReadModelService(pm, settings_resolver_factory=lambda *_: _SettingsResolver(settings), duration_probe=probe)
    monkeypatch.setattr(speech_review, 'PresentationReadModelService', lambda _: reader)
    def transcribe(_path, *, language):
        if not asr_available:
            raise AudioReviewUnavailable('isolated audit: no local ASR configured')
        return {'words': [{'text': '一', 'start': .1, 'end': .5, 'probability': .99},
                          {'text': '二二', 'start': .6, 'end': 1, 'probability': .99}]}
    monkeypatch.setattr(speech_review, 'transcribe_media', transcribe)
    before = snapshot(path)
    result = await speech_review.review_speech(
        ToolRequest(speech_review.ReviewSpeechRequest(unit_id='E1S01', language='zh', variant='use_tts', apply_timing=False)),
        ProjectScope('demo', pm.data_root), CallerContext('test', 'mcp'),
        Services(projects=pm, workflow_planner=None, capabilities=None, queue=None))
    after = snapshot(path)
    new = sorted(after.keys() - before.keys())
    changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
    assert any(k.startswith('presentations/') for k in new)
    assert any(k.startswith('subtitles/') for k in new)
    assert all(before[k] == after[k] for k in before if k.endswith(('.mp4', '.wav')) or k.startswith('scripts/'))
    assert not list((path/'speech_reviews').glob('*.json'))
    if asr_available:
        assert result.problem is None and result.value['applied'] is False
    else:
        assert result.problem.code == 'speech_review_unavailable'
    stable = snapshot(path)
    await speech_review.review_speech(
        ToolRequest(speech_review.ReviewSpeechRequest(unit_id='E1S01', language='zh', variant='use_tts', apply_timing=False)),
        ProjectScope('demo', pm.data_root), CallerContext('test', 'mcp'),
        Services(projects=pm, workflow_planner=None, capabilities=None, queue=None))
    assert snapshot(path) == stable
    print('R10 speech:', {'ASR_available': asr_available, 'created': new, 'changed': changed,
                          'second_call_content_stable': True, 'measured_timing_applied': False})


@pytest.mark.parametrize('delete_during_upload', [False, True])
async def test_r11_upload_with_native_concurrent_deletion(access, monkeypatch, delete_during_upload):
    from server.routers import files
    pm, call = access
    entered, release = threading.Event(), threading.Event()
    real_normalize = files.normalize_uploaded_image
    def paused_normalize(*args, **kwargs):
        entered.set()
        assert release.wait(5), 'audit release timeout'
        return real_normalize(*args, **kwargs)
    monkeypatch.setattr(files, 'normalize_uploaded_image', paused_normalize)
    task = asyncio.create_task(call('upload_reference', kind='character_image', name='Ana',
                                   filename='reference.png', content_base64=png()))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        if delete_during_upload:
            # Supported native deletion, not direct dict/file surgery.
            await asyncio.to_thread(pm.delete_asset, 'demo', 'characters', 'Ana')
            assert 'Ana' not in pm.load_project('demo')['characters']
        release.set()
        result = await task
        assert result.problem is None and result.value['success'] is True
        reference = pm.get_project_path('demo') / result.value['path']
        assert reference.is_file()
        project = pm.load_project('demo')
        registered = 'Ana' in project['characters'] and project['characters']['Ana'].get('reference_image') == result.value['path']
        assert registered == (not delete_during_upload)
        print('R11 upload:', {'concurrent_native_deletion': delete_during_upload,
                              'reported_success': True, 'file_exists': True, 'registered_owner': registered})
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
