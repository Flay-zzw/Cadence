"""Persist observable work boundaries, never estimated model progress."""
from datetime import datetime, timezone
from . import storage


def now():
    return datetime.now(timezone.utc).isoformat()


def new_job(identifier):
    timestamp = now()
    return dict(id=identifier, status='queued', message='已加入生成队列', stage='queued',
                created_at=timestamp, updated_at=timestamp, started_at=None, finished_at=None,
                total_pages=None, current_page=None, completed_pages=0, attempt=0,
                stages=[dict(id='queued', started_at=timestamp, finished_at=None)], pages=[])


class Progress:
    def __init__(self, path, job):
        self.path, self.job = path, job

    def update(self, message, *, stage=None, planned_pages=None, page_index=None,
               completed_page=None, attempt=None):
        job, timestamp = self.job, now()
        if stage and stage != job['stage']:
            job['stages'][-1]['finished_at'] = timestamp
            job['stages'].append(dict(id=stage, started_at=timestamp, finished_at=None))
            job.update(stage=stage, current_page=None, attempt=0)
        if planned_pages is not None:
            job['total_pages'] = len(planned_pages)
            job['pages'] = [dict(index=i, title=p['title'], role=p['role'], status='pending',
                                 started_at=None, finished_at=None, attempt=0)
                            for i, p in enumerate(planned_pages, 1)]
        if page_index is not None:
            job.update(current_page=page_index, attempt=0)
            job['pages'][page_index-1].update(status='running', started_at=timestamp)
        if attempt is not None:
            job['attempt'] = attempt
            if job['current_page'] is not None:
                job['pages'][job['current_page']-1]['attempt'] = attempt
        if completed_page is not None:
            job['pages'][job['current_page']-1].update(
                status='completed', finished_at=timestamp, title=completed_page['title'])
            job['completed_pages'] = sum(p['status'] == 'completed' for p in job['pages'])
        job.update(message=message, updated_at=timestamp)
        storage.write(self.path, job)

    def finish(self, status, message, **fields):
        timestamp = now()
        self.job.update(status=status, message=message, finished_at=timestamp, updated_at=timestamp, **fields)
        self.job['stages'][-1]['finished_at'] = timestamp
        for page in self.job['pages']:
            if page['status'] == 'running':
                page.update(status='failed', finished_at=timestamp)
        storage.write(self.path, self.job)
