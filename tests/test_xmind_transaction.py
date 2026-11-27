"""A failed report generation must not destroy the previous report."""

import errno

import pytest

from maigret import report


@pytest.mark.parametrize(
    'stage', ['design', 'save', 'partial_save', 'normalize', 'replace']
)
@pytest.mark.parametrize('existing', [False, True])
def test_xmind_generation_failure_preserves_destination(
    tmp_path, monkeypatch, stage, existing
):
    filename = tmp_path / 'report.xmind'
    if existing:
        report.save_xmind_report(filename, 'old', {})
        original = filename.read_bytes()

    def fail(*args, **kwargs):
        raise OSError(errno.ENOSPC, 'simulated full report filesystem')

    real_save = report.xmind.save
    real_replace = report.os.replace

    def partial_save(*args, **kwargs):
        real_save(*args, **kwargs)
        fail()

    def fail_publish(source, destination):
        if report.os.path.abspath(destination) == str(filename):
            fail()
        return real_replace(source, destination)

    targets = {
        'design': (report, 'design_xmind_sheet', fail),
        'save': (report.xmind, 'save', fail),
        'partial_save': (report.xmind, 'save', partial_save),
        'normalize': (report, '_normalize_xmind_archive', fail),
        'replace': (report.os, 'replace', fail_publish),
    }
    monkeypatch.setattr(*targets[stage])

    with pytest.raises(OSError) as error:
        report.save_xmind_report(filename, 'new', {})

    assert error.value.errno == errno.ENOSPC
    if existing:
        assert filename.read_bytes() == original
        assert list(tmp_path.iterdir()) == [filename]
    else:
        assert not filename.exists()
        assert list(tmp_path.iterdir()) == []


def test_xmind_interruption_preserves_existing_report(tmp_path, monkeypatch):
    filename = tmp_path / 'report.xmind'
    report.save_xmind_report(filename, 'old', {})
    original = filename.read_bytes()

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(report, '_normalize_xmind_archive', interrupt)
    with pytest.raises(KeyboardInterrupt):
        report.save_xmind_report(filename, 'new', {})

    assert filename.read_bytes() == original
    assert list(tmp_path.iterdir()) == [filename]


def test_xmind_success_still_replaces_report_with_fresh_workbook(tmp_path):
    filename = tmp_path / 'report.xmind'
    report.save_xmind_report(str(filename), 'old', {})
    with report.zipfile.ZipFile(filename, mode='a') as archive:
        archive.writestr('obsolete.txt', b'old report attachment')

    report.save_xmind_report(filename, 'new', {})

    assert list(tmp_path.iterdir()) == [filename]
    with report.zipfile.ZipFile(filename) as archive:
        assert archive.testzip() is None
        assert 'obsolete.txt' not in archive.namelist()
        assert archive.namelist().count('META-INF/manifest.xml') == 1
    workbook = report.xmind.load(str(filename))
    assert workbook.getPrimarySheet().getData()['topic']['title'] == 'new'
