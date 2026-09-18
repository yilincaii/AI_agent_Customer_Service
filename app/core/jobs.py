# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com
"""后台管理页作业运行器:把 make 目标搬到浏览器上按,日志轮询回显,长活能停。

安全边界:只能跑 JOBS 注册表里的目标,argv 全部写死在本模块。前端只传一个 job 名,
传不进任何命令片段、参数或路径——页面有「重跑」按钮,但没有 shell。
命令一律走 make:配方是仓库里那一份,页面按的和终端敲的必须是同一条命令,不许分叉。
"""
import asyncio
import contextlib
import datetime as dt
import logging
import os
import signal
from dataclasses import dataclass, field
from pathlib import Path
logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = REPO_ROOT / 'log' / 'acceptance'
TAIL_LINES = 400

@dataclass(frozen=True)
class JobSpec:
    name: str
    title: str
    argv: tuple[str, ...]
    needs: str
    heavy: bool = False
JOBS: dict[str, JobSpec] = {j.name: j for j in (JobSpec('kb-preview', '材料清单与切块预览', ('make', 'kb-preview'), '本地跑,不写库'), JobSpec('kb-build', '离线建库(文档切块 → pending)', ('make', 'kb-build'), '需 mysql'), JobSpec('kb-mine', '对话挖知识(抽 QA → 去重 → pending)', ('make', 'kb-mine'), '需 mysql + 聊天上游', heavy=True), JobSpec('kb-vectorize', '向量化(嵌入 → Milvus → 回标 done)', ('make', 'kb-vectorize'), '需 mysql + 嵌入上游 + Milvus'), JobSpec('kb-repatch', '补丁式重嵌(md 改动 → 原地改正文)', ('make', 'kb-repatch'), '需 mysql;改完再按「向量化待补块」'), JobSpec('eval-rag', 'RAG 评估(四策略对照)', ('make', 'eval-rag'), '需 Milvus + 已建库 + 聊天上游,分钟级', heavy=True))}

@dataclass
class JobRun:
    """一次运行的状态。进程对象与 watcher 任务留在内存,重启服务后归零——
    但产物里的 ran_at 与日志文件都在盘上,页面照样能说出「上次什么时候跑的、跑成什么样」。"""
    status: str = 'idle'
    pid: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    returncode: int | None = None
    proc: asyncio.subprocess.Process | None = field(default=None, repr=False)
    watcher: asyncio.Task | None = field(default=None, repr=False)
_runs: dict[str, JobRun] = {}

def _run(name: str) -> JobRun:
    return _runs.setdefault(name, JobRun())

def log_path(name: str) -> Path:
    return LOG_DIR / f'{name}.log'

async def start(name: str) -> JobRun:
    """发起一次运行。同名作业未结束时拒绝重入(返回 RuntimeError),避免两份进程抢同一批产物。"""
    spec = JOBS[name]
    run = _run(name)
    if run.status == 'running':
        raise RuntimeError(f'{spec.title}正在运行中(pid {run.pid}),等它跑完再发起')
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = log_path(name)
    header = f'$ {' '.join(spec.argv)}\n# {dt.datetime.now().isoformat(timespec='seconds')} 由后台页发起\n\n'
    path.write_text(header, encoding='utf-8')
    fh = path.open('a', encoding='utf-8', buffering=1)
    try:
        proc = await asyncio.create_subprocess_exec(*spec.argv, cwd=REPO_ROOT, stdout=fh, stderr=asyncio.subprocess.STDOUT, env={**os.environ, 'PYTHONUNBUFFERED': '1'}, start_new_session=True)
    except Exception:
        fh.close()
        raise
    run.status, run.pid = ('running', proc.pid)
    run.started_at = dt.datetime.now().isoformat(timespec='seconds')
    run.finished_at = run.returncode = None
    run.proc = proc
    run.watcher = asyncio.create_task(_watch(name, run, proc, fh))
    logger.info('验收页发起作业 %s pid=%s argv=%s', name, proc.pid, ' '.join(spec.argv))
    return run

async def _watch(name: str, run: JobRun, proc: asyncio.subprocess.Process, fh) -> None:
    try:
        rc = await proc.wait()
    finally:
        with contextlib.suppress(Exception):
            fh.close()
    run.returncode = rc
    run.finished_at = dt.datetime.now().isoformat(timespec='seconds')
    if run.status != 'stopped':
        run.status = 'ok' if rc == 0 else 'failed'
    run.proc = None
    logger.info('验收页作业 %s 结束 rc=%s status=%s', name, rc, run.status)

async def stop(name: str) -> None:
    run = _run(name)
    proc = run.proc
    if run.status != 'running' or proc is None:
        raise RuntimeError('该作业当前没有在运行')
    run.status = 'stopped'
    with contextlib.suppress(ProcessLookupError):
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

def tail(name: str, lines: int=TAIL_LINES) -> str:
    path = log_path(name)
    if not path.exists():
        return ''
    text = path.read_text(encoding='utf-8', errors='replace')
    rows = text.splitlines()
    return '\n'.join(rows[-lines:])

def status(name: str, with_log: bool=False) -> dict:
    spec, run = (JOBS[name], _run(name))
    path = log_path(name)
    out = {'name': name, 'title': spec.title, 'cmd': ' '.join(spec.argv), 'needs': spec.needs, 'heavy': spec.heavy, 'status': run.status, 'pid': run.pid, 'started_at': run.started_at, 'finished_at': run.finished_at, 'returncode': run.returncode, 'log_mtime': dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds') if path.exists() else None}
    if with_log:
        out['log'] = tail(name)
    return out

def status_all() -> list[dict]:
    return [status(n) for n in JOBS]
